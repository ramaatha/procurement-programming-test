# filepath: procurement/models/requests.py
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone

from .base import Kind, UUIDModel, integer_check, kind_check, nonblank, text_check


def request_number() -> str:
    return f'PR-{uuid4()}'


class RequestStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Diajukan'
    CHANGES_REQUESTED = 'CHANGES_REQUESTED', 'Perlu revisi'
    APPROVED = 'APPROVED', 'Disetujui'
    REJECTED = 'REJECTED', 'Ditolak'
    CANCELLED = 'CANCELLED', 'Dibatalkan'


class Decision(models.TextChoices):
    APPROVE = 'APPROVE', 'Setujui'
    REQUEST_CHANGES = 'REQUEST_CHANGES', 'Minta revisi'
    REJECT = 'REJECT', 'Tolak'


class PurchaseRequest(UUIDModel):
    number = models.CharField(max_length=100, default=request_number, unique=True, editable=False)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='purchase_requests')
    kind = models.CharField(max_length=8, choices=Kind.choices)
    title = models.CharField(max_length=200, blank=True, default='')
    reason = models.TextField(max_length=4000, blank=True, default='')
    destination = models.CharField(max_length=500, blank=True, default='')
    needed_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.DRAFT)
    version = models.BigIntegerField(default=1)
    current_revision_number = models.BigIntegerField(default=0)
    selected_quotation = models.ForeignKey('procurement.Quotation', null=True, blank=True, on_delete=models.PROTECT, related_name='selected_for_requests')
    selection_reason = models.TextField(max_length=4000, blank=True, default='')
    single_source_reason = models.TextField(max_length=4000, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            kind_check('pr'),
            models.CheckConstraint(condition=models.Q(status__in=RequestStatus.values), name='pr_status_valid'),
            integer_check('pr', 'version', positive=True),
            integer_check('pr', 'current_revision_number'),
            text_check('pr', 'number', 100),
            *[text_check('pr', field, limit, required=False) for field, limit in [('title',200),('reason',4000),('destination',500),('selection_reason',4000),('single_source_reason',4000)]],
        ]
        indexes = [
            models.Index(fields=['requester','created_at'], name='pr_owner_created_idx'),
            models.Index(fields=['status','created_at'], name='pr_status_created_idx'),
            models.Index(fields=['kind','created_at'], name='pr_kind_created_idx'),
        ]


class RequestItem(UUIDModel):
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name='items')
    position = models.BigIntegerField()
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=40)
    qty_milli = models.BigIntegerField()
    estimated_unit_price_minor = models.BigIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['request','position'], name='request_item_position_unique'),
            *[integer_check('ri', field, positive=True) for field in ['position','qty_milli','estimated_unit_price_minor']],
            text_check('ri', 'name', 200), text_check('ri', 'unit', 40),
        ]


class RequestRevision(UUIDModel):
    request = models.ForeignKey(PurchaseRequest, on_delete=models.PROTECT, related_name='revisions')
    number = models.BigIntegerField()
    kind = models.CharField(max_length=8, choices=Kind.choices)
    title = models.CharField(max_length=200)
    reason = models.TextField(max_length=4000)
    destination = models.CharField(max_length=500)
    needed_on = models.DateField()
    estimated_total_minor = models.BigIntegerField()
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='submitted_revisions')
    submitted_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request','number'], name='request_revision_number_unique'),
            kind_check('rev'), integer_check('rev','number',positive=True), integer_check('rev','estimated_total_minor'),
            text_check('rev','title',200), text_check('rev','reason',4000), text_check('rev','destination',500),
        ]


class RevisionItem(UUIDModel):
    revision = models.ForeignKey(RequestRevision, on_delete=models.PROTECT, related_name='items')
    position = models.BigIntegerField()
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=40)
    qty_milli = models.BigIntegerField()
    estimated_unit_price_minor = models.BigIntegerField()
    line_total_minor = models.BigIntegerField()

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['revision','position'], name='revision_item_position_unique'),
            *[integer_check('rvi', field, positive=True) for field in ['position','qty_milli','estimated_unit_price_minor']],
            integer_check('rvi','line_total_minor'), text_check('rvi','name',200), text_check('rvi','unit',40),
        ]


class ApprovalDecision(UUIDModel):
    revision = models.OneToOneField(RequestRevision, on_delete=models.PROTECT, related_name='approval')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='approval_decisions')
    requester_at_decision = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='received_decisions')
    decision = models.CharField(max_length=20, choices=Decision.choices)
    reason = models.TextField(max_length=4000, blank=True, default='')
    decided_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(decision__in=Decision.values), name='approval_decision_valid'),
            models.CheckConstraint(condition=~models.Q(actor=models.F('requester_at_decision')), name='approval_not_self'),
            models.CheckConstraint(condition=models.Q(decision=Decision.APPROVE) | nonblank('reason'), name='approval_reason_required'),
            text_check('approval','reason',4000,required=False),
        ]
