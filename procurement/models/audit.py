# filepath: procurement/models/audit.py
from django.conf import settings
from django.db import models

from accounts.models import Role

from .base import TargetType, UUIDModel, text_check
from .requests import PurchaseRequest


class AuditEvent(UUIDModel):
    request = models.ForeignKey(PurchaseRequest,on_delete=models.PROTECT,null=True,blank=True,related_name='audit_events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='audit_events')
    actor_name = models.CharField(max_length=200)
    actor_role = models.CharField(max_length=20,choices=Role.choices)
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=20,choices=TargetType.choices)
    target_id = models.CharField(max_length=100)
    reason = models.TextField(max_length=4000,blank=True,default='')
    changes = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(actor_role__in=Role.values),name='audit_actor_role_valid'),
            models.CheckConstraint(condition=models.Q(target_type__in=TargetType.values),name='audit_target_type_valid'),
            *[text_check('audit',field,limit) for field,limit in [('actor_name',200),('action',100),('target_id',100)]],
            text_check('audit','reason',4000,required=False),
        ]
        indexes = [models.Index(fields=['request','created_at'], name='audit_request_created_idx')]


class ActionReceipt(UUIDModel):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='action_receipts')
    nonce = models.UUIDField()
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=20,choices=TargetType.choices)
    target_key = models.CharField(max_length=100)
    payload_hash = models.CharField(max_length=64,blank=True,default='')
    result_type = models.CharField(max_length=20,choices=TargetType.choices)
    result_id = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['actor','nonce'],name='action_actor_nonce_unique'),
            models.CheckConstraint(condition=models.Q(target_type__in=TargetType.values),name='action_target_type_valid'),
            models.CheckConstraint(condition=models.Q(result_type__in=TargetType.values),name='action_result_type_valid'),
            *[text_check('action',field,100) for field in ['action','target_key','result_id']],
            text_check('action','payload_hash',64,required=False),
        ]
