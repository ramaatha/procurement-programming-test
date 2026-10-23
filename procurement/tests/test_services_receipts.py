from datetime import timedelta
from importlib import import_module, util

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Role
from procurement.models import Kind
from procurement.tests.factories import context, issued, user
from procurement.tests.receipt_fixtures import receipt_data


class ServiceReceiptTests(TestCase):
    def test_service_period_and_evidence_required_and_server_dates_saved(self):
        self.assertIsNotNone(util.find_spec('procurement.services.receipts'),'Receipt service missing')
        post = import_module('procurement.services.receipts').post_receipt
        order, actor = issued(kind=Kind.SERVICES), user(Role.RECEIVER)
        today = timezone.localdate()
        good = dict(evidence_type='SERVICE_REPORT',service_started_on=today-timedelta(days=1),service_ended_on=today)
        for change in [dict(service_started_on=None),dict(service_ended_on=None),
                       dict(service_started_on=today+timedelta(days=1)),
                       dict(service_ended_on=today+timedelta(days=1)),dict(evidence_type='GOODS_DELIVERY')]:
            with self.subTest(change=change),self.assertRaises(ValidationError):
                post(context(actor,order),order_id=order.pk,data=receipt_data(order,**(good|change)))
        result = post(context(actor,order),order_id=order.pk,data=receipt_data(order,**good))
        self.assertEqual((result.kind,result.service_ended_on,timezone.localdate(result.confirmed_at)),('SERVICES',today,today))
        self.assertEqual(result.items.get().order_item.unit,'unit')
