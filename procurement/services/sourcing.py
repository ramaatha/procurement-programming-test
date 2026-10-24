# filepath: procurement/services/sourcing.py
from datetime import date
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import prefetch_related_objects
from django.shortcuts import get_object_or_404
from django.utils import timezone

from common.actions import ActionContext, check_version, find_replay, payload_hash, record_action, resolve_result
from common.errors import ConflictError
from common.numbers import MAX_INT64, document_total, format_money, line_total, parse_money
from procurement.inputs import QuotationInput, QuoteLineInput
from procurement.models import ApprovalDecision, AuditEvent, Decision, PurchaseRequest, Quotation, QuotationItem, RequestStatus, Vendor
from procurement.policies import active_actor, require_procurement, require_vendor_manager
from procurement.quotations import quotation_issues
from procurement.selectors import visible_requests
from procurement.services.requests import _advance, _clear_selection, _current_revision, _text, _unissued


def _audit(ctx, actor, result, action, target_type, key, digest, *, request=None, reason='', changes=None):
    AuditEvent.objects.create(request=request, actor=actor, actor_name=actor.username, actor_role=actor.role,
                              action=action, target_type=target_type, target_id=str(result.pk),
                              reason=reason, changes=changes or {})
    record_action(ctx, action=action, target_type='REQUEST' if request else target_type,
                  target_key=key, digest=digest, result=result)


def save_vendor(ctx: ActionContext, *, vendor_id: UUID | None, name: str, contact: str, is_active: bool) -> Vendor:
    with transaction.atomic():
        actor = active_actor(ctx.actor_id)
        require_vendor_manager(actor)
        name = _text(name, 200, 'Nama vendor', required=True)
        contact = _text(contact, 500, 'Kontak vendor', required=True)
        if type(is_active) is not bool:
            raise ValidationError('Status vendor tidak valid.')
        creating = vendor_id is None
        target = None if creating else get_object_or_404(Vendor, pk=vendor_id)
        action = 'vendor.create' if creating else 'vendor.edit'
        key = 'new-vendor' if creating else str(target.pk)
        digest = payload_hash(dict(name=name, contact=contact, is_active=is_active, expected_version=ctx.expected_version))
        replay = find_replay(ctx, action=action, target_type='VENDOR', target_key=key, digest=digest)
        if replay is not None:
            return resolve_result(replay)
        if creating:
            if ctx.expected_version is not None:
                raise ConflictError()
            target = Vendor(created_by=actor)
        else:
            check_version(target, ctx.expected_version)
            if target.version >= MAX_INT64:
                raise ValidationError('Versi vendor mencapai batas penyimpanan.')
            target.version += 1
        target.name, target.contact, target.is_active = name, contact, is_active
        target.save()
        _audit(ctx, actor, target, action, 'VENDOR', key, digest,
               changes=dict(is_active=target.is_active, version=target.version))
        return target


def _prepare(data: QuotationInput) -> QuotationInput:
    if not isinstance(data, QuotationInput) or not isinstance(data.vendor_id, UUID):
        raise ValidationError('Data penawaran tidak valid.')
    if type(data.quoted_on) is not date or type(data.valid_until) is not date or data.quoted_on > data.valid_until:
        raise ValidationError('Tanggal penawaran harus berada sebelum atau pada akhir masa berlaku.')
    if type(data.fulfillment_days) is not int or not 0 <= data.fulfillment_days <= MAX_INT64:
        raise ValidationError('Estimasi pemenuhan harus berupa hari bulat mulai dari nol.')
    if not isinstance(data.items, tuple) or not data.items:
        raise ValidationError('Isi seluruh harga item revisi.')
    lines = []
    seen = set()
    for item in data.items:
        if not isinstance(item, QuoteLineInput) or not isinstance(item.revision_item_id, UUID) or item.revision_item_id in seen:
            raise ValidationError('Item penawaran tidak valid atau berulang.')
        seen.add(item.revision_item_id)
        lines.append(QuoteLineInput(item.revision_item_id, format_money(parse_money(item.unit_price))))
    return QuotationInput(data.vendor_id, _text(data.reference, 100, 'Referensi', required=True),
                          data.quoted_on, data.valid_until, data.fulfillment_days,
                          tuple(sorted(lines, key=lambda item: str(item.revision_item_id))))


def _approved_revision(target: PurchaseRequest):
    _unissued(target)
    if target.status != RequestStatus.APPROVED:
        raise ConflictError('Penawaran hanya dapat diproses pada permintaan yang disetujui sebelum PO.')
    revision = _current_revision(target)
    if not ApprovalDecision.objects.filter(revision=revision, decision=Decision.APPROVE).exists():
        raise ConflictError('Revisi aktif belum disetujui.')
    return revision


def save_quotation(ctx: ActionContext, *, request_id: UUID, quotation_id: UUID | None, data: QuotationInput) -> Quotation:
    with transaction.atomic():
        actor = active_actor(ctx.actor_id)
        require_procurement(actor)
        target = get_object_or_404(visible_requests(actor), pk=request_id)
        data = _prepare(data)
        creating = quotation_id is None
        action = 'quotation.create' if creating else 'quotation.edit'
        payload = dict(vendor_id=str(data.vendor_id), reference=data.reference, quoted_on=data.quoted_on.isoformat(),
                       valid_until=data.valid_until.isoformat(), fulfillment_days=data.fulfillment_days,
                       items=[dict(revision_item_id=str(item.revision_item_id), unit_price=item.unit_price) for item in data.items],
                       quotation_id=str(quotation_id) if quotation_id else None, expected_version=ctx.expected_version)
        digest = payload_hash(payload)
        replay = find_replay(ctx, action=action, target_type='REQUEST', target_key=str(target.pk), digest=digest)
        if replay is not None:
            return resolve_result(replay)
        check_version(target, ctx.expected_version)
        revision = _approved_revision(target)
        quote = None if creating else get_object_or_404(Quotation, pk=quotation_id, revision__request=target)
        if quote is not None and quote.revision_id != revision.pk:
            raise ConflictError('Penawaran revisi lama hanya dapat dibaca.')
        vendor = Vendor.objects.filter(pk=data.vendor_id, is_active=True).first()
        if vendor is None:
            raise ValidationError('Pilih vendor aktif yang tersedia.')
        snapshot = {item.pk: item for item in revision.items.all()}
        if {item.revision_item_id for item in data.items} != set(snapshot):
            raise ValidationError('Rincian harus mencakup tepat seluruh item revisi aktif.')
        rows = []
        for item in data.items:
            price = parse_money(item.unit_price)
            rows.append(dict(revision_item=snapshot[item.revision_item_id], unit_price_minor=price,
                             line_total_minor=line_total(snapshot[item.revision_item_id].qty_milli, price)))
        total = document_total(row['line_total_minor'] for row in rows)
        _advance(target)
        if creating:
            quote = Quotation(revision=revision, created_by=actor)
        quote.vendor = vendor
        for field in ['reference', 'quoted_on', 'valid_until', 'fulfillment_days']:
            setattr(quote, field, getattr(data, field))
        quote.total_minor = total
        quote.save()
        quote.items.all().delete()
        QuotationItem.objects.bulk_create([QuotationItem(quotation=quote, **row) for row in rows])
        if target.selected_quotation_id == quote.pk:
            _clear_selection(target)
        target.save()
        _audit(ctx, actor, quote, action, 'QUOTATION', str(target.pk), digest, request=target,
               changes=dict(version=target.version, revision_number=revision.number, total=format_money(total), vendor_id=str(vendor.pk)))
        return quote


def select_quotation(ctx: ActionContext, *, request_id: UUID, quotation_id: UUID, reason: str, single_source_reason: str) -> PurchaseRequest:
    with transaction.atomic():
        actor = active_actor(ctx.actor_id)
        require_procurement(actor)
        target = get_object_or_404(visible_requests(actor), pk=request_id)
        reason = _text(reason, 4000, 'Alasan pemilihan', required=True)
        single_source_reason = _text(single_source_reason, 4000, 'Alasan sumber tunggal')
        digest = payload_hash(dict(quotation_id=str(quotation_id), reason=reason, single_source_reason=single_source_reason,
                                   expected_version=ctx.expected_version))
        replay = find_replay(ctx, action='quotation.select', target_type='REQUEST', target_key=str(target.pk), digest=digest)
        if replay is not None:
            return resolve_result(replay)
        check_version(target, ctx.expected_version)
        revision = _approved_revision(target)
        quote = get_object_or_404(Quotation.objects.select_related('vendor'), pk=quotation_id, revision__request=target)
        if quote.revision_id != revision.pk:
            raise ConflictError('Penawaran revisi lama tidak dapat dipilih.')
        prefetch_related_objects([revision], 'items')
        today = timezone.localdate()
        issues = quotation_issues(quote, revision, today)
        if issues:
            raise ValidationError(issues)
        eligible_vendors = {candidate.vendor_id for candidate in revision.quotations.select_related('vendor').prefetch_related('items')
                            if not quotation_issues(candidate, revision, today)}
        if len(eligible_vendors) == 1 and not single_source_reason:
            raise ValidationError('Isi alasan sumber tunggal karena hanya satu vendor yang layak.')
        _advance(target)
        target.selected_quotation = quote
        target.selection_reason = reason
        target.single_source_reason = single_source_reason
        target.save()
        _audit(ctx, actor, target, 'quotation.select', 'REQUEST', str(target.pk), digest, request=target, reason=reason,
               changes=dict(version=target.version, revision_number=revision.number, quotation_id=str(quote.pk),
                            single_source_reason=single_source_reason, eligible_vendor_count=len(eligible_vendors)))
        return target
