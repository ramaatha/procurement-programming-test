# filepath: procurement/models/sourcing.py
from django.conf import settings
from django.db import models

from .base import UUIDModel, integer_check, text_check
from .requests import RequestRevision, RevisionItem


class Vendor(UUIDModel):
    name = models.CharField(max_length=200)
    contact = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    version = models.BigIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_vendors')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [text_check('vendor','name',200), text_check('vendor','contact',500), integer_check('vendor','version',positive=True)]


class Quotation(UUIDModel):
    revision = models.ForeignKey(RequestRevision, on_delete=models.PROTECT, related_name='quotations')
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='quotations')
    reference = models.CharField(max_length=100)
    quoted_on = models.DateField()
    valid_until = models.DateField()
    fulfillment_days = models.BigIntegerField()
    total_minor = models.BigIntegerField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_quotations')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            text_check('quote','reference',100), integer_check('quote','fulfillment_days'), integer_check('quote','total_minor'),
            models.CheckConstraint(condition=models.Q(quoted_on__lte=models.F('valid_until')), name='quotation_dates_ordered'),
        ]
        indexes = [models.Index(fields=['revision','vendor'], name='quote_revision_vendor_idx')]


class QuotationItem(UUIDModel):
    quotation = models.ForeignKey(Quotation, on_delete=models.PROTECT, related_name='items')
    revision_item = models.ForeignKey(RevisionItem, on_delete=models.PROTECT, related_name='quotation_items')
    unit_price_minor = models.BigIntegerField()
    line_total_minor = models.BigIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['quotation','revision_item'], name='quote_revision_item_unique'),
            integer_check('qi','unit_price_minor',positive=True), integer_check('qi','line_total_minor'),
        ]
