# filepath: procurement/models/base.py
from uuid import uuid4

from django.db import models
from django.db.models.functions import Length, Trim
from django.db.models.lookups import GreaterThan, LessThanOrEqual
from django.utils import timezone

MAX_INT64 = 9223372036854775807


class Kind(models.TextChoices):
    GOODS = 'GOODS', 'Barang'
    SERVICES = 'SERVICES', 'Jasa'


class TargetType(models.TextChoices):
    USER = 'USER', 'Akun'
    VENDOR = 'VENDOR', 'Vendor'
    REQUEST = 'REQUEST', 'Request'
    QUOTATION = 'QUOTATION', 'Penawaran'
    ORDER = 'ORDER', 'PO'
    RECEIPT = 'RECEIPT', 'Penerimaan'


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        abstract = True


def nonblank(field: str):
    return GreaterThan(Length(Trim(field)), 0)


def text_check(prefix: str, field: str, limit: int, *, required: bool = True):
    condition = LessThanOrEqual(Length(field), limit)
    if required:
        condition &= nonblank(field)
    return models.CheckConstraint(condition=condition, name=f'{prefix}_{field}_text')


def integer_check(prefix: str, field: str, *, positive: bool = False):
    return models.CheckConstraint(
        condition=models.Q(**{f'{field}__gte': 1 if positive else 0, f'{field}__lte': MAX_INT64}),
        name=f'{prefix}_{field}_range',
    )


def kind_check(prefix: str):
    return models.CheckConstraint(condition=models.Q(kind__in=Kind.values), name=f'{prefix}_kind_valid')
