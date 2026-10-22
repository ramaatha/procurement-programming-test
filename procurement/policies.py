# filepath: procurement/policies.py
from django.core.exceptions import PermissionDenied

from accounts.models import Role, User
from procurement.models import PurchaseRequest


def active_actor(actor_id: int) -> User:
    if type(actor_id) is not int:
        raise PermissionDenied
    actor=User.objects.filter(pk=actor_id,is_active=True).first()
    if actor is None:
        raise PermissionDenied
    return actor


def require_request_owner(actor: User, target: PurchaseRequest) -> None:
    current=active_actor(actor.pk)
    if current.role != Role.REQUESTER or target.requester_id != current.pk:
        raise PermissionDenied


def require_request_reviewer(actor: User, target: PurchaseRequest) -> None:
    current = active_actor(actor.pk)
    if current.role != Role.APPROVER or target.requester_id == current.pk:
        raise PermissionDenied


def require_procurement(actor: User) -> None:
    if active_actor(actor.pk).role != Role.PROCUREMENT:
        raise PermissionDenied


def require_vendor_manager(actor: User) -> None:
    if active_actor(actor.pk).role not in (Role.PROCUREMENT, Role.ADMIN):
        raise PermissionDenied
