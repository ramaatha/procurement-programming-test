# filepath: procurement/services/requests.py
from dataclasses import asdict
from datetime import date
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.models import Role, User
from common.actions import ActionContext, check_version, find_replay, payload_hash, record_action, resolve_result
from common.errors import ConflictError
from common.numbers import MAX_INT64, document_total, format_money, format_quantity, line_total, parse_money, parse_quantity
from procurement.inputs import DraftInput, RequestLineInput
from procurement.models import ApprovalDecision, AuditEvent, Decision, Kind, PurchaseOrder, PurchaseRequest, RequestItem, RequestRevision, RequestStatus, RevisionItem
from procurement.policies import active_actor, require_procurement, require_request_owner, require_request_reviewer
from procurement.selectors import visible_requests


def _text(value: str, limit: int, label: str, *, required: bool = False) -> str:
    if not isinstance(value,str):
        raise ValidationError(f'{label} tidak valid.')
    value=value.strip()
    if len(value)>limit or (required and not value):
        raise ValidationError(f'{label} wajib diisi dan maksimal {limit} karakter.' if required else f'{label} maksimal {limit} karakter.')
    return value


def _prepare(data: DraftInput) -> tuple[DraftInput,list[dict],int]:
    if not isinstance(data,DraftInput) or data.kind not in Kind.values or not isinstance(data.items,tuple):
        raise ValidationError('Data permintaan tidak valid.')
    if data.needed_on is not None and type(data.needed_on) is not date:
        raise ValidationError('Tanggal kebutuhan tidak valid.')
    lines=[];rows=[]
    for position,item in enumerate(data.items,1):
        if not isinstance(item,RequestLineInput):
            raise ValidationError('Rincian item tidak valid.')
        name=_text(item.name,200,f'Nama item {position}',required=True)
        unit=_text(item.unit,40,f'Satuan item {position}',required=True)
        qty=parse_quantity(item.quantity);price=parse_money(item.unit_price)
        rows.append(dict(position=position,name=name,unit=unit,qty_milli=qty,estimated_unit_price_minor=price,line_total_minor=line_total(qty,price)))
        lines.append(RequestLineInput(name,unit,format_quantity(qty),format_money(price)))
    normalized=DraftInput(str(data.kind),_text(data.title,200,'Judul'),_text(data.reason,4000,'Alasan'),_text(data.destination,500,'Tujuan'),data.needed_on,tuple(lines))
    return normalized,rows,document_total(row['line_total_minor'] for row in rows)


def _payload(data: DraftInput, version: int | None) -> dict:
    return dict(kind=data.kind,title=data.title,reason=data.reason,destination=data.destination,needed_on=data.needed_on.isoformat() if data.needed_on else None,items=[asdict(item) for item in data.items],expected_version=version)


def _target(ctx: ActionContext) -> User:
    return active_actor(ctx.actor_id)


def _owned(actor: User, request_id: UUID) -> PurchaseRequest:
    target=get_object_or_404(visible_requests(actor),pk=request_id)
    require_request_owner(actor,target)
    return target


def _advance(target: PurchaseRequest) -> None:
    if target.version>=MAX_INT64:
        raise ValidationError('Versi permintaan mencapai batas penyimpanan.')
    target.version+=1


def _unissued(target: PurchaseRequest) -> None:
    if PurchaseOrder.objects.filter(request=target).exists():
        raise ConflictError('Permintaan sudah memiliki PO dan tidak dapat diubah atau dibatalkan.')


def _clear_selection(target: PurchaseRequest) -> None:
    target.selected_quotation=None
    target.selection_reason=''
    target.single_source_reason=''


def _record(ctx: ActionContext, actor: User, target: PurchaseRequest, action: str, key: str, digest: str, *, reason: str = '', total: int | None = None, decision: str | None = None) -> None:
    changes=dict(status=target.status,version=target.version,revision_number=target.current_revision_number)
    if total is not None:
        changes['estimated_total']=format_money(total)
    if decision is not None:
        changes['decision'] = decision
    AuditEvent.objects.create(request=target,actor=actor,actor_name=actor.username,actor_role=actor.role,action=action,target_type='REQUEST',target_id=str(target.pk),reason=reason,changes=changes)
    record_action(ctx,action=action,target_type='REQUEST',target_key=key,digest=digest,result=target)


def save_draft(ctx: ActionContext, *, request_id: UUID | None, data: DraftInput) -> PurchaseRequest:
    with transaction.atomic():
        actor=_target(ctx)
        creating=request_id is None
        if creating:
            if actor.role != Role.REQUESTER:
                raise PermissionDenied
            target=None
        else:
            target=_owned(actor,request_id)
        data,rows,total=_prepare(data)
        action='request.create' if creating else 'request.edit'
        key='new-request' if creating else str(target.pk)
        digest=payload_hash(_payload(data,ctx.expected_version))
        replay=find_replay(ctx,action=action,target_type='REQUEST',target_key=key,digest=digest)
        if replay is not None:
            result=resolve_result(replay)
            require_request_owner(actor,result)
            return result
        if creating:
            if ctx.expected_version is not None:raise ConflictError()
            target=PurchaseRequest(requester=actor,kind=data.kind)
        else:
            check_version(target,ctx.expected_version)
            _unissued(target)
            if target.status not in (RequestStatus.DRAFT,RequestStatus.CHANGES_REQUESTED):raise ConflictError()
            _advance(target)
        for field in ('kind','title','reason','destination','needed_on'):
            setattr(target,field,getattr(data,field))
        _clear_selection(target)
        target.save()
        target.items.all().delete()
        RequestItem.objects.bulk_create([RequestItem(request=target,position=row['position'],name=row['name'],unit=row['unit'],qty_milli=row['qty_milli'],estimated_unit_price_minor=row['estimated_unit_price_minor']) for row in rows])
        _record(ctx,actor,target,action,key,digest,total=total)
        return target


def submit_request(ctx: ActionContext, *, request_id: UUID) -> PurchaseRequest:
    with transaction.atomic():
        actor=_target(ctx);target=_owned(actor,request_id)
        digest=payload_hash(dict(expected_version=ctx.expected_version))
        replay=find_replay(ctx,action='request.submit',target_type='REQUEST',target_key=str(target.pk),digest=digest)
        if replay is not None:return resolve_result(replay)
        check_version(target,ctx.expected_version)
        _unissued(target)
        if target.status not in (RequestStatus.DRAFT,RequestStatus.CHANGES_REQUESTED):raise ConflictError()
        source=DraftInput(target.kind,target.title,target.reason,target.destination,target.needed_on,tuple(RequestLineInput(item.name,item.unit,format_quantity(item.qty_milli),format_money(item.estimated_unit_price_minor)) for item in target.items.all()))
        normalized,rows,total=_prepare(source)
        for value,label in [(normalized.title,'Judul'),(normalized.reason,'Alasan'),(normalized.destination,'Tujuan')]:
            if not value:raise ValidationError(f'{label} wajib diisi sebelum pengajuan.')
        if not rows:raise ValidationError('Isi minimal satu item sebelum pengajuan.')
        if normalized.needed_on is None or normalized.needed_on<timezone.localdate():
            raise ValidationError('Tanggal kebutuhan wajib diisi dan tidak boleh lampau saat pengajuan.')
        if target.current_revision_number>=MAX_INT64:raise ValidationError('Nomor revisi mencapai batas penyimpanan.')
        _advance(target)
        number=target.current_revision_number+1
        revision=RequestRevision.objects.create(request=target,number=number,kind=normalized.kind,title=normalized.title,reason=normalized.reason,destination=normalized.destination,needed_on=normalized.needed_on,estimated_total_minor=total,submitted_by=actor)
        RevisionItem.objects.bulk_create([RevisionItem(revision=revision,**row) for row in rows])
        target.status=RequestStatus.SUBMITTED
        target.current_revision_number=number
        _clear_selection(target)
        target.save()
        _record(ctx,actor,target,'request.submit',str(target.pk),digest,total=total)
        return target


def cancel_request(ctx: ActionContext, *, request_id: UUID, reason: str) -> PurchaseRequest:
    with transaction.atomic():
        actor=_target(ctx);target=_owned(actor,request_id)
        reason=_text(reason,4000,'Alasan pembatalan',required=True)
        digest=payload_hash(dict(reason=reason,expected_version=ctx.expected_version))
        replay=find_replay(ctx,action='request.cancel',target_type='REQUEST',target_key=str(target.pk),digest=digest)
        if replay is not None:return resolve_result(replay)
        check_version(target,ctx.expected_version)
        _unissued(target)
        if target.status not in (RequestStatus.DRAFT,RequestStatus.CHANGES_REQUESTED,RequestStatus.SUBMITTED,RequestStatus.APPROVED):raise ConflictError()
        _advance(target)
        target.status=RequestStatus.CANCELLED
        _clear_selection(target)
        target.save()
        _record(ctx,actor,target,'request.cancel',str(target.pk),digest,reason=reason)
        return target


def _current_revision(target: PurchaseRequest) -> RequestRevision:
    revision = target.revisions.filter(number=target.current_revision_number).first()
    if revision is None or not revision.items.exists():
        raise ConflictError('Revisi pengajuan tidak tersedia. Muat ulang permintaan.')
    return revision


def review_request(ctx: ActionContext, *, request_id: UUID, decision: str, reason: str) -> PurchaseRequest:
    with transaction.atomic():
        actor = active_actor(ctx.actor_id)
        target = get_object_or_404(visible_requests(actor), pk=request_id)
        require_request_reviewer(actor, target)
        if decision not in Decision.values:
            raise ValidationError('Keputusan tidak valid.')
        reason = _text(reason, 4000, 'Alasan keputusan', required=decision != Decision.APPROVE)
        digest = payload_hash(dict(decision=decision, reason=reason, expected_version=ctx.expected_version))
        replay = find_replay(ctx, action='request.review', target_type='REQUEST', target_key=str(target.pk), digest=digest)
        if replay is not None:
            return resolve_result(replay)
        check_version(target, ctx.expected_version)
        _unissued(target)
        if target.status != RequestStatus.SUBMITTED:
            raise ConflictError()
        revision = _current_revision(target)
        if ApprovalDecision.objects.filter(revision=revision).exists():
            raise ConflictError('Revisi ini sudah memiliki keputusan.')
        _advance(target)
        ApprovalDecision.objects.create(revision=revision, actor=actor, requester_at_decision=target.requester,
                                        decision=decision, reason=reason)
        target.status = {
            Decision.APPROVE: RequestStatus.APPROVED,
            Decision.REQUEST_CHANGES: RequestStatus.CHANGES_REQUESTED,
            Decision.REJECT: RequestStatus.REJECTED,
        }[decision]
        _clear_selection(target)
        target.save()
        _record(ctx, actor, target, 'request.review', str(target.pk), digest, reason=reason, decision=decision)
        return target


def request_revision(ctx: ActionContext, *, request_id: UUID, reason: str) -> PurchaseRequest:
    with transaction.atomic():
        actor = active_actor(ctx.actor_id)
        require_procurement(actor)
        target = get_object_or_404(visible_requests(actor), pk=request_id)
        reason = _text(reason, 4000, 'Alasan revisi', required=True)
        digest = payload_hash(dict(reason=reason, expected_version=ctx.expected_version))
        replay = find_replay(ctx, action='request.revision', target_type='REQUEST', target_key=str(target.pk), digest=digest)
        if replay is not None:
            return resolve_result(replay)
        check_version(target, ctx.expected_version)
        _unissued(target)
        if target.status != RequestStatus.APPROVED:
            raise ConflictError()
        revision = _current_revision(target)
        if not ApprovalDecision.objects.filter(revision=revision, decision=Decision.APPROVE).exists():
            raise ConflictError('Revisi aktif belum memiliki persetujuan yang sesuai.')
        _advance(target)
        _clear_selection(target)
        target.status = RequestStatus.CHANGES_REQUESTED
        target.save()
        _record(ctx, actor, target, 'request.revision', str(target.pk), digest, reason=reason)
        return target
