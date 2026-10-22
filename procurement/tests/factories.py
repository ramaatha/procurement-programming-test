# filepath: procurement/tests/factories.py
"""Business fixtures follow the same services as application mutations."""
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
    from procurement.services.orders import issue_order
    from procurement.inputs import QuotationInput, QuoteLineInput
    from procurement.services.sourcing import save_quotation, save_vendor, select_quotation
    request = _approved(user(Role.REQUESTER), user(Role.APPROVER), kind, parse_quantity(quantity))
    revision = request.revisions.get(number=1)
    revision_item = revision.items.get()
    actor = user(Role.PROCUREMENT)
    vendor = save_vendor(ActionContext(actor.pk, uuid4(), None), vendor_id=None,
                         name='Vendor contoh', contact='vendor@example.invalid', is_active=True)
    data = QuotationInput(vendor.pk, 'Q-CONTOH', timezone.localdate(),
                          timezone.localdate()+timedelta(days=7), 1,
                          (QuoteLineInput(revision_item.pk, '10.00'),))
    quote = save_quotation(context(actor, request), request_id=request.pk, quotation_id=None, data=data)
    request.refresh_from_db()
    request = select_quotation(context(actor, request), request_id=request.pk, quotation_id=quote.pk,
                                reason='Sesuai kebutuhan', single_source_reason='Satu sumber tersedia')
    return issue_order(context(actor,request),request_id=request.pk)


def context(actor: User, target: Model, *, nonce: UUID | None = None) -> ActionContext:
    return ActionContext(actor_id=actor.pk, nonce=nonce or uuid4(), expected_version=target.version)
