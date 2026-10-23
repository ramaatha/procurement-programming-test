from importlib import import_module, util
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from accounts.models import Role, User
from common.errors import ConflictError
from procurement.models import ActionReceipt, Receipt
from procurement.tests.factories import context, issued, user
from procurement.tests.receipt_fixtures import receipt_data


class ClosureTests(TestCase):
    def setUp(self):
        from procurement.services import orders
        self.assertTrue(hasattr(orders,'close_order'),'Closure service missing')
        self.close = orders.close_order
        self.order,self.actor = issued(),user(Role.APPROVER)

    def test_cancel_without_accepted_and_close_short_after_partial(self):
        post = import_module('procurement.services.receipts').post_receipt
        receiver = user(Role.RECEIVER)
        for accepted,status in [('0','CANCELLED'),('6','CLOSED_SHORT')]:
            order = issued()
            result = post(context(receiver,order),order_id=order.pk,data=receipt_data(order,accepted))
            order.refresh_from_db()
            closed = self.close(context(self.actor,order),order_id=order.pk,reason='Tidak dilanjutkan')
            self.assertEqual((closed.status,closed.closed_by_id,closed.closed_reason),(status,self.actor.pk,'Tidak dilanjutkan'))
            self.assertEqual(result.items.get().accepted_milli,int(accepted)*1000)
            with self.assertRaises(ConflictError):
                post(context(receiver,closed),order_id=closed.pk,data=receipt_data(closed))

    def test_owner_cannot_close_after_role_change(self):
        owner = self.order.request.requester
        User.objects.filter(pk=owner.pk).update(role=Role.APPROVER)
        with self.assertRaises(PermissionDenied):
            self.close(context(owner,self.order),order_id=self.order.pk,reason='Batal')

    def test_reason_role_terminal_and_replay(self):
        with self.assertRaises(ValidationError):
            self.close(context(self.actor,self.order),order_id=self.order.pk,reason=' ')
        for role in [Role.ADMIN,Role.RECEIVER,Role.REQUESTER,Role.PROCUREMENT]:
            with self.subTest(role=role),self.assertRaises(PermissionDenied):
                self.close(context(user(role),self.order),order_id=self.order.pk,reason='Batal')
        ctx = context(self.actor,self.order)
        first = self.close(ctx,order_id=self.order.pk,reason='Batal')
        self.assertEqual(self.close(ctx,order_id=self.order.pk,reason='Batal').pk,first.pk)
        with self.assertRaises(ConflictError):
            self.close(context(self.actor,first),order_id=first.pk,reason='Lagi')

    def test_closure_audit_failure_rolls_back(self):
        before = ActionReceipt.objects.count()
        with patch('procurement.services.orders.AuditEvent.objects.create',side_effect=RuntimeError('audit failed')):
            with self.assertRaises(RuntimeError):
                self.close(context(self.actor,self.order),order_id=self.order.pk,reason='Batal')
        self.order.refresh_from_db()
        self.assertEqual((self.order.status,self.order.version,self.order.closed_at),('ISSUED',1,None))
        self.assertEqual(ActionReceipt.objects.count(),before)
