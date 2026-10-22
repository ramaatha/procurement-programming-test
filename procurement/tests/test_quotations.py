# filepath: procurement/tests/test_quotations.py
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from importlib import import_module, util
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import OperationalError, close_old_connections
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import resolve
from django.utils import timezone
from django.views.debug import SafeExceptionReporterFilter

from accounts.models import Role, User
from common.actions import ActionContext
from common.errors import ConflictError
from procurement.inputs import DraftInput, QuotationInput, QuoteLineInput, RequestLineInput
from procurement.models import ActionReceipt, AuditEvent, PurchaseRequest, Quotation, Vendor
from procurement.services import requests
from procurement.tests.factories import approved, context, issued, user


class QuotationTests(TestCase):
    def setUp(self):
        self.assertIsNotNone(util.find_spec('procurement.services.sourcing'), 'Sourcing service missing')
        self.service = import_module('procurement.services.sourcing')
        self.owner = user(Role.REQUESTER)
        self.approver = user(Role.APPROVER)
        self.actor = user(Role.PROCUREMENT)
        self.target = approved(self.owner, self.approver)
        self.vendor = self.make_vendor()
        self.client.force_login(self.actor)
        self.path = f'/requests/{self.target.pk}/quotations/'

    def make_vendor(self):
        return self.service.save_vendor(ActionContext(self.actor.pk, uuid4(), None), vendor_id=None,
                                        name='Vendor ' + uuid4().hex[:6], contact='Kontak', is_active=True)

    def data(self, *, vendor=None, price='8.00', **changes):
        revision = self.target.revisions.get(number=self.target.current_revision_number)
        values = QuotationInput((vendor or self.vendor).pk, 'Q-001', timezone.localdate(),
                                 timezone.localdate()+timedelta(days=3), 2,
                                 tuple(QuoteLineInput(row.pk, price) for row in revision.items.all()))
        return replace(values, **changes)

    def quote(self, target=None, data=None):
        self.target.refresh_from_db()
        return self.service.save_quotation(context(self.actor, self.target), request_id=self.target.pk,
                                           quotation_id=target.pk if target else None, data=data or self.data())

    def select(self, quote, *, reason='Sesuai spesifikasi', single='Satu sumber yang layak', ctx=None):
        self.target.refresh_from_db()
        return self.service.select_quotation(ctx or context(self.actor, self.target), request_id=self.target.pk,
                                             quotation_id=quote.pk, reason=reason, single_source_reason=single)

    def test_TC08_quote_uses_snapshot_quantity_and_server_computed_totals(self):
        before = self.target.version
        quote = self.quote()
        self.target.refresh_from_db()
        self.assertEqual((quote.total_minor, quote.items.get().unit_price_minor,
                          quote.items.get().line_total_minor, self.target.version), (8000, 800, 8000, before+1))
        self.assertEqual(quote.revision.number, 1)
        self.assertEqual(quote.created_by_id, self.actor.pk)

    def test_TC08_complete_exact_item_set_and_strict_prices_are_required(self):
        item = self.data().items[0]
        cases = [replace(self.data(), items=()), replace(self.data(), items=(item, item)),
                 replace(self.data(), items=(QuoteLineInput(uuid4(), '8.00'),)),
                 self.data(price='0'), self.data(price='NaN'), self.data(price='1.001'),
                 self.data(price='92233720368547758.07')]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                self.quote(data=data)
        self.assertFalse(Quotation.objects.exists())

    def test_TC08_dates_reference_and_fulfillment_are_validated(self):
        for changes in [dict(reference=' '), dict(quoted_on=timezone.localdate()+timedelta(days=5)),
                        dict(fulfillment_days=-1), dict(fulfillment_days=True), dict(fulfillment_days=9223372036854775808),
                        dict(quoted_on=None), dict(vendor_id=uuid4())]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.quote(data=self.data(**changes))

    def test_TC07_inactive_vendor_denied_and_old_quotation_kept(self):
        quote = self.quote()
        Vendor.objects.filter(pk=self.vendor.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            self.quote()
        with self.assertRaises(ValidationError):
            self.select(quote)
        self.assertEqual(Quotation.objects.count(), 1)

    def test_TC08_only_procurement_can_mutate_and_current_role_precedes_replay(self):
        self.target.refresh_from_db()
        ctx = context(self.actor, self.target)
        data = self.data()
        self.service.save_quotation(ctx, request_id=self.target.pk, quotation_id=None, data=data)
        for role in [Role.ADMIN, Role.APPROVER, Role.REQUESTER, Role.RECEIVER]:
            User.objects.filter(pk=self.actor.pk).update(role=role)
            with self.subTest(role=role), self.assertRaises(PermissionDenied):
                self.service.save_quotation(ctx, request_id=self.target.pk, quotation_id=None, data=data)

    def test_TC08_approved_current_decision_and_no_po_are_required(self):
        PurchaseRequest.objects.filter(pk=self.target.pk).update(status='SUBMITTED')
        with self.assertRaises(ConflictError):
            self.quote()
        PurchaseRequest.objects.filter(pk=self.target.pk).update(status='APPROVED', current_revision_number=2)
        with self.assertRaises(ConflictError):
            self.quote(data=self.data_for_first_revision())
        order = issued()
        self.target = order.request
        with self.assertRaises(ConflictError):
            self.quote()

    def data_for_first_revision(self):
        item = self.target.revisions.get(number=1).items.get()
        return QuotationInput(self.vendor.pk, 'Q', timezone.localdate(), timezone.localdate(), 0,
                              (QuoteLineInput(item.pk, '1.00'),))

    def test_TC18_quote_replay_numeric_canonicalization_and_stale_version(self):
        ctx = context(self.actor, self.target)
        quote = self.service.save_quotation(ctx, request_id=self.target.pk, quotation_id=None, data=self.data(price='8'))
        replay = self.service.save_quotation(ctx, request_id=self.target.pk, quotation_id=None, data=self.data(price='8.00'))
        self.assertEqual(replay.pk, quote.pk)
        with self.assertRaises(ConflictError):
            self.service.save_quotation(ctx, request_id=self.target.pk, quotation_id=None, data=self.data(price='9'))
        with self.assertRaises(ConflictError):
            self.service.save_quotation(ActionContext(self.actor.pk, uuid4(), ctx.expected_version),
                                         request_id=self.target.pk, quotation_id=None, data=self.data())
        self.assertEqual(Quotation.objects.count(), 1)

    def test_TC09_single_source_requires_reason_and_counts_unique_eligible_vendors(self):
        quote = self.quote()
        self.quote(data=self.data(reference='Q-002', price='7.00'))
        with self.assertRaises(ValidationError):
            self.select(quote, single='')
        other_vendor = self.make_vendor()
        self.quote(data=self.data(vendor=other_vendor, price='6.00'))
        result = self.select(quote, single='')
        self.assertEqual(result.selected_quotation_id, quote.pk)
        self.assertEqual(result.selection_reason, 'Sesuai spesifikasi')

    def test_TC09_future_expired_over_ceiling_or_corrupt_quote_is_not_selectable(self):
        today = timezone.localdate()
        for data in [self.data(quoted_on=today+timedelta(days=1)),
                     self.data(quoted_on=today-timedelta(days=2), valid_until=today-timedelta(days=1)),
                     self.data(price='11.00')]:
            quote = self.quote(data=data)
            with self.subTest(data=data), self.assertRaises(ValidationError):
                self.select(quote)
        quote = self.quote()
        Quotation.objects.filter(pk=quote.pk).update(total_minor=1)
        with self.assertRaises(ValidationError):
            self.select(quote)

    def test_TC09_invalid_alternatives_do_not_remove_single_source_requirement(self):
        quote = self.quote()
        other_vendor = self.make_vendor()
        self.quote(data=self.data(vendor=other_vendor, price='11.00'))
        with self.assertRaises(ValidationError):
            self.select(quote, single='')
        with self.assertRaises(ValidationError):
            self.select(quote, reason=' ')

    def test_TC09_edit_selected_quote_clears_choice_and_history_keeps_old_reason(self):
        quote = self.quote()
        self.select(quote)
        self.quote(quote, data=self.data(price='7.00'))
        self.target.refresh_from_db()
        self.assertEqual((self.target.selected_quotation_id, self.target.selection_reason,
                          self.target.single_source_reason), (None, '', ''))
        self.assertEqual(AuditEvent.objects.get(request=self.target, action='quotation.select').reason, 'Sesuai spesifikasi')
        self.assertEqual(Quotation.objects.get().total_minor, 7000)

    def test_TC10_foreign_request_and_historical_quote_cannot_be_edited_or_selected(self):
        quote = self.quote()
        old_revision = quote.revision_id
        self.target.refresh_from_db()
        self.target = requests.request_revision(context(self.actor, self.target), request_id=self.target.pk, reason='Ubah')
        self.target = requests.submit_request(context(self.owner, self.target), request_id=self.target.pk)
        self.target = requests.review_request(context(self.approver, self.target), request_id=self.target.pk, decision='APPROVE', reason='')
        for action in [lambda: self.quote(quote), lambda: self.select(quote)]:
            with self.assertRaises(ConflictError):
                action()
        quote.refresh_from_db()
        self.assertEqual((quote.revision_id, quote.total_minor), (old_revision, 8000))

    def test_TC18_selection_replays_and_changed_payload_conflicts(self):
        quote = self.quote()
        self.target.refresh_from_db()
        ctx = context(self.actor, self.target)
        result = self.select(quote, ctx=ctx)
        self.assertEqual(self.select(quote, ctx=ctx).pk, result.pk)
        with self.assertRaises(ConflictError):
            self.select(quote, reason='Berbeda', ctx=ctx)
        self.assertEqual(AuditEvent.objects.filter(request=self.target, action='quotation.select').count(), 1)

    def test_TC18_quote_and_selection_audit_failure_roll_back_whole_change(self):
        before = self.target.version
        with patch('procurement.services.sourcing.AuditEvent.objects.create', side_effect=RuntimeError('Synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.quote()
        self.target.refresh_from_db()
        self.assertEqual(self.target.version, before)
        self.assertFalse(Quotation.objects.exists())
        quote = self.quote()
        with patch('procurement.services.sourcing.AuditEvent.objects.create', side_effect=RuntimeError('Synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.select(quote)
        self.target.refresh_from_db()
        self.assertIsNone(self.target.selected_quotation_id)

    def form_payload(self):
        response = self.client.get(self.path+'new/')
        self.assertEqual(response.status_code, 200)
        item = self.target.revisions.get(number=self.target.current_revision_number).items.get()
        return dict(response.context['form'].initial) | {
            'vendor':str(self.vendor.pk), 'reference':'Q-HTTP', 'quoted_on':str(timezone.localdate()),
            'valid_until':str(timezone.localdate()+timedelta(days=2)), 'fulfillment_days':'3',
            'items-TOTAL_FORMS':'1', 'items-INITIAL_FORMS':'1', 'items-0-revision_item_id':str(item.pk),
            'items-0-unit_price':'8.00', 'items-0-quantity':'9999', 'total_minor':'1',
        }

    def test_TC08_http_quote_and_comparison_ignore_qty_total_and_show_fulfillment(self):
        self.assertContains(self.client.get(self.path), 'Belum ada penawaran')
        payload = self.form_payload()
        self.assertEqual(self.client.post(self.path+'new/', payload).status_code, 303)
        quote = Quotation.objects.get()
        self.assertEqual(quote.total_minor, 8000)
        response = self.client.get(self.path)
        self.assertContains(response, '80,00')
        self.assertContains(response, '3 hari')
        self.assertEqual(self.client.post(self.path+'new/', payload).status_code, 303)
        self.assertEqual(Quotation.objects.count(), 1)

    def test_TC08_http_missing_items_invalid_management_or_foreign_item_do_not_save(self):
        payload = self.form_payload()
        for changes in [{'items-TOTAL_FORMS':'0'}, {'items-TOTAL_FORMS':'-1'},
                        {'items-0-revision_item_id':str(uuid4())}, {'items-0-unit_price':''}]:
            response = self.client.post(self.path+'new/', payload | changes)
            self.assertEqual(response.status_code, 400)
            self.assertContains(response, 'Q-HTTP', status_code=400)
        self.assertFalse(Quotation.objects.exists())

    def test_TC09_http_select_reason_required_and_non_procurement_cannot_mutate(self):
        quote = self.quote()
        response = self.client.get(self.path)
        self.assertIsNotNone(response.context['selection_form'])
        payload = dict(response.context['selection_form'].initial) | dict(quotation=str(quote.pk), reason='Sesuai', single_source_reason='')
        self.assertEqual(self.client.post(self.path+'select/', payload).status_code, 400)
        payload['single_source_reason'] = 'Satu sumber layak'
        self.assertEqual(self.client.post(self.path+'select/', payload).status_code, 303)
        self.assertEqual(self.client.get(self.path+'select/').status_code, 405)
        self.client.force_login(self.approver)
        self.assertEqual(self.client.get(self.path).status_code, 200)
        self.assertEqual(self.client.post(self.path+'select/', payload).status_code, 403)
        self.assertEqual(self.client.get(self.path+'new/').status_code, 403)
        self.client.force_login(user(Role.REQUESTER))
        self.assertEqual(self.client.get(self.path).status_code, 404)

    def test_TC18_http_csrf_other_actor_token_and_stale_quote_are_rejected(self):
        payload = self.form_payload()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.actor)
        self.assertEqual(client.post(self.path+'new/', payload).status_code, 403)
        self.client.force_login(user(Role.PROCUREMENT))
        self.assertEqual(self.client.post(self.path+'new/', payload).status_code, 400)
        self.client.force_login(self.actor)
        self.quote()
        self.assertEqual(self.client.post(self.path+'new/', payload).status_code, 409)

    def test_TC18_http_quote_replay_survives_vendor_deactivation(self):
        payload = self.form_payload()
        self.assertEqual(self.client.post(self.path+'new/', payload).status_code, 303)
        Vendor.objects.filter(pk=self.vendor.pk).update(is_active=False)
        self.assertEqual(self.client.post(self.path+'new/', payload).status_code, 303)
        self.assertEqual(Quotation.objects.count(), 1)

    def test_TC09_choice_labels_distinguish_same_vendor_reference_by_price_and_delivery(self):
        self.quote()
        self.quote(data=self.data(price='7.00', fulfillment_days=5))
        form = self.client.get(self.path).context['selection_form']
        labels = [str(label) for value, label in form.fields['quotation'].choices if str(value)]
        self.assertEqual(len(set(labels)), 2)
        self.assertTrue(any('80,00' in label and '2 hari' in label for label in labels))
        self.assertTrue(any('70,00' in label and '5 hari' in label for label in labels))

    @override_settings(DEBUG=False)
    def test_TC18_sourcing_post_tokens_are_redacted(self):
        paths = ['/vendors/new/', f'/vendors/{self.vendor.pk}/edit/', self.path+'new/',
                 self.path+f'{uuid4()}/edit/', self.path+'select/']
        for path in paths:
            self.assertEqual(self.client.get(path).status_code in (200,404,405), True)
            request = RequestFactory().post(path, dict(action_token='synthetic-token', csrfmiddlewaretoken='synthetic-csrf'))
            request.user = AnonymousUser()
            match = resolve(path)
            match.func(request, **match.kwargs)
            filtered = SafeExceptionReporterFilter().get_post_parameters(request)
            self.assertNotEqual(filtered['action_token'], request.POST['action_token'])
            self.assertNotEqual(filtered['csrfmiddlewaretoken'], request.POST['csrfmiddlewaretoken'])


class QuotationConcurrencyTests(TransactionTestCase):
    def test_TC18_two_quote_writers_use_request_version_and_same_nonce_replays(self):
        self.assertIsNotNone(util.find_spec('procurement.services.sourcing'), 'Sourcing service missing')
        service = import_module('procurement.services.sourcing')
        actor = user(Role.PROCUREMENT)
        vendor = service.save_vendor(ActionContext(actor.pk, uuid4(), None), vendor_id=None,
                                     name='Vendor', contact='Kontak', is_active=True)
        for same_nonce in [False, True]:
            target = approved(user(Role.REQUESTER), user(Role.APPROVER))
            item = target.revisions.get(number=1).items.get()
            data = QuotationInput(vendor.pk, 'Q', timezone.localdate(), timezone.localdate(), 0, (QuoteLineInput(item.pk,'8.00'),))
            nonce = uuid4()
            contexts = [ActionContext(actor.pk, nonce, target.version),
                        ActionContext(actor.pk, nonce if same_nonce else uuid4(), target.version)]
            gate = Barrier(2)
            def save(ctx):
                close_old_connections()
                try:
                    gate.wait(timeout=5)
                    service.save_quotation(ctx, request_id=target.pk, quotation_id=None, data=data)
                    return 'ok'
                except ConflictError:
                    return 'conflict'
                finally:
                    close_old_connections()
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(save, contexts, timeout=15))
            self.assertCountEqual(results, ['ok','ok'] if same_nonce else ['ok','conflict'])
            self.assertEqual(Quotation.objects.filter(revision__request=target).count(), 1)
