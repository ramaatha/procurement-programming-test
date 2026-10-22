# filepath: accounts/services.py
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.debug import sensitive_variables

from accounts.models import Role, User
from accounts.policies import require_role
from common.actions import ActionContext, check_version, find_replay, payload_hash, record_action, resolve_result
from common.errors import ConflictError
from common.numbers import MAX_INT64
from procurement.models import AuditEvent, TargetType


def _admin(actor_id: int) -> User:
    actor = User.objects.filter(pk=actor_id).first()
    if actor is None:
        raise PermissionDenied
    require_role(actor, Role.ADMIN)
    return actor


def _identity(username: str, role: str, is_active: bool) -> str:
    if not isinstance(username, str):
        raise ValidationError({'username': 'Username tidak valid.'})
    username = User.normalize_username(username.strip())
    if not username or len(username) > 150:
        raise ValidationError({'username': 'Isi username maksimal 150 karakter.'})
    if role not in Role.values:
        raise ValidationError({'role': 'Pilih peran yang tersedia.'})
    if type(is_active) is not bool:
        raise ValidationError({'is_active': 'Status akun tidak valid.'})
    return username


@sensitive_variables('password')
def _password(password: str, target: User, field: str) -> None:
    if not isinstance(password, str) or not password or len(password) > 4096:
        raise ValidationError({field: 'Isi password yang valid, maksimal 4096 karakter.'})
    try:
        validate_password(password, user=target)
    except ValidationError as error:
        raise ValidationError({field: error.messages}) from None


def _metadata(target: User) -> dict:
    return dict(username=target.username, role=target.role, is_active=target.is_active, version=target.version)


def _advance_version(target: User) -> None:
    if target.version >= MAX_INT64:
        raise ValidationError('Versi akun sudah mencapai batas penyimpanan.')
    target.version += 1


def _audit(actor: User, target: User, action: str, changes: dict) -> None:
    AuditEvent.objects.create(
        actor=actor, actor_name=actor.username, actor_role=actor.role,
        action=action, target_type=TargetType.USER, target_id=str(target.pk), changes=changes,
    )


@sensitive_variables('initial_password')
def save_user(ctx: ActionContext, *, user_id: int | None, username: str, role: str, is_active: bool, initial_password: str | None = None) -> User:
    with transaction.atomic():
        actor = _admin(ctx.actor_id)
        creating = user_id is None
        action = 'account.create' if creating else 'account.edit'
        if not creating and (type(user_id) is not int or user_id < 1):
            raise ValidationError('Akun tidak valid.')
        target_key = 'new-user' if creating else str(user_id)
        target = User() if creating else get_object_or_404(User, pk=user_id)
        username = _identity(username, role, is_active)
        role = str(role)
        digest = '' if creating else payload_hash(dict(username=username,role=role,is_active=is_active,expected_version=ctx.expected_version))
        replay = find_replay(ctx, action=action, target_type=TargetType.USER, target_key=target_key, digest=digest)
        if replay is not None:
            return resolve_result(replay)
        if creating:
            if ctx.expected_version is not None:
                raise ConflictError()
        else:
            check_version(target, ctx.expected_version)
            if initial_password is not None:
                raise ValidationError('Gunakan halaman reset password untuk mengganti password.')
            if target.role == Role.ADMIN and target.is_active and (role != Role.ADMIN or not is_active):
                if not User.objects.filter(role=Role.ADMIN, is_active=True).exclude(pk=target.pk).exists():
                    raise ValidationError('Admin aktif terakhir tidak dapat dinonaktifkan atau diubah perannya.')
        before = {} if creating else _metadata(target)
        target.username, target.role, target.is_active = username, role, is_active
        target.full_clean(exclude=['password'], validate_unique=False)
        if User.objects.filter(username=username).exclude(pk=target.pk).exists():
            raise ValidationError({'username': 'Username sudah digunakan.'})
        if creating:
            _password(initial_password, target, 'initial_password')
            target.set_password(initial_password)
        else:
            _advance_version(target)
        target.save()
        _audit(actor, target, action, dict(before=before, after=_metadata(target)))
        record_action(ctx, action=action, target_type=TargetType.USER, target_key=target_key, digest=digest, result=target)
        return target


@sensitive_variables('new_password')
def reset_password(ctx: ActionContext, *, user_id: int, new_password: str) -> User:
    with transaction.atomic():
        actor = _admin(ctx.actor_id)
        if type(user_id) is not int or user_id < 1:
            raise ValidationError('Akun tidak valid.')
        target = get_object_or_404(User, pk=user_id)
        replay = find_replay(ctx, action='account.password', target_type=TargetType.USER, target_key=str(user_id), digest='')
        if replay is not None:
            return resolve_result(replay)
        check_version(target, ctx.expected_version)
        _password(new_password, target, 'new_password')
        target.set_password(new_password)
        _advance_version(target)
        target.save(update_fields=['password','version'])
        _audit(actor, target, 'account.password', dict(credential_reset=True, version=target.version))
        record_action(ctx, action='account.password', target_type=TargetType.USER, target_key=str(user_id), digest='', result=target)
        return target
