# filepath: accounts/policies.py
from django.core.exceptions import PermissionDenied

from accounts.models import User


def require_role(actor: User, *roles: str) -> None:
    if not getattr(actor, 'is_authenticated', False) or actor.pk is None:
        raise PermissionDenied
    current = User.objects.filter(pk=actor.pk).values('is_active', 'role').first()
    if current is None or not current['is_active'] or current['role'] not in roles:
        raise PermissionDenied
