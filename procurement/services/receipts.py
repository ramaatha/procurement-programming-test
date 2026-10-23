# filepath: procurement/services/receipts.py
from datetime import date
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.models import Role
from common.actions import ActionContext, check_version, find_replay, payload_hash, record_action, resolve_result
from common.errors import ConflictError
from common.numbers import MAX_INT64, parse_quantity
from procurement.inputs import ReceiptInput, ReceiptLineInput
from procurement.models import AuditEvent, EvidenceType, Kind, OrderStatus, PurchaseOrder, Receipt, ReceiptItem
from procurement.policies import active_actor
from procurement.selectors import order_balances, visible_orders
from procurement.services.requests import _text


def require_open(order: PurchaseOrder) -> None:
    if order.status not in (OrderStatus.ISSUED,OrderStatus.PARTIALLY_RECEIVED):
        raise ConflictError('PO sudah berakhir dan tidak dapat diubah.')


def advance_order(order: PurchaseOrder) -> None:
    if order.version >= MAX_INT64:
        raise ValidationError('Versi PO mencapai batas penyimpanan.')
    order.version += 1


def _prepare(data: ReceiptInput) -> tuple[dict,list[dict]]:
    if not isinstance(data,ReceiptInput) or not isinstance(data.items,tuple) or not 1 <= len(data.items) <= 1000:
        raise ValidationError('Isi rincian penerimaan, maksimal 1000 item.')
    header = dict(reference=_text(data.reference,100,'Referensi',required=True),
                  notes=_text(data.notes,4000,'Catatan',required=True),evidence_type=str(data.evidence_type))
    if data.evidence_type not in EvidenceType.values:
        raise ValidationError('Jenis bukti tidak valid.')
    for key in ('service_started_on','service_ended_on'):
        value = getattr(data,key)
        if value is not None and type(value) is not date:
            raise ValidationError('Periode jasa tidak valid.')
        header[key] = value
    seen, rows = set(), []
    for line in data.items:
        if not isinstance(line,ReceiptLineInput) or not isinstance(line.order_item_id,UUID) or line.order_item_id in seen:
            raise ValidationError('Item penerimaan tidak valid atau berulang.')
        seen.add(line.order_item_id)
        accepted = parse_quantity(line.accepted,allow_zero=True)
        rejected = parse_quantity(line.rejected,allow_zero=True)
        reason = _text(line.rejection_reason,4000,'Alasan penolakan',required=bool(rejected))
        rows.append(dict(order_item_id=line.order_item_id,accepted_milli=accepted,rejected_milli=rejected,rejection_reason=reason))
    if not any(row['accepted_milli'] or row['rejected_milli'] for row in rows):
        raise ValidationError('Minimal satu jumlah diterima atau ditolak harus lebih dari nol.')
    rows.sort(key=lambda row: str(row['order_item_id']))
    return header,rows


def post_receipt(ctx: ActionContext, *, order_id: UUID, data: ReceiptInput) -> Receipt:
    with transaction.atomic():
        actor = active_actor(ctx.actor_id)
        if actor.role != Role.RECEIVER:
            raise PermissionDenied
        order = get_object_or_404(visible_orders(actor),pk=order_id)
        header,rows = _prepare(data)
        payload = {key: value.isoformat() if type(value) is date else value for key,value in header.items()}
        payload['items'] = [row | dict(order_item_id=str(row['order_item_id'])) for row in rows]
        digest = payload_hash(payload | dict(expected_version=ctx.expected_version))
        replay = find_replay(ctx,action='receipt.post',target_type='ORDER',target_key=str(order.pk),digest=digest)
        if replay is not None:
            return resolve_result(replay)
        check_version(order,ctx.expected_version)
        require_open(order)
        now = timezone.now()
        start,end = header['service_started_on'],header['service_ended_on']
        if order.kind == Kind.GOODS:
            if header['evidence_type'] != EvidenceType.GOODS_DELIVERY or start is not None or end is not None:
                raise ValidationError('Barang memakai bukti surat jalan tanpa periode jasa.')
        elif header['evidence_type'] not in (EvidenceType.SERVICE_REPORT,EvidenceType.SERVICE_ACCEPTANCE) or start is None or end is None or not start <= end <= timezone.localdate(now):
            raise ValidationError('Isi bukti jasa dan periode awal sampai akhir yang tidak melewati hari konfirmasi.')
        balances = order_balances(order)
        for row in rows:
            balance = balances.get(row['order_item_id'])
            if balance is None or row['accepted_milli'] > balance['remaining_milli']:
                raise ValidationError('Item tidak sesuai PO atau jumlah diterima melebihi sisa pesanan.')
        receipt = Receipt.objects.create(order=order,kind=order.kind,confirmed_by=actor,confirmed_at=now,**header)
        ReceiptItem.objects.bulk_create([ReceiptItem(receipt=receipt,**row) for row in rows
                                        if row['accepted_milli'] or row['rejected_milli']])
        accepted_now = {row['order_item_id']:row['accepted_milli'] for row in rows}
        remaining = [balance['remaining_milli']-accepted_now.get(key,0) for key,balance in balances.items()]
        any_accepted = any(balance['accepted_milli'] or accepted_now.get(key,0) for key,balance in balances.items())
        order.status = OrderStatus.RECEIVED if all(value==0 for value in remaining) else (
            OrderStatus.PARTIALLY_RECEIVED if any_accepted else OrderStatus.ISSUED)
        advance_order(order)
        order.save(update_fields=['status','version','updated_at'])
        AuditEvent.objects.create(request=order.request,actor=actor,actor_name=actor.username,actor_role=actor.role,
                                  action='receipt.post',target_type='RECEIPT',target_id=str(receipt.pk),reason=header['notes'],
                                  changes=dict(order_status=order.status,order_version=order.version,receipt_number=receipt.number))
        record_action(ctx,action='receipt.post',target_type='ORDER',target_key=str(order.pk),digest=digest,result=receipt)
        return receipt
