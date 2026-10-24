# filepath: procurement/tests/test_demo_setup.py
import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import TestCase

from accounts.models import User
from procurement.models import AuditEvent, PurchaseRequest, PurchaseOrder, Vendor
from procurement.selectors import order_balances


class DemoSetupTests(TestCase):
    def seed(self, password='Synthetic-local-49620!'):
        out = StringIO()
        with patch.dict(os.environ, {'DEMO_PASSWORD': password}):
            call_command('seed_demo', stdout=out)
        self.assertNotIn(password, out.getvalue())
        return out.getvalue()

    def test_repeat_preserves_accounts_transactions_audit_and_password(self):
        self.seed()
        self.assertEqual(User.objects.count(), 5)
        self.assertEqual(PurchaseRequest.objects.count(), 5)
        self.assertEqual(PurchaseOrder.objects.count(), 3)
        before = (AuditEvent.objects.count(), Vendor.objects.count())
        actor = User.objects.get(username='demo_pemohon')
        actor.role = 'RECEIVER'
        actor.set_password('Changed-locally-97451!')
        actor.save()
        output = self.seed('Another-local-45678!')
        actor.refresh_from_db()
        self.assertEqual(actor.role, 'RECEIVER')
        self.assertTrue(actor.check_password('Changed-locally-97451!'))
        self.assertEqual((AuditEvent.objects.count(), Vendor.objects.count()), before)
        self.assertEqual(PurchaseRequest.objects.count(), 5)
        self.assertIn('G-03', output)

    def test_missing_or_invalid_password_creates_nothing(self):
        for password in ('', '123', '123456'):
            with self.subTest(password=password), self.assertRaises(CommandError):
                self.seed(password)
            self.assertFalse(User.objects.exists())
            self.assertFalse(AuditEvent.objects.exists())

    def test_existing_username_is_not_adopted(self):
        actor = User.objects.create_user(username='demo_pemohon', password='Existing-local-98765!', role='ADMIN')
        with self.assertRaises(CommandError):
            self.seed()
        actor.refresh_from_db()
        self.assertTrue(actor.check_password('Existing-local-98765!'))
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(PurchaseRequest.objects.exists())

    def test_collision_late_in_setup_rolls_back_everything(self):
        Vendor.objects.create(name='DEMO Vendor Peralatan', contact='existing@example.invalid', created_by=User.objects.create_user(username='existing', role='ADMIN'))
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Vendor.objects.count(), 1)
        self.assertFalse(AuditEvent.objects.exists())

    def test_scenarios_scope_snapshot_and_balances(self):
        self.seed()
        partial = PurchaseOrder.objects.get(request__title__startswith='[DEMO G-03]')
        balance = next(iter(order_balances(partial).values()))
        self.assertEqual(balance, dict(ordered_milli=10000, accepted_milli=6000, rejected_milli=2000, remaining_milli=4000))
        self.assertEqual(partial.status, 'PARTIALLY_RECEIVED')
        complete = PurchaseOrder.objects.get(request__title__startswith='[DEMO J-02]')
        self.assertEqual(complete.status, 'RECEIVED')
        self.assertEqual(complete.receipts.get().evidence_type, 'SERVICE_REPORT')
        admin = User.objects.get(username='demo_admin')
        self.client.force_login(admin)
        self.assertContains(self.client.get('/requests/'), '[DEMO G-01]')
        self.assertContains(self.client.get('/orders/'), partial.number)
        self.assertContains(self.client.get(f'/orders/{partial.pk}/print/'), 'DEMO Vendor Peralatan')

    def test_repeat_does_not_restore_advanced_draft(self):
        self.seed()
        from common.actions import ActionContext
        from procurement.services.requests import submit_request
        from uuid import uuid4
        draft = PurchaseRequest.objects.get(title__startswith='[DEMO G-01]')
        submit_request(ActionContext(draft.requester_id, uuid4(), draft.version), request_id=draft.pk)
        count = AuditEvent.objects.count()
        self.seed()
        draft.refresh_from_db()
        self.assertEqual(draft.status, 'SUBMITTED')
        self.assertEqual(AuditEvent.objects.count(), count)

    def test_service_failure_rolls_back_bootstrap_and_all_documents(self):
        with patch('procurement.management.commands.seed_demo.post_receipt', side_effect=RuntimeError('simulated failure')):
            with self.assertRaises(RuntimeError):
                self.seed()
        self.assertFalse(User.objects.exists())
        self.assertFalse(PurchaseRequest.objects.exists())
        self.assertFalse(PurchaseOrder.objects.exists())
        self.assertFalse(Vendor.objects.exists())
        self.assertFalse(AuditEvent.objects.exists())
