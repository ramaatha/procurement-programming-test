from uuid import uuid4

from django.db import connection
from django.test import TransactionTestCase

from accounts.models import Role
from procurement.models import Receipt, ReceiptItem
from procurement.tests.factories import issued, user
from procurement.tests.order_workers import run_race


class ReceiptConcurrencyTests(TransactionTestCase):
    def job(self,action,order,actor,nonce=None):
        return dict(action=action,actor_id=actor.pk,nonce=str(nonce or uuid4()),version=order.version,order_id=str(order.pk))

    def test_two_receipts_cannot_over_receive_and_same_nonce_replays_once(self):
        for same_nonce in (False,True):
            order,actor = issued(),user(Role.RECEIVER)
            nonce = uuid4()
            results = run_race(connection.settings_dict,[self.job('receipt',order,actor,nonce),self.job('receipt',order,actor,nonce if same_nonce else None)])
            self.assertCountEqual(results,['ok','ok'] if same_nonce else ['ok','conflict'])
            self.assertEqual(Receipt.objects.filter(order=order).count(),1)
            self.assertEqual(ReceiptItem.objects.get(receipt__order=order).accepted_milli,6000)
            order.refresh_from_db()
            self.assertEqual((order.status,order.version),('PARTIALLY_RECEIVED',2))

    def test_close_and_receive_only_one_can_win_at_same_version(self):
        order,receiver,approver = issued(),user(Role.RECEIVER),user(Role.APPROVER)
        results = run_race(connection.settings_dict,[self.job('receipt',order,receiver),self.job('close',order,approver)])
        self.assertCountEqual(results,['ok','conflict'])
        order.refresh_from_db()
        self.assertEqual(order.version,2)
        if results[0]=='ok':
            self.assertEqual(order.status,'PARTIALLY_RECEIVED')
            self.assertEqual(Receipt.objects.filter(order=order).count(),1)
        else:
            self.assertEqual(order.status,'CANCELLED')
            self.assertFalse(Receipt.objects.filter(order=order).exists())
