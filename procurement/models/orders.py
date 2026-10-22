# filepath: procurement/models/orders.py
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone

from .base import Kind, UUIDModel, integer_check, kind_check, nonblank, text_check
from .requests import PurchaseRequest, RequestRevision, RevisionItem
from .sourcing import Quotation, Vendor


def order_number() -> str:
    return f'PO-{uuid4()}'


class OrderStatus(models.TextChoices):
    ISSUED = 'ISSUED', 'Terbit'
    PARTIALLY_RECEIVED = 'PARTIALLY_RECEIVED', 'Diterima sebagian'
    RECEIVED = 'RECEIVED', 'Diterima lengkap'
    CANCELLED = 'CANCELLED', 'Dibatalkan'
    CLOSED_SHORT = 'CLOSED_SHORT', 'Sisa ditutup'


class PurchaseOrder(UUIDModel):
    number = models.CharField(max_length=100, unique=True, default=order_number, editable=False)
    request = models.OneToOneField(PurchaseRequest, on_delete=models.PROTECT, related_name='order')
    revision = models.ForeignKey(RequestRevision, on_delete=models.PROTECT, related_name='orders')
    quotation = models.OneToOneField(Quotation, on_delete=models.PROTECT, related_name='order')
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='orders')
    vendor_name = models.CharField(max_length=200)
    vendor_contact = models.CharField(max_length=500)
    kind = models.CharField(max_length=8, choices=Kind.choices)
    destination = models.CharField(max_length=500)
    total_minor = models.BigIntegerField()
    selection_reason = models.TextField(max_length=4000)
    single_source_reason = models.TextField(max_length=4000, blank=True, default='')
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.ISSUED)
    version = models.BigIntegerField(default=1)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='issued_orders')
    issued_at = models.DateTimeField(default=timezone.now, editable=False)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='closed_orders')
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_reason = models.TextField(max_length=4000, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            kind_check('po'),
            models.CheckConstraint(condition=models.Q(status__in=OrderStatus.values), name='po_status_valid'),
            integer_check('po','total_minor'), integer_check('po','version',positive=True),
            *[text_check('po',field,limit) for field,limit in [('number',100),('vendor_name',200),('vendor_contact',500),('destination',500),('selection_reason',4000)]],
            text_check('po','single_source_reason',4000,required=False), text_check('po','closed_reason',4000,required=False),
            models.CheckConstraint(
                condition=(models.Q(status__in=[OrderStatus.CANCELLED,OrderStatus.CLOSED_SHORT],closed_by__isnull=False,closed_at__isnull=False)&nonblank('closed_reason'))
                | models.Q(status__in=[OrderStatus.ISSUED,OrderStatus.PARTIALLY_RECEIVED,OrderStatus.RECEIVED],closed_by__isnull=True,closed_at__isnull=True,closed_reason=''),
                name='po_closure_metadata_valid',
            ),
        ]
        indexes = [models.Index(fields=['status','issued_at'], name='po_status_issued_idx')]


class PurchaseOrderItem(UUIDModel):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='items')
    revision_item = models.ForeignKey(RevisionItem, on_delete=models.PROTECT, related_name='order_items')
    position = models.BigIntegerField()
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=40)
    qty_milli = models.BigIntegerField()
    unit_price_minor = models.BigIntegerField()
    line_total_minor = models.BigIntegerField()

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['order','position'], name='order_item_position_unique'),
            models.UniqueConstraint(fields=['order','revision_item'], name='order_revision_item_unique'),
            *[integer_check('poi',field,positive=True) for field in ['position','qty_milli','unit_price_minor']],
            integer_check('poi','line_total_minor'), text_check('poi','name',200), text_check('poi','unit',40),
        ]
