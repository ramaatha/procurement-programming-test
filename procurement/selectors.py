# filepath: procurement/selectors.py
from django.db.models import QuerySet

from accounts.models import Role, User
from procurement.models import PurchaseRequest
from procurement.policies import active_actor


def visible_requests(actor: User) -> QuerySet[PurchaseRequest]:
    current=active_actor(actor.pk)
    queryset=PurchaseRequest.objects.select_related('requester')
    if current.role == Role.REQUESTER:
        return queryset.filter(requester_id=current.pk)
    if current.role == Role.RECEIVER:
        return queryset.filter(order__isnull=False)
    if current.role in (Role.APPROVER,Role.PROCUREMENT,Role.ADMIN):
        return queryset
    return queryset.none()
