# filepath: procurement/views/orders.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_POST, require_safe

from common.actions import ActionContext, load_action_token, make_action_token
from common.errors import ConflictError
from common.http import database_busy, validation_errors
from procurement.forms.orders import IssueOrderForm
from procurement.models import AuditEvent
from procurement.policies import active_actor, require_procurement
from procurement.selectors import can_source, visible_orders, visible_requests
from procurement.services.orders import issue_order


def _scope(request,target):
    return dict(actor_id=request.user.pk,target_type='REQUEST',target_key=str(target.pk),action='order.issue')


@sensitive_variables()
def issue_context(request,target,*,form=None):
    existing = visible_orders(request.user).filter(request=target).first()
    eligible_action = can_source(active_actor(request.user.pk),target) and target.selected_quotation_id is not None
    if form is None and eligible_action:
        form = IssueOrderForm(initial=dict(action_token=make_action_token(**_scope(request,target)),expected_version=target.version))
    # Error submissions retain their original token/version; replay is decided by the service.
    return dict(issue_form=form,existing_order=existing)


@login_required
@require_safe
def order_list(request):
    page = Paginator(visible_orders(request.user).order_by('-issued_at','-pk'),25).get_page(request.GET.get('page'))
    return render(request,'procurement/order_list.html',dict(page_obj=page))


def _snapshot_context(order):
    event = AuditEvent.objects.filter(action='order.issue',target_type='ORDER',target_id=str(order.pk)).first()
    return dict(order=order,items=order.items.all(),issued_actor_name=event.actor_name if event else f'Akun {order.issued_by_id}')


@login_required
@require_safe
def order_detail(request,order_id):
    order = get_object_or_404(visible_orders(request.user),pk=order_id)
    return render(request,'procurement/order_detail.html',_snapshot_context(order))


@login_required
@require_safe
def order_print(request,order_id):
    order = get_object_or_404(visible_orders(request.user),pk=order_id)
    return render(request,'procurement/order_print.html',_snapshot_context(order))


@sensitive_variables()
def _issue(request,request_id):
    from procurement.views.requests import _render_detail
    target = get_object_or_404(visible_requests(request.user),pk=request_id)
    require_procurement(request.user)
    form = IssueOrderForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            nonce = load_action_token(form.cleaned_data['action_token'],**_scope(request,target))
            order = issue_order(ActionContext(request.user.pk,nonce,form.cleaned_data['expected_version']),request_id=target.pk)
        except ValidationError as error:
            validation_errors(form,error)
        except ConflictError:
            form.add_error(None,'Data atau status sudah berubah. Muat ulang sebelum menerbitkan PO.')
            status = 409
        except OperationalError as error:
            if not database_busy(error):
                raise
            form.add_error(None,'Penyimpanan sedang sibuk. Coba kembali sebentar lagi.')
            status = 503
        else:
            messages.success(request,'PO berhasil diterbitkan.')
            response = redirect('procurement:order_detail',order_id=order.pk)
            response.status_code = 303
            return response
    target.refresh_from_db()
    return _render_detail(request,target,issue_form=form,status=status)


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@login_required
@require_POST
def order_issue(request,request_id):
    return _issue(request,request_id)
