# filepath: procurement/tests/test_constraints.py
from datetime import date, timedelta
from uuid import uuid4

from django.apps import apps
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User


class ConstraintTests(TestCase):
    def setUp(self):
        self.assertTrue(apps.is_installed('procurement'), 'Schema Procurement belum terdaftar.')
        self.owner = User.objects.create_user(username='owner')
        self.approver = User.objects.create_user(username='approver', role='APPROVER')
        self.models = {name: apps.get_model('procurement', name) for name in [
            'PurchaseRequest', 'RequestItem', 'RequestRevision', 'RevisionItem', 'ApprovalDecision', 'Vendor',
            'Quotation', 'QuotationItem', 'PurchaseOrder', 'PurchaseOrderItem', 'Receipt', 'ReceiptItem', 'AuditEvent', 'ActionReceipt',
        ]}
        self.request = self.models['PurchaseRequest'].objects.create(requester=self.owner, kind='GOODS')

    def create_revision(self, **overrides):
        values = dict(request=self.request, number=1, kind='GOODS', title='Kursi kerja', reason='Penggantian', destination='Kantor', needed_on=date(2026, 10, 25), estimated_total_minor=10000, submitted_by=self.owner)
        return self.models['RequestRevision'].objects.create(**(values | overrides))

    def create_revision_item(self, revision, **overrides):
        values = dict(revision=revision, position=1, name='Kursi', unit='unit', qty_milli=10000, estimated_unit_price_minor=1000, line_total_minor=10000)
        return self.models['RevisionItem'].objects.create(**(values | overrides))

    def create_order(self):
        revision = self.create_revision()
        item = self.create_revision_item(revision)
        vendor = self.models['Vendor'].objects.create(name='Vendor contoh', contact='vendor@example.invalid', created_by=self.approver)
        quote = self.models['Quotation'].objects.create(revision=revision, vendor=vendor, reference='Q-1', quoted_on=date(2026, 10, 22), valid_until=date(2026, 10, 25), fulfillment_days=1, total_minor=10000, created_by=self.approver)
        self.models['QuotationItem'].objects.create(quotation=quote, revision_item=item, unit_price_minor=1000, line_total_minor=10000)
        order = self.models['PurchaseOrder'].objects.create(request=self.request, revision=revision, quotation=quote, vendor=vendor, vendor_name=vendor.name, vendor_contact=vendor.contact, kind='GOODS', destination='Kantor', total_minor=10000, selection_reason='Sesuai kebutuhan', single_source_reason='Satu vendor tersedia', issued_by=self.approver)
        order_item = self.models['PurchaseOrderItem'].objects.create(order=order, revision_item=item, position=1, name='Kursi', unit='unit', qty_milli=10000, unit_price_minor=1000, line_total_minor=10000)
        return order, order_item

    def rejects_update(self, obj, **changes):
        with self.assertRaises(IntegrityError), transaction.atomic():
            type(obj).objects.filter(pk=obj.pk).update(**changes)

    def test_TC04_draft_allows_incomplete_header_but_validates_kind_and_ranges(self):
        self.assertIsNone(self.request.needed_on)
        for values in [dict(kind='OTHER'), dict(status='OTHER'), dict(version=0), dict(current_revision_number=-1), dict(title='x'*201), dict(destination='x'*501)]:
            with self.subTest(values=list(values)):
                self.rejects_update(self.request, **values)

    def test_TC04_items_require_positive_scaled_values_and_unique_position(self):
        model = self.models['RequestItem']
        item = model.objects.create(request=self.request, position=1, name='Kursi', unit='unit', qty_milli=10000, estimated_unit_price_minor=1000)
        for values in [dict(qty_milli=0), dict(qty_milli=-1), dict(estimated_unit_price_minor=0), dict(position=0), dict(name='   '), dict(unit='x'*41)]:
            with self.subTest(values=values):
                self.rejects_update(item, **values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            model.objects.create(request=self.request, position=1, name='Meja', unit='unit', qty_milli=1000, estimated_unit_price_minor=100)

    def test_TC06_revisions_and_approval_decisions_cannot_be_duplicated(self):
        revision = self.create_revision()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_revision()
        decision = self.models['ApprovalDecision'].objects.create(revision=revision, actor=self.approver, requester_at_decision=self.owner, decision='APPROVE')
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.models['ApprovalDecision'].objects.create(revision=revision, actor=self.approver, requester_at_decision=self.owner, decision='REJECT', reason='Tidak diperlukan')
        for values in [dict(actor=self.owner), dict(decision='OTHER'), dict(decision='REJECT', reason=''), dict(decision='REQUEST_CHANGES', reason='   ')]:
            with self.subTest(values=values):
                self.rejects_update(decision, **values)
        for values in [dict(number=0), dict(title=''), dict(estimated_total_minor=-1), dict(kind='OTHER')]:
            with self.subTest(values=values):
                self.rejects_update(revision, **values)

    def test_TC11_one_order_per_request_and_quotation_including_terminal_orders(self):
        order, item = self.create_order()
        order.status='CANCELLED';order.closed_by=self.approver;order.closed_at=timezone.now();order.closed_reason='Tidak dilanjutkan';order.save()
        order.pk=uuid4();order.number='PO-'+str(uuid4())
        with self.assertRaises(IntegrityError), transaction.atomic():
            order.save(force_insert=True)

    def test_TC11_quote_and_order_rows_reject_duplicates_and_invalid_dates(self):
        order, item = self.create_order()
        quote_item = order.quotation.items.get()
        self.rejects_update(order.quotation, valid_until=date(2026, 10, 21))
        self.rejects_update(order.quotation, fulfillment_days=-1)
        self.rejects_update(quote_item, unit_price_minor=0)
        for model, values in [
            (self.models['QuotationItem'], dict(quotation=order.quotation, revision_item=item.revision_item, unit_price_minor=100, line_total_minor=1000)),
            (self.models['PurchaseOrderItem'], dict(order=order, revision_item=item.revision_item, position=2, name='Ulang', unit='unit', qty_milli=1000, unit_price_minor=100, line_total_minor=100)),
        ]:
            with self.subTest(model=model.__name__), self.assertRaises(IntegrityError), transaction.atomic():
                model.objects.create(**values)

    def test_TC11_order_closure_metadata_matches_terminal_status(self):
        order, item = self.create_order()
        for values in [dict(status='OTHER'), dict(status='CANCELLED'), dict(status='CLOSED_SHORT'), dict(closed_reason='Ada alasan'), dict(closed_by=self.approver, closed_at=timezone.now(), closed_reason='Alasan')]:
            with self.subTest(values=values):
                self.rejects_update(order, **values)

    def test_TC13_receipts_validate_period_evidence_and_nonempty_quantities(self):
        order, item = self.create_order()
        receipt=self.models['Receipt'].objects.create(order=order, kind='GOODS', reference='SJ-1', evidence_type='GOODS_DELIVERY', confirmed_by=self.approver)
        row=self.models['ReceiptItem'].objects.create(receipt=receipt, order_item=item, accepted_milli=6000, rejected_milli=2000, rejection_reason='Rusak')
        for values in [dict(accepted_milli=-1), dict(rejected_milli=-1), dict(accepted_milli=0,rejected_milli=0), dict(rejection_reason='   ')]:
            with self.subTest(values=values):
                self.rejects_update(row, **values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.models['ReceiptItem'].objects.create(receipt=receipt, order_item=item, accepted_milli=1)
        for values in [dict(kind='SERVICES'), dict(evidence_type='SERVICE_REPORT'), dict(service_started_on=date(2026,10,20)), dict(reference='')]:
            with self.subTest(values=values):
                self.rejects_update(receipt, **values)
        service=self.models['Receipt'].objects.create(order=order, kind='SERVICES', reference='BA-1', evidence_type='SERVICE_ACCEPTANCE', service_started_on=date(2026,10,20),service_ended_on=date(2026,10,21), confirmed_by=self.approver)
        self.rejects_update(service, service_ended_on=date(2026,10,19))
        self.rejects_update(service, service_started_on=None)

    def test_TC13_foreign_keys_reject_missing_documents(self):
        # A valid FK can still point to the wrong aggregate; services must reject
        # that case later. This test covers absent parents, which the DB owns.
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.models['RequestItem'].objects.create(request_id=uuid4(), position=1, name='Kursi', unit='unit', qty_milli=1000, estimated_unit_price_minor=100)
            self.check_constraints()

    def check_constraints(self):
        from django.db import connection
        connection.check_constraints()

    def test_TC13_historical_parents_and_actors_are_protected(self):
        order, item=self.create_order()
        receipt=self.models['Receipt'].objects.create(order=order, kind='GOODS', reference='SJ-1', evidence_type='GOODS_DELIVERY', confirmed_by=self.approver)
        self.models['ReceiptItem'].objects.create(receipt=receipt,order_item=item,accepted_milli=1000)
        for parent in [self.owner,self.approver,self.request,order.revision,item.revision_item,order.quotation,order.vendor,order,item,receipt]:
            with self.subTest(parent=type(parent).__name__), self.assertRaises(ProtectedError):
                parent.delete()

    def test_TC18_actor_nonce_is_unique_and_audit_role_is_valid(self):
        values=dict(actor=self.owner,nonce=uuid4(),action='request.create',target_type='REQUEST',target_key='new-request',payload_hash='a'*64,result_type='REQUEST',result_id=str(self.request.pk))
        row=self.models['ActionReceipt'].objects.create(**values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.models['ActionReceipt'].objects.create(**values)
        event=self.models['AuditEvent'].objects.create(request=self.request,actor=self.owner,actor_name=self.owner.username,actor_role='REQUESTER',action='request.create',target_type='REQUEST',target_id=str(self.request.pk),changes={})
        self.rejects_update(event,actor_role='OTHER')
