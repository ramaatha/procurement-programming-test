# filepath: procurement/services/orders.py
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import prefetch_related_objects
from django.shortcuts import get_object_or_404
from django.utils import timezone

from common.actions import ActionContext, check_version, find_replay, payload_hash, record_action, resolve_result
from common.errors import ConflictError
from common.numbers import format_money
from procurement.models import AuditEvent, PurchaseOrder, PurchaseOrderItem, Quotation
from procurement.policies import active_actor, require_procurement
from procurement.quotations import quotation_issues
from procurement.selectors import visible_requests
from procurement.services.requests import _advance, _text
from procurement.services.sourcing import _approved_revision


def issue_order(ctx: ActionContext, *, request_id: UUID) -> PurchaseOrder:
    with transaction.atomic():
        actor = active_actor(ctx.actor_id)
        require_procurement(actor)
        target = get_object_or_404(visible_requests(actor),pk=request_id)
        digest = payload_hash(dict(expected_version=ctx.expected_version))
        replay = find_replay(ctx,action='order.issue',target_type='REQUEST',target_key=str(target.pk),digest=digest)
        if replay is not None:
            return resolve_result(replay)
        check_version(target,ctx.expected_version)
        revision = _approved_revision(target)
        if target.selected_quotation_id is None:
            raise ValidationError('Pilih penawaran sebelum menerbitkan PO.')
        quote = Quotation.objects.select_related('vendor').prefetch_related('items').get(pk=target.selected_quotation_id)
        if quote.revision_id != revision.pk:
            raise ConflictError('Penawaran terpilih tidak sesuai revisi aktif.')
        prefetch_related_objects([revision],'items')
        today = timezone.localdate()
        issues = quotation_issues(quote,revision,today)
        if issues:
            raise ValidationError(issues)
        reason = _text(target.selection_reason,4000,'Alasan pemilihan',required=True)
        source_reason = _text(target.single_source_reason,4000,'Alasan sumber tunggal')
        eligible_vendors = {candidate.vendor_id for candidate in revision.quotations.select_related('vendor').prefetch_related('items')
                            if not quotation_issues(candidate,revision,today)}
        if len(eligible_vendors)==1 and not source_reason:
            raise ValidationError('Kondisi sumber berubah. Pilih kembali penawaran dengan alasan sumber tunggal.')
        _advance(target)
        order = PurchaseOrder.objects.create(request=target,revision=revision,quotation=quote,vendor=quote.vendor,
                    vendor_name=quote.vendor.name,vendor_contact=quote.vendor.contact,kind=revision.kind,
                    destination=revision.destination,total_minor=quote.total_minor,selection_reason=reason,
                    single_source_reason=source_reason,issued_by=actor)
        prices = {row.revision_item_id:row for row in quote.items.all()}
        PurchaseOrderItem.objects.bulk_create([
            PurchaseOrderItem(order=order,revision_item=item,position=item.position,name=item.name,unit=item.unit,
                              qty_milli=item.qty_milli,unit_price_minor=prices[item.pk].unit_price_minor,
                              line_total_minor=prices[item.pk].line_total_minor)
            for item in revision.items.all()
        ])
        target.save(update_fields=['version','updated_at'])
        AuditEvent.objects.create(request=target,actor=actor,actor_name=actor.username,actor_role=actor.role,
                                   action='order.issue',target_type='ORDER',target_id=str(order.pk),reason=reason,
                                   changes=dict(request_version=target.version,revision_number=revision.number,
                                                status=order.status,order_number=order.number,total=format_money(order.total_minor)))
        record_action(ctx,action='order.issue',target_type='REQUEST',target_key=str(target.pk),digest=digest,result=order)
        return order


def close_order(ctx: ActionContext, *, order_id: UUID, reason: str) -> PurchaseOrder:
    from procurement.policies import require_request_reviewer
    from procurement.selectors import visible_orders
    from procurement.services.receipts import advance_order, order_balances, require_open
    from procurement.models import OrderStatus

    with transaction.atomic():
        actor = active_actor(ctx.actor_id)
        from accounts.models import Role
        from django.core.exceptions import PermissionDenied
        if actor.role != Role.APPROVER:
            raise PermissionDenied
        order = get_object_or_404(visible_orders(actor),pk=order_id)
        require_request_reviewer(actor,order.request)
        reason = _text(reason,4000,'Alasan penutupan',required=True)
        digest = payload_hash(dict(reason=reason,expected_version=ctx.expected_version))
        replay = find_replay(ctx,action='order.close',target_type='ORDER',target_key=str(order.pk),digest=digest)
        if replay is not None:
            return resolve_result(replay)
        check_version(order,ctx.expected_version)
        require_open(order)
        order.status = OrderStatus.CLOSED_SHORT if any(row['accepted'] for row in order_balances(order)) else OrderStatus.CANCELLED
        order.closed_by,order.closed_at,order.closed_reason = actor,timezone.now(),reason
        advance_order(order)
        order.save(update_fields=['status','version','closed_by','closed_at','closed_reason','updated_at'])
        AuditEvent.objects.create(request=order.request,actor=actor,actor_name=actor.username,actor_role=actor.role,
                                  action='order.close',target_type='ORDER',target_id=str(order.pk),reason=reason,
                                  changes=dict(status=order.status,order_version=order.version))
        record_action(ctx,action='order.close',target_type='ORDER',target_key=str(order.pk),digest=digest,result=order)
        return order
