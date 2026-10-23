# filepath: procurement/views/receipts.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from accounts.models import Role
from common.actions import ActionContext, load_action_token, make_action_token
from common.errors import ConflictError
from common.http import database_busy, validation_errors
from common.numbers import format_quantity
from procurement.forms.receipts import CloseOrderForm, ReceiptForm, ReceiptLineFormSet
from procurement.models import OrderStatus, Receipt
from procurement.policies import active_actor, require_request_reviewer
from procurement.selectors import visible_orders
from procurement.presentation import balance_rows
from procurement.services.orders import close_order
from procurement.services.receipts import post_receipt, require_open


def _scope(request,order,action):
    return dict(actor_id=request.user.pk,target_type='ORDER',target_key=str(order.pk),action=action)


def order_receipt_context(request,order,*,close_form=None):
    from procurement.views.tracking import audit_context
    actor = active_actor(request.user.pk)
    open_order = order.status in (OrderStatus.ISSUED,OrderStatus.PARTIALLY_RECEIVED)
    can_close = open_order and actor.role == Role.APPROVER and order.request.requester_id != actor.pk
    if can_close and close_form is None:
        close_form = CloseOrderForm(initial=dict(action_token=make_action_token(**_scope(request,order,'order.close')),expected_version=order.version))
    return dict(balances=balance_rows(order),receipts=order.receipts.order_by('confirmed_at','pk'),
                can_receive=open_order and actor.role==Role.RECEIVER,close_form=close_form if can_close or close_form is not None else None,
                **audit_context(order.request,request.GET))


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@sensitive_variables()
@login_required
@require_http_methods(['GET','POST'])
def receipt_create(request,order_id):
    actor = active_actor(request.user.pk)
    if actor.role != Role.RECEIVER:
        raise PermissionDenied
    order = get_object_or_404(visible_orders(actor).prefetch_related('items'),pk=order_id)
    if request.method=='GET':
        try:
            require_open(order)
        except ConflictError:
            return render(request,'procurement/receipt_unavailable.html',dict(order=order),status=409)
    bound = request.POST if request.method=='POST' else None
    initial = dict(action_token=make_action_token(**_scope(request,order,'receipt.post')),expected_version=order.version,
                   evidence_type='GOODS_DELIVERY' if order.kind=='GOODS' else 'SERVICE_REPORT') if bound is None else None
    form = ReceiptForm(bound,kind=order.kind,initial=initial)
    balances = balance_rows(order)
    formset = ReceiptLineFormSet(bound,prefix='items',initial=[dict(order_item_id=row['item'].pk,accepted='0',rejected='0') for row in balances])
    status = 200 if bound is None else 400
    if bound is not None:
        valid_form,valid_items = form.is_valid(),formset.is_valid()
        if valid_form and valid_items:
            try:
                nonce = load_action_token(form.cleaned_data['action_token'],**_scope(request,order,'receipt.post'))
                receipt = post_receipt(ActionContext(actor.pk,nonce,form.cleaned_data['expected_version']),order_id=order.pk,data=form.to_input(formset))
            except ValidationError as error:
                validation_errors(form,error)
            except ConflictError:
                form.add_error(None,'Data atau status sudah berubah. Muat ulang sebelum mencatat penerimaan.')
                status = 409
            except OperationalError as error:
                if not database_busy(error):
                    raise
                form.add_error(None,'Penyimpanan sedang sibuk. Coba kembali sebentar lagi.')
                status = 503
            else:
                messages.success(request,'Penerimaan berhasil dicatat dan tidak dapat diedit.')
                response = redirect('procurement:receipt_detail',receipt_id=receipt.pk)
                response.status_code = 303
                return response
    rows = {str(row['item'].pk):row for row in balances}
    line_forms = []
    for line in formset:
        line_forms.append((line,rows.get(str(line['order_item_id'].value()))))
    response = render(request,'procurement/receipt_form.html',dict(order=order,form=form,formset=formset,line_forms=line_forms),status=status)
    if status==503:
        response['Retry-After'] = '5'
    return response


@login_required
@require_safe
def receipt_detail(request,receipt_id):
    receipt = get_object_or_404(Receipt.objects.select_related('order'),pk=receipt_id,order__in=visible_orders(request.user))
    lines = [dict(item=row.order_item,accepted=format_quantity(row.accepted_milli),rejected=format_quantity(row.rejected_milli),reason=row.rejection_reason)
             for row in receipt.items.select_related('order_item').order_by('order_item__position')]
    return render(request,'procurement/receipt_detail.html',dict(receipt=receipt,lines=lines))


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@sensitive_variables()
@login_required
@require_POST
def order_close(request,order_id):
    from procurement.views.orders import _snapshot_context
    actor = active_actor(request.user.pk)
    order = get_object_or_404(visible_orders(actor),pk=order_id)
    require_request_reviewer(actor,order.request)
    form = CloseOrderForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            nonce = load_action_token(form.cleaned_data['action_token'],**_scope(request,order,'order.close'))
            close_order(ActionContext(actor.pk,nonce,form.cleaned_data['expected_version']),order_id=order.pk,reason=form.cleaned_data['reason'])
        except ValidationError as error:
            validation_errors(form,error)
        except ConflictError:
            form.add_error(None,'Data atau status sudah berubah. Muat ulang sebelum menutup PO.')
            status = 409
        except OperationalError as error:
            if not database_busy(error):
                raise
            form.add_error(None,'Penyimpanan sedang sibuk. Coba kembali sebentar lagi.')
            status = 503
        else:
            messages.success(request,'PO berhasil diakhiri. Riwayat penerimaan tetap tersimpan.')
            response = redirect('procurement:order_detail',order_id=order.pk)
            response.status_code = 303
            return response
    order.refresh_from_db()
    response = render(request,'procurement/order_detail.html',_snapshot_context(order)|order_receipt_context(request,order,close_form=form),status=status)
    if status==503:
        response['Retry-After'] = '5'
    return response
