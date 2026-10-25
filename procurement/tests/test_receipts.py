from dataclasses import replace
from importlib import import_module, util
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from accounts.models import Role, User
from common.actions import ActionContext
from common.errors import ConflictError
from procurement.inputs import ReceiptLineInput
from procurement.models import ActionReceipt, AuditEvent, Receipt, ReceiptItem
from procurement.tests.factories import context, issued, user
from procurement.tests.receipt_fixtures import receipt_data


class ReceiptTests(TestCase):
    def setUp(self):
        self.assertIsNotNone(util.find_spec('procurement.services.receipts'), 'Receipt service missing')
        self.service = import_module('procurement.services.receipts')
        self.order = issued()
        self.actor = user(Role.RECEIVER)

    def post(self, data=None, ctx=None):
        return self.service.post_receipt(ctx or context(self.actor,self.order),order_id=self.order.pk,
                                         data=data or receipt_data(self.order))

    def test_partial_then_complete_rejected_does_not_reduce_remaining(self):
        first = self.post()
        self.order.refresh_from_db()
        self.assertEqual((self.order.status,self.order.version),('PARTIALLY_RECEIVED',2))
        self.assertEqual((first.items.get().accepted_milli,first.items.get().rejected_milli),(6000,2000))
        self.post(receipt_data(self.order,'4','0',''))
        self.order.refresh_from_db()
        self.assertEqual((self.order.status,self.order.version),('RECEIVED',3))
        self.assertEqual(Receipt.objects.count(),2)

    def test_rejection_only_keeps_order_issued(self):
        self.post(receipt_data(self.order,'0','2'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status,'ISSUED')

    def test_invalid_lines_are_atomic(self):
        good = receipt_data(self.order)
        row = good.items[0]
        for rows in [(),(replace(row,accepted='0',rejected='0'),),
                     (replace(row,accepted='-1'),),(replace(row,accepted='11'),),
                     (replace(row,rejection_reason=' '),),(row,row),
                     (row,replace(row,order_item_id=uuid4())),(replace(row,accepted='0.0001'),)]:
            with self.subTest(rows=rows),self.assertRaises(ValidationError):
                self.post(replace(good,items=rows))
            self.assertFalse(Receipt.objects.exists())
            self.order.refresh_from_db()
            self.assertEqual((self.order.status,self.order.version),('ISSUED',1))

    def test_required_notes_reference_and_goods_period_are_validated(self):
        from datetime import date
        good = receipt_data(self.order)
        for change in [dict(notes=' '),dict(reference=' '),dict(evidence_type='SERVICE_REPORT'),
                       dict(service_started_on=date.today())]:
            with self.subTest(change=change),self.assertRaises(ValidationError):
                self.post(replace(good,**change))

    def test_replay_is_canonical_and_different_payload_conflicts(self):
        ctx = context(self.actor,self.order)
        result = self.post(ctx=ctx)
        self.assertEqual(self.post(receipt_data(self.order,'6.000','2.0'),ctx).pk,result.pk)
        with self.assertRaises(ConflictError):
            self.post(receipt_data(self.order,'5','2'),ctx)
        self.assertEqual(Receipt.objects.count(),1)
        self.assertEqual(AuditEvent.objects.filter(action='receipt.post').count(),1)

    def test_receiver_current_role_and_activity_required_even_for_replay(self):
        ctx = context(self.actor,self.order)
        self.post(ctx=ctx)
        for role in [Role.REQUESTER,Role.APPROVER,Role.PROCUREMENT,Role.ADMIN]:
            User.objects.filter(pk=self.actor.pk).update(role=role,is_superuser=True)
            with self.subTest(role=role),self.assertRaises(PermissionDenied):
                self.post(ctx=ctx)
        User.objects.filter(pk=self.actor.pk).update(role=Role.RECEIVER,is_active=False)
        with self.assertRaises(PermissionDenied):
            self.post(ctx=ctx)

    def test_terminal_or_stale_order_rejects_new_receipt(self):
        self.post(receipt_data(self.order,'10','0',''))
        with self.assertRaises(ConflictError):
            self.post()
        self.order.refresh_from_db()
        with self.assertRaises(ConflictError):
            self.post()

    def test_audit_failure_rolls_back_receipt_lines_status_and_replay(self):
        before = (Receipt.objects.count(),ReceiptItem.objects.count(),ActionReceipt.objects.count())
        with patch('procurement.services.receipts.AuditEvent.objects.create',side_effect=RuntimeError('audit failed')):
            with self.assertRaises(RuntimeError):
                self.post()
        self.order.refresh_from_db()
        self.assertEqual((self.order.status,self.order.version),('ISSUED',1))
        self.assertEqual((Receipt.objects.count(),ReceiptItem.objects.count(),ActionReceipt.objects.count()),before)

    def test_over_receipt_after_partial_uses_committed_remaining(self):
        self.post()
        self.order.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.post(receipt_data(self.order,'5','0',''))
        self.assertEqual(Receipt.objects.count(),1)

    def test_cumulative_rejections_do_not_break_quantity_display(self):
        self.post(receipt_data(self.order,'0','9223372036854775.807','Ditolak'))
        self.order.refresh_from_db()
        self.post(receipt_data(self.order,'0','9223372036854775.807','Ditolak'))
        self.client.force_login(self.actor)
        self.assertContains(self.client.get(f'/orders/{self.order.pk}/'),'18.446.744.073.709.551,614')
        self.assertEqual(self.client.get(f'/orders/{self.order.pk}/receipts/new/').status_code,200)
        self.assertEqual(Receipt.objects.filter(order=self.order).count(),2)

    def test_multiple_items_complete_only_when_all_are_received(self):
        from datetime import timedelta
        from django.utils import timezone
        from procurement.inputs import DraftInput, RequestLineInput, QuotationInput, QuoteLineInput
        from procurement.services import requests, sourcing, orders
        from procurement.models import ReceiptItem
        owner,approver,buyer = user(Role.REQUESTER),user(Role.APPROVER),user(Role.PROCUREMENT)
        data = DraftInput('GOODS','Dua item','Kebutuhan','Kantor',timezone.localdate()+timedelta(days=1),
                          (RequestLineInput('A','unit','10','10'),RequestLineInput('B','pak','2','10')))
        target = requests.save_draft(ActionContext(owner.pk,uuid4(),None),request_id=None,data=data)
        target = requests.submit_request(context(owner,target),request_id=target.pk)
        target = requests.review_request(context(approver,target),request_id=target.pk,decision='APPROVE',reason='')
        vendor = sourcing.save_vendor(ActionContext(buyer.pk,uuid4(),None),vendor_id=None,name='Vendor multi',contact='Kontak',is_active=True)
        lines = tuple(QuoteLineInput(row.pk,'10') for row in target.revisions.get(number=1).items.all())
        quote = sourcing.save_quotation(context(buyer,target),request_id=target.pk,quotation_id=None,
                    data=QuotationInput(vendor.pk,'Q-MULTI',timezone.localdate(),timezone.localdate()+timedelta(days=1),1,lines))
        target.refresh_from_db()
        target = sourcing.select_quotation(context(buyer,target),request_id=target.pk,quotation_id=quote.pk,reason='Cocok',single_source_reason='Satu vendor')
        order = orders.issue_order(context(buyer,target),request_id=target.pk)
        a,b = list(order.items.all())
        header = receipt_data(self.order)
        # A valid first row must not survive an invalid second row.
        with self.assertRaises(ValidationError):
            self.service.post_receipt(context(self.actor,order),order_id=order.pk,
                data=replace(header,items=(ReceiptLineInput(a.pk,'10','0',''),ReceiptLineInput(b.pk,'3','0',''))))
        self.assertFalse(Receipt.objects.filter(order=order).exists())
        self.service.post_receipt(context(self.actor,order),order_id=order.pk,data=replace(header,items=(ReceiptLineInput(a.pk,'10','0',''),)))
        order.refresh_from_db()
        self.assertEqual(order.status,'PARTIALLY_RECEIVED')
        self.service.post_receipt(context(self.actor,order),order_id=order.pk,data=replace(header,items=(ReceiptLineInput(b.pk,'2','0',''),)))
        order.refresh_from_db()
        self.assertEqual(order.status,'RECEIVED')
