# filepath: procurement/selectors.py
from typing import TypedDict
from uuid import UUID

from django.db.models import Case, CharField, F, Q, QuerySet, When
from django.db.models import prefetch_related_objects
from django.core.exceptions import PermissionDenied

from accounts.models import Role, User
from procurement.models import ApprovalDecision, Decision, PurchaseOrder, PurchaseRequest, Quotation, ReceiptItem, RequestStatus
from procurement.quotations import quotation_issues
from django.utils import timezone
from procurement.policies import active_actor


def visible_requests(actor: User) -> QuerySet[PurchaseRequest]:
    current=active_actor(actor.pk)
    queryset=PurchaseRequest.objects.select_related('requester','order')
    if current.role == Role.REQUESTER:
        return queryset.filter(requester_id=current.pk)
    if current.role == Role.RECEIVER:
        return queryset.filter(order__isnull=False)
    if current.role in (Role.APPROVER,Role.PROCUREMENT,Role.ADMIN):
        return queryset
    return queryset.none()


def visible_orders(actor: User) -> QuerySet[PurchaseOrder]:
    return PurchaseOrder.objects.filter(request_id__in=visible_requests(actor).values('pk')).select_related('request')


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


def comparison_rows(revision, quotations=None):
    if revision is None:
        return []
    prefetch_related_objects([revision], 'items')
    today = timezone.localdate()
    result = []
    candidates = quotations if quotations is not None else revision.quotations.select_related('vendor').prefetch_related('items__revision_item').order_by('total_minor','fulfillment_days','pk')
    for quote in candidates:
        result.append(dict(quote=quote, issues=quotation_issues(quote, revision, today),
                           lines=sorted(quote.items.all(), key=lambda row: row.revision_item.position)))
    return result


class OrderBalance(TypedDict):
    ordered_milli: int
    accepted_milli: int
    rejected_milli: int
    remaining_milli: int


def operational_stage(target: PurchaseRequest) -> str:
    try:
        return target.order.status
    except PurchaseOrder.DoesNotExist:
        return target.status


def order_balances(order: PurchaseOrder) -> dict[UUID, OrderBalance]:
    balances = {item.pk: OrderBalance(ordered_milli=item.qty_milli,accepted_milli=0,rejected_milli=0,
                                     remaining_milli=item.qty_milli) for item in order.items.all()}
    lines = ReceiptItem.objects.filter(receipt__order=order).values_list('order_item_id','accepted_milli','rejected_milli')
    # Python totals preserve histories whose aggregate exceeds SQLite's integer SUM range.
    for item_id,accepted,rejected in lines.iterator(chunk_size=1000):
        balance = balances[item_id]
        balance['accepted_milli'] += accepted
        balance['rejected_milli'] += rejected
        balance['remaining_milli'] -= accepted
    return balances


def request_tracking_query(actor: User, *, query: str = '', kind: str = '', stage: str = '') -> QuerySet[PurchaseRequest]:
    queryset = visible_requests(actor).annotate(
        _stage=Case(When(order__isnull=False,then=F('order__status')),default=F('status'),output_field=CharField()))
    if query:
        queryset = queryset.filter(Q(number__icontains=query)|Q(title__icontains=query))
    if kind:
        queryset = queryset.filter(kind=kind)
    if stage:
        queryset = queryset.filter(_stage=stage)
    return queryset.order_by('-created_at','-pk')


def order_tracking_query(actor: User, *, query: str = '', kind: str = '', stage: str = '') -> QuerySet[PurchaseOrder]:
    queryset = visible_orders(actor)
    if query:
        queryset = queryset.filter(Q(number__icontains=query)|Q(request__number__icontains=query)|Q(request__title__icontains=query))
    if kind:
        queryset = queryset.filter(kind=kind)
    if stage:
        queryset = queryset.filter(status=stage)
    return queryset.order_by('-issued_at','-pk')
