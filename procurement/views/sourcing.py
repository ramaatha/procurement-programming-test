# filepath: procurement/views/sourcing.py
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from common.actions import ActionContext, load_action_token, make_action_token
from common.errors import ConflictError
from common.http import database_busy, validation_errors
from common.numbers import format_money
from procurement.forms.sourcing import QuotationForm, QuotationLineFormSet, SelectionForm, VendorForm
from procurement.models import Quotation, Vendor
from procurement.policies import active_actor, require_procurement, require_vendor_manager
from procurement.selectors import can_source, comparison_rows, sourcing_revision, visible_requests
from procurement.services.sourcing import save_quotation, save_vendor, select_quotation


def _scope(request, target_type, key, action):
    return dict(actor_id=request.user.pk, target_type=target_type, target_key=key, action=action)


def _initial(request, target_type, key, action, version):
    return dict(action_token=make_action_token(**_scope(request, target_type, key, action)), expected_version=version)


def _redirect(name, **kwargs):
    response = redirect(name, **kwargs)
    response.status_code = 303
    return response


@sensitive_variables()
def _error(form, error):
    if isinstance(error, ValidationError):
        validation_errors(form, error)
        return 400
    if isinstance(error, ConflictError):
        form.add_error(None, 'Data atau status sudah berubah. Muat ulang sebelum menyimpan.')
        return 409
    if not database_busy(error):
        raise error
    form.add_error(None, 'Penyimpanan sedang sibuk. Coba kembali sebentar lagi.')
    return 503


def _retry(response):
    if response.status_code == 503:
        response['Retry-After'] = '1'
    return response


@login_required
@require_safe
def vendor_list(request):
    require_vendor_manager(request.user)
    page = Paginator(Vendor.objects.order_by('name','pk'),25).get_page(request.GET.get('page'))
    return render(request,'procurement/vendor_list.html',dict(page_obj=page))


@sensitive_variables()
def _vendor_form(request, vendor_id=None):
    require_vendor_manager(request.user)
    target = None if vendor_id is None else get_object_or_404(Vendor, pk=vendor_id)
    creating = target is None
    action, key = ('vendor.create','new-vendor') if creating else ('vendor.edit',str(target.pk))
    initial = _initial(request, 'VENDOR', key, action, None if creating else target.version)
    initial.update(dict(name=target.name, contact=target.contact, is_active=target.is_active) if target else dict(is_active=True))
    form = VendorForm(request.POST if request.method == 'POST' else None, initial=initial, creating=creating)
    status = 200
    if request.method == 'POST':
        status = 400
        if form.is_valid():
            try:
                nonce = load_action_token(form.cleaned_data['action_token'], **_scope(request,'VENDOR',key,action))
                save_vendor(ActionContext(request.user.pk,nonce,form.cleaned_data.get('expected_version')),
                            vendor_id=vendor_id, name=form.cleaned_data['name'], contact=form.cleaned_data['contact'],
                            is_active=form.cleaned_data['is_active'])
            except (ValidationError, ConflictError, OperationalError) as error:
                status = _error(form, error)
            else:
                messages.success(request,'Vendor berhasil disimpan.')
                return _redirect('procurement:vendor_list')
    return _retry(render(request,'procurement/vendor_form.html',dict(form=form,target=target),status=status))


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@login_required
@require_http_methods(['GET','POST'])
def vendor_create(request):
    return _vendor_form(request)


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@login_required
@require_http_methods(['GET','POST'])
def vendor_edit(request, vendor_id):
    return _vendor_form(request,vendor_id)


def _target(request, request_id):
    return get_object_or_404(visible_requests(request.user), pk=request_id)


@sensitive_variables()
def _render_comparison(request, target, *, selection_form=None, status=200, message=''):
    revision = sourcing_revision(target)
    editable = can_source(active_actor(request.user.pk), target)
    quotes = Quotation.objects.filter(revision=revision).select_related('vendor') if revision else Quotation.objects.none()
    if selection_form is None and editable:
        selection_form = SelectionForm(quotations=quotes,
                                        initial=_initial(request,'REQUEST',str(target.pk),'quotation.select',target.version))
    current = Paginator(quotes.prefetch_related('items__revision_item').order_by('total_minor','fulfillment_days','pk'),25).get_page(request.GET.get('page'))
    current.object_list = comparison_rows(revision,current.object_list)
    history = target.revisions.values_list('pk',flat=True)
    historical = Quotation.objects.filter(revision_id__in=history).exclude(revision=revision).select_related('vendor','revision').prefetch_related('items__revision_item').order_by('-created_at','pk')
    history_page = Paginator(historical,25).get_page(request.GET.get('history_page'))
    return _retry(render(request,'procurement/quotation_list.html',dict(breadcrumb_page='quotation_list',target=target,revision=revision,
                         page_obj=current,history_page=history_page,editable=editable,selection_form=selection_form,
                         message=message),status=status))


@login_required
@require_safe
def quotation_list(request, request_id):
    return _render_comparison(request,_target(request,request_id))


@sensitive_variables()
def _quote_form(request, request_id, quotation_id=None):
    target = _target(request,request_id)
    require_procurement(request.user)
    quote = None if quotation_id is None else get_object_or_404(Quotation.objects.select_related('revision'),pk=quotation_id,revision__request=target)
    revision = quote.revision if quote else sourcing_revision(target)
    if request.method == 'GET' and (not can_source(active_actor(request.user.pk),target)
                                   or quote is not None and quote.revision.number != target.current_revision_number):
        return _render_comparison(request,target,status=409,message='Penawaran tidak dapat diedit pada status atau revisi ini.')
    action = 'quotation.create' if quote is None else 'quotation.edit'
    initial = _initial(request,'REQUEST',str(target.pk),action,target.version)
    if quote:
        initial.update({field:getattr(quote,field) for field in ['reference','quoted_on','valid_until','fulfillment_days']})
        initial['vendor'] = quote.vendor_id
    snapshots = {item.pk:item for item in revision.items.order_by('position')} if revision else {}
    prices = {item.revision_item_id:format_money(item.unit_price_minor) for item in quote.items.all()} if quote else {}
    rows = [dict(revision_item_id=item.pk,unit_price=prices.get(item.pk,'')) for item in snapshots.values()]
    bound = request.POST if request.method == 'POST' else None
    form = QuotationForm(bound,initial=initial)
    formset = QuotationLineFormSet(bound,initial=rows,prefix='items')
    status = 200
    if request.method == 'POST':
        status = 400
        header_valid, items_valid = form.is_valid(), formset.is_valid()
        if header_valid and items_valid:
            try:
                nonce = load_action_token(form.cleaned_data['action_token'], **_scope(request,'REQUEST',str(target.pk),action))
                save_quotation(ActionContext(request.user.pk,nonce,form.cleaned_data['expected_version']),
                               request_id=target.pk,quotation_id=quotation_id,data=form.to_input(formset))
            except (ValidationError,ConflictError,OperationalError) as error:
                status = _error(form,error)
            else:
                messages.success(request,'Penawaran berhasil disimpan. Pemilihan dilakukan terpisah.')
                return _redirect('procurement:quotation_list',request_id=target.pk)
    entries = []
    for row in formset.forms:
        try:
            item = snapshots.get(UUID(str(row['revision_item_id'].value())))
        except (ValueError,TypeError):
            item = None
        entries.append(dict(form=row,item=item))
    return _retry(render(request,'procurement/quotation_form.html',dict(target=target,quote=quote,revision=revision,
                         form=form,formset=formset,entries=entries),status=status))


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@login_required
@require_http_methods(['GET','POST'])
def quotation_create(request,request_id):
    return _quote_form(request,request_id)


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@login_required
@require_http_methods(['GET','POST'])
def quotation_edit(request,request_id,quotation_id):
    return _quote_form(request,request_id,quotation_id)


@sensitive_variables()
def _select(request,request_id):
    target = _target(request,request_id)
    require_procurement(request.user)
    quotes = Quotation.objects.filter(revision__request=target).select_related('vendor')
    form = SelectionForm(request.POST,quotations=quotes)
    status = 400
    if form.is_valid():
        try:
            nonce = load_action_token(form.cleaned_data['action_token'], **_scope(request,'REQUEST',str(target.pk),'quotation.select'))
            select_quotation(ActionContext(request.user.pk,nonce,form.cleaned_data['expected_version']),request_id=target.pk,
                             quotation_id=form.cleaned_data['quotation'].pk,reason=form.cleaned_data['reason'],
                             single_source_reason=form.cleaned_data['single_source_reason'])
        except (ValidationError,ConflictError,OperationalError) as error:
            status = _error(form,error)
        else:
            messages.success(request,'Penawaran berhasil dipilih. PO belum diterbitkan.')
            return _redirect('procurement:quotation_list',request_id=target.pk)
    target.refresh_from_db()
    return _render_comparison(request,target,selection_form=form,status=status)


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@login_required
@require_POST
def quotation_select(request,request_id):
    return _select(request,request_id)
