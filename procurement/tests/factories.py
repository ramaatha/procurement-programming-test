# filepath: procurement/tests/factories.py
"""Drafts use services; approval/order rows remain fixtures until their services exist."""
from datetime import timedelta
from uuid import UUID, uuid4

from django.db.models import Model
from django.utils import timezone

from accounts.models import Role, User
from common.actions import ActionContext
from common.numbers import line_total, parse_quantity
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
    request = draft(owner, kind=kind)
    request.title = 'Kebutuhan contoh'
    request.reason = 'Pengadaan operasional'
    request.destination = 'Kantor'
    request.needed_on = timezone.localdate() + timedelta(days=3)
    request.status = 'APPROVED'
    request.current_revision_number = 1
    request.save()
    total = line_total(qty_milli, 1000)
    RequestItem.objects.create(request=request, position=1, name='Item contoh', unit='unit', qty_milli=qty_milli, estimated_unit_price_minor=1000)
    revision = RequestRevision.objects.create(request=request, number=1, kind=kind, title=request.title, reason=request.reason, destination=request.destination, needed_on=request.needed_on, estimated_total_minor=total, submitted_by=owner)
    RevisionItem.objects.create(revision=revision, position=1, name='Item contoh', unit='unit', qty_milli=qty_milli, estimated_unit_price_minor=1000, line_total_minor=total)
    ApprovalDecision.objects.create(revision=revision, actor=approver, requester_at_decision=owner, decision='APPROVE')
    return request


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
