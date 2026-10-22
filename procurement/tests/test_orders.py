# filepath: procurement/tests/test_orders.py
from datetime import timedelta
from importlib import import_module, util
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import OperationalError
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import resolve
from django.utils import timezone
from django.views.debug import SafeExceptionReporterFilter

from accounts.models import Role, User
from common.actions import ActionContext
from common.errors import ConflictError
from procurement.inputs import QuotationInput, QuoteLineInput
from procurement.models import ActionReceipt, ApprovalDecision, AuditEvent, PurchaseOrder, PurchaseRequest, Quotation, Vendor
from procurement.services import requests, sourcing
from procurement.tests.factories import approved, context, user


def prepared(*, two_sources=False):
    owner, approver, buyer = user(Role.REQUESTER), user(Role.APPROVER), user(Role.PROCUREMENT)
    target = approved(owner, approver)
    item = target.revisions.get(number=1).items.get()
    quotes = []
    for position in range(2 if two_sources else 1):
        vendor = sourcing.save_vendor(ActionContext(buyer.pk, uuid4(), None), vendor_id=None,
                                      name=f'Vendor pesanan {position}', contact='Kontak pesanan', is_active=True)
        data = QuotationInput(vendor.pk, f'Q-{position}', timezone.localdate(),
                              timezone.localdate()+timedelta(days=3), 2, (QuoteLineInput(item.pk,'8.00'),))
        target.refresh_from_db()
        quotes.append(sourcing.save_quotation(context(buyer,target),request_id=target.pk,quotation_id=None,data=data))
    target.refresh_from_db()
    target = sourcing.select_quotation(context(buyer,target),request_id=target.pk,quotation_id=quotes[0].pk,
                                        reason='Sesuai kebutuhan',single_source_reason='' if two_sources else 'Satu vendor layak')
    return target, owner, approver, buyer


class OrderServiceTests(TestCase):
    def setUp(self):
        self.assertIsNotNone(util.find_spec('procurement.services.orders'),'Order service missing')
        self.service = import_module('procurement.services.orders')
        self.target,self.owner,self.approver,self.actor = prepared()

    def issue(self, ctx=None):
        return self.service.issue_order(ctx or context(self.actor,self.target),request_id=self.target.pk)

    def test_TC11_issue_copies_approved_snapshot_and_keeps_request_approved(self):
        version = self.target.version
        order = self.issue()
        self.target.refresh_from_db()
        self.assertEqual((order.status,order.version,self.target.status,self.target.version),('ISSUED',1,'APPROVED',version+1))
        self.assertEqual((order.vendor_name,order.vendor_contact,order.kind,order.destination,order.total_minor),
                         ('Vendor pesanan 0','Kontak pesanan','GOODS','Kantor',8000))
        self.assertEqual(order.issued_by_id,self.actor.pk)
        self.assertEqual((order.selection_reason,order.single_source_reason),('Sesuai kebutuhan','Satu vendor layak'))
        row = order.items.get()
        self.assertEqual((row.name,row.unit,row.qty_milli,row.unit_price_minor,row.line_total_minor),('Item contoh','unit',10000,800,8000))
        self.assertEqual(row.revision_item.revision_id,order.revision_id)
        self.assertEqual(AuditEvent.objects.filter(request=self.target,action='order.issue').count(),1)
        receipt = ActionReceipt.objects.get(actor=self.actor,action='order.issue')
        self.assertEqual((receipt.target_type,receipt.target_key,receipt.result_type,receipt.result_id),
                         ('REQUEST',str(self.target.pk),'ORDER',str(order.pk)))

    def test_TC18_issue_replay_returns_same_order_after_vendor_deactivation(self):
        ctx = context(self.actor,self.target)
        first = self.issue(ctx)
        Vendor.objects.filter(pk=first.vendor_id).update(is_active=False)
        self.assertEqual(self.issue(ctx).pk,first.pk)
        with self.assertRaises(ConflictError):
            self.issue(ActionContext(self.actor.pk,ctx.nonce,ctx.expected_version+1))
        self.assertEqual(PurchaseOrder.objects.count(),1)
        self.assertEqual(AuditEvent.objects.filter(action='order.issue').count(),1)

    def test_TC02_current_procurement_role_required_even_for_replay_and_superuser(self):
        ctx = context(self.actor,self.target)
        self.issue(ctx)
        for role in [Role.ADMIN,Role.REQUESTER,Role.APPROVER,Role.RECEIVER]:
            User.objects.filter(pk=self.actor.pk).update(role=role,is_superuser=True)
            with self.subTest(role=role),self.assertRaises(PermissionDenied):
                self.issue(ctx)
        User.objects.filter(pk=self.actor.pk).update(role=Role.PROCUREMENT,is_active=False)
        with self.assertRaises(PermissionDenied):
            self.issue(ctx)

    def test_TC11_candidate_and_selection_reason_are_required(self):
        quote_id = self.target.selected_quotation_id
        for values in [dict(selected_quotation=None),dict(selected_quotation_id=quote_id,selection_reason=' '),
                       dict(selected_quotation_id=quote_id,selection_reason='Sesuai',single_source_reason='')]:
            PurchaseRequest.objects.filter(pk=self.target.pk).update(**values)
            with self.subTest(values=values),self.assertRaises(ValidationError):
                self.issue()
        self.assertFalse(PurchaseOrder.objects.exists())

    def test_TC11_current_revision_approval_and_parent_must_match(self):
        for status in ['DRAFT','SUBMITTED','CHANGES_REQUESTED','REJECTED','CANCELLED']:
            PurchaseRequest.objects.filter(pk=self.target.pk).update(status=status)
            with self.subTest(status=status),self.assertRaises(ConflictError):
                self.issue()
        PurchaseRequest.objects.filter(pk=self.target.pk).update(status='APPROVED',current_revision_number=2)
        with self.assertRaises(ConflictError):
            self.issue()
        PurchaseRequest.objects.filter(pk=self.target.pk).update(current_revision_number=1)
        foreign,_,_,_ = prepared()
        PurchaseRequest.objects.filter(pk=self.target.pk).update(selected_quotation_id=foreign.selected_quotation_id)
        with self.assertRaises(ConflictError):
            self.issue()
        PurchaseRequest.objects.filter(pk=self.target.pk).update(selected_quotation_id=self.target.selected_quotation_id)
        ApprovalDecision.objects.filter(revision__request=self.target).delete()
        with self.assertRaises(ConflictError):
            self.issue()

    def test_TC11_vendor_dates_ceiling_and_corrupt_totals_are_rechecked_at_issue(self):
        for case in ['inactive','future','expired','ceiling','total','missing_item']:
            target,owner,approver,actor = prepared()
            quote = target.selected_quotation
            if case == 'inactive':
                Vendor.objects.filter(pk=quote.vendor_id).update(is_active=False)
            elif case == 'future':
                Quotation.objects.filter(pk=quote.pk).update(quoted_on=timezone.localdate()+timedelta(days=1))
            elif case == 'expired':
                Quotation.objects.filter(pk=quote.pk).update(quoted_on=timezone.localdate()-timedelta(days=2),valid_until=timezone.localdate()-timedelta(days=1))
            elif case == 'ceiling':
                quote.items.update(unit_price_minor=1100,line_total_minor=11000)
                Quotation.objects.filter(pk=quote.pk).update(total_minor=11000)
            elif case == 'total':
                Quotation.objects.filter(pk=quote.pk).update(total_minor=1)
            else:
                quote.items.all().delete()
            with self.subTest(case=case),self.assertRaises(ValidationError):
                self.service.issue_order(context(actor,target),request_id=target.pk)
        self.assertFalse(PurchaseOrder.objects.exists())

    def test_TC11_single_source_is_recounted_when_alternative_is_deactivated(self):
        target,owner,approver,actor = prepared(two_sources=True)
        alternative = target.revisions.get(number=1).quotations.exclude(pk=target.selected_quotation_id).get()
        Vendor.objects.filter(pk=alternative.vendor_id).update(is_active=False)
        with self.assertRaises(ValidationError):
            self.service.issue_order(context(actor,target),request_id=target.pk)
        self.assertFalse(PurchaseOrder.objects.exists())

    def test_TC11_audit_failure_rolls_back_header_items_request_version_and_receipt(self):
        before = self.target.version
        with patch('procurement.services.orders.AuditEvent.objects.create',side_effect=RuntimeError('Synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.issue()
        self.target.refresh_from_db()
        self.assertEqual(self.target.version,before)
        self.assertFalse(PurchaseOrder.objects.exists())
        self.assertFalse(ActionReceipt.objects.filter(action='order.issue').exists())

    def test_TC11_vendor_edits_do_not_change_saved_order_fields(self):
        order = self.issue()
        vendor = order.vendor
        sourcing.save_vendor(context(self.actor,vendor),vendor_id=vendor.pk,name='Nama berubah',contact='Kontak berubah',is_active=False)
        order.refresh_from_db()
        self.assertEqual((order.vendor_name,order.vendor_contact,order.total_minor),('Vendor pesanan 0','Kontak pesanan',8000))

    def test_TC15_any_order_including_terminal_blocks_second_issue_and_request_mutations(self):
        order = self.issue()
        for status in ['ISSUED','RECEIVED','CANCELLED','CLOSED_SHORT']:
            values = dict(status=status)
            if status in ['CANCELLED','CLOSED_SHORT']:
                values.update(closed_by=self.approver,closed_at=timezone.now(),closed_reason='Fixture terminal')
            else:
                values.update(closed_by=None,closed_at=None,closed_reason='')
            PurchaseOrder.objects.filter(pk=order.pk).update(**values)
            self.target.refresh_from_db()
            for action in [lambda: self.issue(),
                           lambda: requests.cancel_request(context(self.owner,self.target),request_id=self.target.pk,reason='Batal'),
                           lambda: requests.request_revision(context(self.actor,self.target),request_id=self.target.pk,reason='Ubah')]:
                with self.subTest(status=status),self.assertRaises(ConflictError):
                    action()
        self.assertEqual(PurchaseOrder.objects.count(),1)

    def test_TC18_stale_request_and_version_overflow_do_not_create_order(self):
        stale = context(self.actor,self.target)
        PurchaseRequest.objects.filter(pk=self.target.pk).update(version=self.target.version+1)
        with self.assertRaises(ConflictError):
            self.issue(stale)
        PurchaseRequest.objects.filter(pk=self.target.pk).update(version=9223372036854775807)
        self.target.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.issue()
        self.assertFalse(PurchaseOrder.objects.exists())


class OrderHttpTests(TestCase):
    def setUp(self):
        self.target,self.owner,self.approver,self.actor = prepared()
        self.path = f'/requests/{self.target.pk}/issue-po/'
        self.client.force_login(self.actor)

    def payload(self):
        response = self.client.get(f'/requests/{self.target.pk}/')
        self.assertEqual(response.status_code,200)
        self.assertIsNotNone(response.context.get('issue_form'),'Issue form missing')
        return dict(response.context['issue_form'].initial)

    def issue(self):
        response = self.client.post(self.path,self.payload())
        self.assertEqual(response.status_code,303)
        return PurchaseOrder.objects.get(request=self.target)

    def test_TC11_post_issues_once_ignores_server_only_fields_and_redirects_to_order(self):
        self.assertEqual(self.client.get(self.path).status_code,405)
        payload = self.payload() | dict(vendor=str(uuid4()),quotation=str(uuid4()),total_minor='1',status='RECEIVED')
        response = self.client.post(self.path,payload)
        self.assertEqual(response.status_code,303)
        order = PurchaseOrder.objects.get()
        self.assertEqual(response['Location'],f'/orders/{order.pk}/')
        self.assertEqual((order.status,order.total_minor,order.issued_by_id),('ISSUED',8000,self.actor.pk))
        self.assertEqual(self.client.post(self.path,payload).status_code,303)
        detail = self.client.get(f'/requests/{self.target.pk}/')
        self.assertIsNone(detail.context['issue_form'])

    def test_TC02_order_list_detail_print_visibility_follows_request_scope(self):
        order = self.issue()
        for actor in [self.owner,self.approver,self.actor,user(Role.ADMIN),user(Role.RECEIVER)]:
            self.client.force_login(actor)
            for path in ['/orders/',f'/orders/{order.pk}/',f'/orders/{order.pk}/print/']:
                self.assertContains(self.client.get(path),order.number)
        self.client.force_login(user(Role.REQUESTER))
        self.assertNotContains(self.client.get('/orders/'),order.number)
        self.assertEqual(self.client.get(f'/orders/{order.pk}/').status_code,404)
        self.assertEqual(self.client.get(f'/orders/{order.pk}/print/').status_code,404)
        self.client.logout()
        self.assertEqual(self.client.get('/orders/').status_code,302)

    def test_TC11_print_reads_snapshot_without_mutations_after_vendor_and_actor_rename(self):
        order = self.issue()
        before = AuditEvent.objects.count()
        Vendor.objects.filter(pk=order.vendor_id).update(name='Vendor berubah',contact='Kontak berubah')
        User.objects.filter(pk=self.actor.pk).update(username='nama-aktor-berubah')
        original_name = self.actor.username
        for _ in range(2):
            response = self.client.get(f'/orders/{order.pk}/print/')
            self.assertContains(response,'Vendor pesanan 0')
            self.assertContains(response,'Kontak pesanan')
            self.assertContains(response,'80,00')
            self.assertContains(response,original_name)
            self.assertNotContains(response,'Vendor berubah')
            self.assertNotContains(response,'nama-aktor-berubah')
            self.assertNotContains(response,'<form')
        self.assertEqual(AuditEvent.objects.count(),before)
        self.assertEqual(self.client.post(f'/orders/{order.pk}/print/',{}).status_code,405)

    def test_TC18_csrf_other_actor_token_stale_and_unauthorized_issue_are_rejected(self):
        payload = self.payload()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.actor)
        self.assertEqual(csrf_client.post(self.path,payload).status_code,403)
        self.client.force_login(user(Role.PROCUREMENT))
        self.assertEqual(self.client.post(self.path,payload).status_code,400)
        self.client.force_login(self.actor)
        PurchaseRequest.objects.filter(pk=self.target.pk).update(version=self.target.version+1)
        self.assertEqual(self.client.post(self.path,payload).status_code,409)
        self.client.force_login(self.approver)
        self.assertEqual(self.client.post(self.path,payload).status_code,403)
        self.assertFalse(PurchaseOrder.objects.exists())

    def test_TC18_busy_maps_503_and_unexpected_database_error_is_rethrown(self):
        payload = self.payload()
        with patch('procurement.views.orders.issue_order',side_effect=OperationalError('database is locked')):
            response = self.client.post(self.path,payload)
        self.assertEqual((response.status_code,response['Retry-After']),(503,'1'))
        with patch('procurement.views.orders.issue_order',side_effect=OperationalError('unknown table')):
            with self.assertRaises(OperationalError):
                self.client.post(self.path,payload)

    @override_settings(DEBUG=False)
    def test_TC18_issue_tokens_are_redacted_in_exception_report_post_data(self):
        self.assertEqual(self.client.get(self.path).status_code,405)
        request = RequestFactory().post(self.path,dict(action_token='synthetic-token',csrfmiddlewaretoken='synthetic-csrf'))
        request.user = AnonymousUser()
        match = resolve(self.path)
        match.func(request,**match.kwargs)
        filtered = SafeExceptionReporterFilter().get_post_parameters(request)
        self.assertNotEqual(filtered['action_token'],request.POST['action_token'])
        self.assertNotEqual(filtered['csrfmiddlewaretoken'],request.POST['csrfmiddlewaretoken'])
