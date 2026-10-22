# filepath: procurement/tests/factories.py
"""Requests and approvals use services; order rows remain fixtures until available."""
from datetime import timedelta
from uuid import UUID, uuid4

from django.db.models import Model
from django.utils import timezone

from accounts.models import Role, User
from common.actions import ActionContext
from common.numbers import format_quantity, parse_quantity
from procurement.models import (
    ApprovalDecision, Kind, PurchaseOrder, PurchaseOrderItem, PurchaseRequest,
    Quotation, QuotationItem, RequestItem, RequestRevision, RevisionItem, Vendor,
)


def user(role: str) -> User:
    return User.objects.create_user(username=f'fixture-{uuid4().hex}', role=role)


def draft(owner: User, *, kind: str = Kind.GOODS) -> PurchaseRequest:
    from procurement.inputs import DraftInput
    from procurement.services.requests import save_draft
    return save_draft(ActionContext(owner.pk,uuid4(),None),request_id=None,data=DraftInput(str(kind),'','','',None,()))


def _approved(owner: User, approver: User, kind: str, qty_milli: int) -> PurchaseRequest:
    from procurement.inputs import DraftInput, RequestLineInput
    from procurement.services.requests import review_request, save_draft, submit_request
    data = DraftInput(str(kind), 'Kebutuhan contoh', 'Pengadaan operasional', 'Kantor',
                      timezone.localdate() + timedelta(days=3),
                      (RequestLineInput('Item contoh', 'unit', format_quantity(qty_milli), '10.00'),))
    request = save_draft(ActionContext(owner.pk, uuid4(), None), request_id=None, data=data)
    request = submit_request(context(owner, request), request_id=request.pk)
    return review_request(context(approver, request), request_id=request.pk, decision='APPROVE', reason='')


def approved(owner: User, approver: User, *, kind: str = Kind.GOODS) -> PurchaseRequest:
    return _approved(owner, approver, kind, 10000)


def issued(*, quantity: str = '10', kind: str = Kind.GOODS) -> PurchaseOrder:
    request = _approved(user(Role.REQUESTER), user(Role.APPROVER), kind, parse_quantity(quantity))
    revision = request.revisions.get(number=1)
    revision_item = revision.items.get()
    actor = user(Role.PROCUREMENT)
    vendor = Vendor.objects.create(name='Vendor contoh', contact='vendor@example.invalid', created_by=actor)
    quote = Quotation.objects.create(revision=revision, vendor=vendor, reference='Q-CONTOH', quoted_on=timezone.localdate(), valid_until=timezone.localdate()+timedelta(days=7), fulfillment_days=1, total_minor=revision.estimated_total_minor, created_by=actor)
    QuotationItem.objects.create(quotation=quote, revision_item=revision_item, unit_price_minor=1000, line_total_minor=revision.estimated_total_minor)
    request.selected_quotation=quote
    request.selection_reason='Sesuai kebutuhan'
    request.single_source_reason='Satu sumber tersedia'
    request.save()
    order=PurchaseOrder.objects.create(request=request, revision=revision, quotation=quote, vendor=vendor, vendor_name=vendor.name, vendor_contact=vendor.contact, kind=kind, destination=request.destination, total_minor=revision.estimated_total_minor, selection_reason=request.selection_reason, single_source_reason=request.single_source_reason, issued_by=actor)
    PurchaseOrderItem.objects.create(order=order, revision_item=revision_item, position=1, name=revision_item.name, unit=revision_item.unit, qty_milli=revision_item.qty_milli, unit_price_minor=1000, line_total_minor=revision.estimated_total_minor)
    return order


def context(actor: User, target: Model, *, nonce: UUID | None = None) -> ActionContext:
    return ActionContext(actor_id=actor.pk, nonce=nonce or uuid4(), expected_version=target.version)
