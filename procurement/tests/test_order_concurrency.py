# filepath: procurement/tests/test_order_concurrency.py
from importlib import import_module, util
from time import monotonic
from uuid import uuid4

from django.db import connection
from django.test import TransactionTestCase

from common.actions import ActionContext
from procurement.models import AuditEvent, PurchaseOrder
from procurement.tests.factories import context
from procurement.tests.test_orders import prepared


class OrderConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.assertIsNotNone(util.find_spec('procurement.services.orders'),'Order service missing')
        self.service = import_module('procurement.services.orders')

    def race(self, actions):
        from procurement.tests.order_workers import run_race
        return run_race(connection.settings_dict,actions)

    def job(self, action, ctx, **values):
        return dict(action=action,actor_id=ctx.actor_id,nonce=str(ctx.nonce),version=ctx.expected_version,**values)

    def test_TC18_concurrency_harness_terminates_a_stalled_process(self):
        self.assertIsNotNone(util.find_spec('procurement.tests.order_workers'),'Bounded process harness missing')
        from django.db import connection
        from procurement.tests.order_workers import run_race
        started = monotonic()
        with self.assertRaises(TimeoutError):
            run_race(connection.settings_dict,[dict(action='pause',seconds=5),dict(action='pause',seconds=5)],timeout=0.2)
        self.assertLess(monotonic()-started,4)

    def test_TC11_two_issue_calls_create_one_order_for_same_or_different_nonce(self):
        for same_nonce in [False,True]:
            target,owner,approver,actor = prepared()
            nonce = uuid4()
            contexts = [ActionContext(actor.pk,nonce,target.version),
                        ActionContext(actor.pk,nonce if same_nonce else uuid4(),target.version)]
            results = self.race([self.job('issue',ctx,request_id=str(target.pk)) for ctx in contexts])
            self.assertCountEqual(results,['ok','ok'] if same_nonce else ['ok','conflict'])
            self.assertEqual(PurchaseOrder.objects.filter(request=target).count(),1)
            self.assertEqual(AuditEvent.objects.filter(request=target,action='order.issue').count(),1)

    def test_TC15_cancel_request_and_issue_cannot_both_succeed(self):
        target,owner,approver,actor = prepared()
        issue_ctx,cancel_ctx = context(actor,target),context(owner,target)
        results = self.race([self.job('issue',issue_ctx,request_id=str(target.pk)),
                             self.job('cancel',cancel_ctx,request_id=str(target.pk))])
        self.assertCountEqual(results,['ok','conflict'])
        target.refresh_from_db()
        if results[0]=='ok':
            self.assertEqual(target.status,'APPROVED')
            self.assertEqual(PurchaseOrder.objects.filter(request=target,status='ISSUED').count(),1)
        else:
            self.assertEqual(target.status,'CANCELLED')
            self.assertFalse(PurchaseOrder.objects.filter(request=target).exists())

    def test_TC11_vendor_deactivation_serializes_with_issue_and_keeps_snapshot_if_issued_first(self):
        target,owner,approver,actor = prepared()
        vendor = target.selected_quotation.vendor
        issue_ctx,vendor_ctx = context(actor,target),context(actor,vendor)
        results = self.race([self.job('issue',issue_ctx,request_id=str(target.pk)),
                             self.job('deactivate',vendor_ctx,vendor_id=str(vendor.pk))])
        self.assertEqual(results[1],'ok')
        self.assertIn(results[0],['ok','invalid'])
        vendor.refresh_from_db()
        self.assertFalse(vendor.is_active)
        if results[0]=='ok':
            order = PurchaseOrder.objects.get(request=target)
            self.assertEqual((order.vendor_name,order.vendor_contact),('Vendor pesanan 0','Kontak pesanan'))
        else:
            self.assertFalse(PurchaseOrder.objects.filter(request=target).exists())
