# filepath: common/actions.py
import hashlib
import json
import re
from dataclasses import dataclass
from uuid import UUID, uuid4

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import connection, models

from procurement.models import ActionReceipt, PurchaseOrder, PurchaseRequest, Quotation, Receipt, TargetType, Vendor

from .errors import ConflictError
from .numbers import MAX_INT64

_SALT = 'procurement.action.v1'
_SINGLE_USE_ACTIONS = frozenset({'account.create', 'account.password'})


@dataclass(frozen=True)
class ActionContext:
    actor_id: int
    nonce: UUID
    expected_version: int | None

    def __post_init__(self) -> None:
        if type(self.actor_id) is not int or self.actor_id < 1 or not isinstance(self.nonce, UUID):
            raise ValidationError('Konteks aksi tidak valid.')
        if self.expected_version is not None and (type(self.expected_version) is not int or not 1 <= self.expected_version <= MAX_INT64):
            raise ValidationError('Versi data tidak valid.')


def _scope(*, actor_id: int, target_type: str, target_key: str, action: str) -> dict:
    if type(actor_id) is not int or actor_id < 1 or target_type not in TargetType.values:
        raise ValidationError('Scope aksi tidak valid.')
    for value in (target_key, action):
        if not isinstance(value, str) or not value.strip() or len(value) > 100:
            raise ValidationError('Scope aksi tidak valid.')
    return dict(actor_id=actor_id, target_type=target_type, target_key=target_key, action=action)


def make_action_token(*, actor_id: int, target_type: str, target_key: str, action: str) -> str:
    scope = _scope(actor_id=actor_id, target_type=target_type, target_key=target_key, action=action)
    return signing.dumps(scope | {'nonce': str(uuid4())}, salt=_SALT)


def load_action_token(token: str, *, actor_id: int, target_type: str, target_key: str, action: str) -> UUID:
    scope = _scope(actor_id=actor_id, target_type=target_type, target_key=target_key, action=action)
    try:
        if not isinstance(token, str) or len(token) > 2048:
            raise ValueError
        payload = signing.loads(token, salt=_SALT, max_age=86400)
        nonce = UUID(payload['nonce'])
        if payload != scope | {'nonce': str(nonce)}:
            raise ValueError
    except (signing.BadSignature, ValueError, TypeError, KeyError, AttributeError):
        raise ValidationError('Token aksi tidak valid atau kedaluwarsa. Muat ulang halaman.') from None
    return nonce


def _validate_payload(value) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str) or any(sensitive in key.casefold() for sensitive in ('password', 'secret', 'token', 'cookie')):
                raise ValidationError('Payload aksi memuat field yang tidak diizinkan.')
            _validate_payload(nested)
    elif isinstance(value, (tuple, list)):
        for nested in value:
            _validate_payload(nested)
    elif value is not None and type(value) not in (str, int, bool):
        raise ValidationError('Payload aksi harus memakai nilai desimal yang sudah dikanonisasi.')


def payload_hash(payload: dict) -> str:
    if not isinstance(payload, dict):
        raise ValidationError('Payload aksi harus berupa objek.')
    _validate_payload(payload)
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def _require_transaction() -> None:
    if not connection.in_atomic_block:
        raise RuntimeError('Protokol aksi harus dipanggil di dalam transaction.atomic().')


def _check_digest(digest: str, action: str) -> None:
    if action in _SINGLE_USE_ACTIONS:
        valid = digest == ''
    else:
        valid = isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest) is not None
    if not valid:
        raise ValidationError('Ringkasan payload aksi tidak valid.')


def find_replay(ctx: ActionContext, *, action: str, target_type: str, target_key: str, digest: str, replayable: bool = True) -> ActionReceipt | None:
    _require_transaction()
    _scope(actor_id=ctx.actor_id, target_type=target_type, target_key=target_key, action=action)
    _check_digest(digest, action)
    receipt = ActionReceipt.objects.filter(actor_id=ctx.actor_id, nonce=ctx.nonce).first()
    if receipt is None:
        return None
    if not replayable or action in _SINGLE_USE_ACTIONS or (receipt.action, receipt.target_type, receipt.target_key, receipt.payload_hash) != (action, target_type, target_key, digest):
        raise ConflictError()
    return receipt


def check_version(target: models.Model, expected_version: int | None) -> None:
    if type(expected_version) is not int or expected_version < 1 or target.version != expected_version:
        raise ConflictError()


def _result_models() -> dict:
    return {
        TargetType.USER: get_user_model(), TargetType.VENDOR: Vendor,
        TargetType.REQUEST: PurchaseRequest, TargetType.QUOTATION: Quotation,
        TargetType.ORDER: PurchaseOrder, TargetType.RECEIPT: Receipt,
    }


def record_action(ctx: ActionContext, *, action: str, target_type: str, target_key: str, digest: str, result: models.Model) -> ActionReceipt:
    _require_transaction()
    _scope(actor_id=ctx.actor_id, target_type=target_type, target_key=target_key, action=action)
    _check_digest(digest, action)
    result_type = next((key for key, model in _result_models().items() if type(result) is model), None)
    if result_type is None or result.pk is None or result._state.adding:
        raise ValidationError('Hasil aksi tidak valid.')
    return ActionReceipt.objects.create(actor_id=ctx.actor_id, nonce=ctx.nonce, action=action, target_type=target_type, target_key=target_key, payload_hash=digest, result_type=result_type, result_id=str(result.pk))


def resolve_result(receipt: ActionReceipt) -> models.Model:
    model = _result_models().get(receipt.result_type)
    if model is None:
        raise ConflictError('Hasil aksi tidak dapat ditemukan.')
    try:
        return model.objects.get(pk=receipt.result_id)
    except (model.DoesNotExist, ValueError, ValidationError):
        raise ConflictError('Hasil aksi tidak dapat ditemukan.') from None
