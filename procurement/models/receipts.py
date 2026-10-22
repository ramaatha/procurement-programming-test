# filepath: procurement/models/receipts.py
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone

from .base import Kind, UUIDModel, integer_check, kind_check, nonblank, text_check
from .orders import PurchaseOrder, PurchaseOrderItem


def receipt_number() -> str:
    return f'RCV-{uuid4()}'


class EvidenceType(models.TextChoices):
    GOODS_DELIVERY = 'GOODS_DELIVERY', 'Surat jalan'
    SERVICE_REPORT = 'SERVICE_REPORT', 'Laporan pekerjaan'
    SERVICE_ACCEPTANCE = 'SERVICE_ACCEPTANCE', 'Berita acara jasa'


class Receipt(UUIDModel):
    number = models.CharField(max_length=100, unique=True, default=receipt_number, editable=False)
    order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='receipts')
    kind = models.CharField(max_length=8, choices=Kind.choices)
    reference = models.CharField(max_length=100)
    notes = models.TextField(max_length=4000, blank=True, default='')
    evidence_type = models.CharField(max_length=20, choices=EvidenceType.choices)
    service_started_on = models.DateField(null=True, blank=True)
    service_ended_on = models.DateField(null=True, blank=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='confirmed_receipts')
    confirmed_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            kind_check('rcv'), text_check('rcv','number',100), text_check('rcv','reference',100), text_check('rcv','notes',4000,required=False),
            models.CheckConstraint(
                condition=models.Q(kind=Kind.GOODS,evidence_type=EvidenceType.GOODS_DELIVERY,service_started_on__isnull=True,service_ended_on__isnull=True)
                | models.Q(kind=Kind.SERVICES,evidence_type__in=[EvidenceType.SERVICE_REPORT,EvidenceType.SERVICE_ACCEPTANCE],service_started_on__isnull=False,service_ended_on__isnull=False,service_started_on__lte=models.F('service_ended_on')),
                name='receipt_evidence_period_valid',
            ),
        ]


class ReceiptItem(UUIDModel):
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, related_name='items')
    order_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.PROTECT, related_name='receipt_items')
    accepted_milli = models.BigIntegerField(default=0)
    rejected_milli = models.BigIntegerField(default=0)
    rejection_reason = models.TextField(max_length=4000, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['receipt','order_item'], name='receipt_order_item_unique'),
            integer_check('rci','accepted_milli'), integer_check('rci','rejected_milli'),
            models.CheckConstraint(condition=models.Q(accepted_milli__gt=0)|models.Q(rejected_milli__gt=0),name='receipt_item_nonzero'),
            models.CheckConstraint(condition=models.Q(rejected_milli=0)|nonblank('rejection_reason'),name='receipt_rejection_reason'),
            text_check('rci','rejection_reason',4000,required=False),
        ]
