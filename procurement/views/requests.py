# filepath: procurement/views/requests.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.paginator import Paginator
from django.db import OperationalError
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.debug import sensitive_post_parameters,sensitive_variables
from django.views.decorators.http import require_http_methods,require_POST,require_safe

from accounts.models import Role
from common.actions import ActionContext,load_action_token,make_action_token
from common.errors import ConflictError
from common.forms import ActionForm
from common.http import database_busy,validation_errors
from common.numbers import document_total,format_money,format_quantity,line_total
from procurement.forms.requests import CancelForm,DraftForm,RequestLineFormSet,ReviewForm,RevisionForm
from procurement.models import ApprovalDecision,Decision,PurchaseOrder,RequestStatus
from procurement.policies import active_actor,require_procurement,require_request_owner,require_request_reviewer
from procurement.selectors import approval_queue,visible_requests
from procurement.services.requests import cancel_request,save_draft,submit_request,review_request,request_revision as return_for_revision
from procurement.views.tracking import audit_context, request_list


def _visible(request,request_id):
    return get_object_or_404(visible_requests(request.user),pk=request_id)


def _can_edit(actor,target) -> bool:
    return actor.role==Role.REQUESTER and target.requester_id==actor.pk and target.status in (RequestStatus.DRAFT,RequestStatus.CHANGES_REQUESTED) and not PurchaseOrder.objects.filter(request=target).exists()


def _can_cancel(actor,target) -> bool:
    return actor.role==Role.REQUESTER and target.requester_id==actor.pk and target.status in (RequestStatus.DRAFT,RequestStatus.CHANGES_REQUESTED,RequestStatus.SUBMITTED,RequestStatus.APPROVED) and not PurchaseOrder.objects.filter(request=target).exists()


def _rows(items,*,snapshot=False):
    return [dict(name=item.name,unit=item.unit,qty_milli=item.qty_milli,estimated_unit_price_minor=item.estimated_unit_price_minor,line_total_minor=item.line_total_minor if snapshot else line_total(item.qty_milli,item.estimated_unit_price_minor)) for item in items]


def _scope(request,target,action):
    return dict(actor_id=request.user.pk,target_type='REQUEST',target_key=str(target.pk) if target else 'new-request',action=action)


def _initial_action(request,target,action):
    return dict(action_token=make_action_token(**_scope(request,target,action)),expected_version=target.version)


@sensitive_variables()
def _render_detail(request,target,*,submit_form=None,cancel_form=None,review_form=None,revision_form=None,issue_form=None,status=200,message=''):
    from procurement.views.orders import issue_context
    order_context = issue_context(request,target,form=issue_form)
    editable=_can_edit(request.user,target)
    cancellable=_can_cancel(request.user,target)
    if submit_form is None and editable:
        submit_form=ActionForm(initial=_initial_action(request,target,'request.submit'))
        submit_form.fields['expected_version'].required=True
    if cancel_form is None and cancellable:
        cancel_form=CancelForm(initial=_initial_action(request,target,'request.cancel'))
    active_revision = target.revisions.filter(number=target.current_revision_number).select_related('approval__actor').first()
    unissued = not PurchaseOrder.objects.filter(request=target).exists()
    if (review_form is None and request.user.role == Role.APPROVER and target.requester_id != request.user.pk
            and target.status == RequestStatus.SUBMITTED and active_revision is not None and unissued
            and not ApprovalDecision.objects.filter(revision=active_revision).exists()):
        review_form = ReviewForm(initial=_initial_action(request,target,'request.review'))
    if (revision_form is None and request.user.role == Role.PROCUREMENT and target.status == RequestStatus.APPROVED
            and active_revision is not None and unissued
            and ApprovalDecision.objects.filter(revision=active_revision,decision=Decision.APPROVE).exists()):
        revision_form = RevisionForm(initial=_initial_action(request,target,'request.revision'))
    rows=_rows(target.items.all())
    from procurement.presentation import balance_rows
    balances = balance_rows(order_context['existing_order']) if order_context['existing_order'] else []
    response=render(request,'procurement/request_detail.html',dict(breadcrumb_page='request_detail',target=target,rows=rows,total_minor=document_total(row['line_total_minor'] for row in rows),editable=editable,submit_form=submit_form,cancel_form=cancel_form,review_form=review_form,revision_form=revision_form,active_revision=active_revision,revisions=target.revisions.select_related('approval__actor').order_by('-number'),balances=balances,message=message,**audit_context(target,request.GET),**order_context),status=status)
    if status==503:response['Retry-After']='1'
    return response


@login_required
@require_safe
def request_detail(request,request_id):
    return _render_detail(request,_visible(request,request_id))


@login_required
@require_safe
def approval_list(request):
    page = Paginator(approval_queue(request.user).order_by('created_at','pk'),25).get_page(request.GET.get('page'))
    return render(request,'procurement/approval_list.html',dict(page_obj=page))


@login_required
@require_safe
def request_revision(request,request_id,number):
    target=_visible(request,request_id)
    revision=get_object_or_404(target.revisions.select_related('approval__actor'),number=number)
    return render(request,'procurement/request_revision.html',dict(target=target,revision=revision,rows=_rows(revision.items.all(),snapshot=True)))


@sensitive_variables()
def _draft_form(request,target=None):
    actor=active_actor(request.user.pk)
    if target is None:
        if actor.role!=Role.REQUESTER:raise PermissionDenied
    else:
        require_request_owner(actor,target)
        if request.method=='GET' and not _can_edit(actor,target):
            return _render_detail(request,target,status=409,message='Permintaan tidak dapat diedit pada status ini.')
    creating=target is None
    action='request.create' if creating else 'request.edit'
    scope=_scope(request,target,action)
    initial=dict(kind='GOODS',action_token=make_action_token(**scope),expected_version=None if creating else target.version) if request.method=='GET' else None
    rows=[]
    if target is not None:
        if initial is not None:initial.update({field:getattr(target,field) for field in ('kind','title','reason','destination','needed_on')})
        rows=[dict(name=item.name,unit=item.unit,quantity=format_quantity(item.qty_milli),unit_price=format_money(item.estimated_unit_price_minor)) for item in target.items.all()]
    bound=request.POST if request.method=='POST' else None
    form=DraftForm(bound,initial=initial,creating=creating)
    formset=RequestLineFormSet(bound,initial=rows,prefix='items')
    status=200
    if request.method=='POST':
        status=400
        header_valid=form.is_valid();items_valid=formset.is_valid()
        if request.POST.get('intent')=='add_row' and formset.management_form.is_valid():
            try:
                load_action_token(request.POST.get('action_token',''),**scope)
                if target is not None and not _can_edit(actor,target):raise ConflictError()
                if formset.total_form_count()>=formset.max_num:raise ValidationError('Batas baris form tercapai.')
            except ValidationError as error:validation_errors(form,error)
            except ConflictError:form.add_error(None,'Status permintaan sudah berubah. Muat ulang data.');status=409
            else:
                expanded=request.POST.copy()
                expanded['items-TOTAL_FORMS']=str(formset.total_form_count()+1)
                formset=RequestLineFormSet(expanded,initial=rows,prefix='items')
                status=200
        elif header_valid and items_valid:
            try:
                nonce=load_action_token(form.cleaned_data['action_token'],**scope)
                result=save_draft(ActionContext(actor.pk,nonce,form.cleaned_data.get('expected_version')),request_id=None if creating else target.pk,data=form.to_input(formset))
            except ValidationError as error:validation_errors(form,error)
            except ConflictError:form.add_error(None,'Data sudah berubah atau token dipakai untuk isian lain. Muat ulang sebelum menyimpan.');status=409
            except OperationalError as error:
                if not database_busy(error):raise
                form.add_error(None,'Penyimpanan sedang sibuk. Coba kembali sebentar lagi.');status=503
            else:
                messages.success(request,'Draf berhasil disimpan.')
                response=redirect('procurement:request_detail',request_id=result.pk);response.status_code=303
                return response
    response=render(request,'procurement/request_form.html',dict(form=form,formset=formset,target=target,reload_url=request.path),status=status)
    if status==503:response['Retry-After']='1'
    return response


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@login_required
@require_http_methods(['GET','POST'])
def request_create(request):return _draft_form(request)


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@login_required
@require_http_methods(['GET','POST'])
def request_edit(request,request_id):return _draft_form(request,_visible(request,request_id))


@sensitive_variables()
def _transition(request,request_id,*,cancel=False):
    target=_visible(request,request_id)
    require_request_owner(request.user,target)
    action='request.cancel' if cancel else 'request.submit'
    form=CancelForm(request.POST) if cancel else ActionForm(request.POST)
    form.fields['expected_version'].required=True
    status=400
    if form.is_valid():
        try:
            nonce=load_action_token(form.cleaned_data['action_token'],**_scope(request,target,action))
            ctx=ActionContext(request.user.pk,nonce,form.cleaned_data['expected_version'])
            if cancel:result=cancel_request(ctx,request_id=target.pk,reason=form.cleaned_data['reason'])
            else:result=submit_request(ctx,request_id=target.pk)
        except ValidationError as error:validation_errors(form,error)
        except ConflictError:form.add_error(None,'Data atau status sudah berubah. Muat ulang halaman.');status=409
        except OperationalError as error:
            if not database_busy(error):raise
            form.add_error(None,'Penyimpanan sedang sibuk. Coba kembali sebentar lagi.');status=503
        else:
            messages.success(request,'Permintaan dibatalkan.' if cancel else 'Permintaan berhasil diajukan.')
            response=redirect('procurement:request_detail',request_id=result.pk);response.status_code=303
            return response
    target.refresh_from_db()
    return _render_detail(request,target,cancel_form=form if cancel else None,submit_form=None if cancel else form,status=status)


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@login_required
@require_POST
def request_submit(request,request_id):return _transition(request,request_id)


@sensitive_post_parameters('action_token','csrfmiddlewaretoken')
@login_required
@require_POST
def request_cancel(request,request_id):return _transition(request,request_id,cancel=True)


@sensitive_variables()
def _decision_transition(request, request_id, *, return_revision=False):
    target = _visible(request, request_id)
    if return_revision:
        require_procurement(request.user)
    else:
        require_request_reviewer(request.user, target)
    action = 'request.revision' if return_revision else 'request.review'
    form = RevisionForm(request.POST) if return_revision else ReviewForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            nonce = load_action_token(form.cleaned_data['action_token'], **_scope(request, target, action))
            ctx = ActionContext(request.user.pk, nonce, form.cleaned_data['expected_version'])
            if return_revision:
                result = return_for_revision(ctx, request_id=target.pk, reason=form.cleaned_data['reason'])
            else:
                result = review_request(ctx, request_id=target.pk,
                                        decision=form.cleaned_data['decision'], reason=form.cleaned_data['reason'])
        except ValidationError as error:
            validation_errors(form, error)
        except ConflictError:
            form.add_error(None, 'Data atau status sudah berubah. Muat ulang sebelum melanjutkan.')
            status = 409
        except OperationalError as error:
            if not database_busy(error):
                raise
            form.add_error(None, 'Penyimpanan sedang sibuk. Coba kembali sebentar lagi.')
            status = 503
        else:
            messages.success(request, 'Permintaan dikembalikan untuk revisi.' if return_revision else 'Keputusan berhasil disimpan.')
            response = redirect('procurement:request_detail', request_id=result.pk)
            response.status_code = 303
            return response
    target.refresh_from_db()
    return _render_detail(request, target, review_form=None if return_revision else form,
                          revision_form=form if return_revision else None, status=status)


@sensitive_post_parameters('action_token', 'csrfmiddlewaretoken')
@login_required
@require_POST
def request_review(request, request_id):
    return _decision_transition(request, request_id)


@sensitive_post_parameters('action_token', 'csrfmiddlewaretoken')
@login_required
@require_POST
def request_return_revision(request, request_id):
    return _decision_transition(request, request_id, return_revision=True)
