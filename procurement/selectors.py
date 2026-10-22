# filepath: procurement/selectors.py
from django.db.models import QuerySet
from django.core.exceptions import PermissionDenied

from accounts.models import Role, User
from procurement.models import ApprovalDecision, Decision, PurchaseOrder, PurchaseRequest, Quotation, RequestStatus
from procurement.quotations import quotation_issues
from django.utils import timezone
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


def approval_queue(actor: User) -> QuerySet[PurchaseRequest]:
    current = active_actor(actor.pk)
    if current.role != Role.APPROVER:
        raise PermissionDenied
    return visible_requests(current).filter(status=RequestStatus.SUBMITTED).exclude(requester_id=current.pk)


def sourcing_revision(target: PurchaseRequest):
    return target.revisions.prefetch_related('items').filter(number=target.current_revision_number).first()


def can_source(actor: User, target: PurchaseRequest) -> bool:
    return (actor.role == Role.PROCUREMENT and target.status == RequestStatus.APPROVED
            and not PurchaseOrder.objects.filter(request=target).exists()
            and ApprovalDecision.objects.filter(revision__request=target,
                                                revision__number=target.current_revision_number,
                                                decision=Decision.APPROVE).exists())


def comparison_rows(revision):
    if revision is None:
        return []
    today = timezone.localdate()
    result = []
    for quote in revision.quotations.select_related('vendor').prefetch_related('items__revision_item').order_by('total_minor','fulfillment_days','pk'):
        result.append(dict(quote=quote, issues=quotation_issues(quote, revision, today),
                           lines=sorted(quote.items.all(), key=lambda row: row.revision_item.position)))
    return result
