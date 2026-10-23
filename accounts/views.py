# filepath: accounts/views.py
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import OperationalError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods, require_safe

from accounts.forms import LoginForm, PasswordForm, UserForm
from accounts.models import Role, User
from accounts.policies import require_role
from accounts.services import reset_password, save_user
from common.actions import ActionContext, load_action_token, make_action_token
from common.errors import ConflictError
from common.http import database_busy as _busy, validation_errors as _validation_errors


class AccountLoginView(LoginView):
    authentication_form = LoginForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form: LoginForm) -> HttpResponse:
        response = super().form_valid(form)
        response.status_code = 303
        return response

    def form_invalid(self, form: LoginForm) -> HttpResponse:
        return self.render_to_response(self.get_context_data(form=form), status=400)


class AccountLogoutView(LogoutView):
    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = super().post(request, *args, **kwargs)
        response.status_code = 303
        return response


@login_required
@require_safe
def logout_confirm(request: HttpRequest) -> HttpResponse:
    return render(request, 'accounts/logout_confirm.html')


@login_required
@require_safe
def home(request: HttpRequest) -> HttpResponse:
    from procurement.dashboard import work_queue
    return render(request, 'accounts/home.html', work_queue(request.user))


@login_required
@require_safe
def user_list(request: HttpRequest) -> HttpResponse:
    require_role(request.user, Role.ADMIN)
    page = Paginator(User.objects.order_by('username','pk'), 25).get_page(request.GET.get('page'))
    return render(request, 'accounts/user_list.html', {'page_obj': page})


@sensitive_variables()
def _account_form(request: HttpRequest, target: User | None, *, password_only: bool = False) -> HttpResponse:
    creating = target is None
    action = 'account.create' if creating else 'account.password' if password_only else 'account.edit'
    target_key = 'new-user' if creating else str(target.pk)
    scope = dict(actor_id=request.user.pk,target_type='USER',target_key=target_key,action=action)
    initial = None
    if request.method != 'POST':
        initial = dict(action_token=make_action_token(**scope), expected_version=None if creating else target.version)
        if not password_only:
            initial.update(username='' if creating else target.username,role=Role.REQUESTER if creating else target.role,is_active=True if creating else target.is_active)
    bound_data = request.POST if request.method == 'POST' else None
    form = PasswordForm(bound_data,initial=initial) if password_only else UserForm(bound_data,initial=initial,creating=creating)
    status = 200
    if request.method == 'POST':
        status = 400
        if form.is_valid():
            try:
                nonce = load_action_token(form.cleaned_data['action_token'], **scope)
                ctx = ActionContext(request.user.pk, nonce, form.cleaned_data.get('expected_version'))
                if password_only:
                    result = reset_password(ctx,user_id=target.pk,new_password=form.cleaned_data['new_password'])
                else:
                    result = save_user(ctx,user_id=None if creating else target.pk,username=form.cleaned_data['username'],role=form.cleaned_data['role'],is_active=form.cleaned_data['is_active'],initial_password=form.cleaned_data.get('initial_password'))
            except ValidationError as error:
                _validation_errors(form,error)
            except ConflictError:
                status=409
                form.add_error(None,'Data sudah berubah atau aksi ini sudah digunakan. Muat ulang halaman sebelum melanjutkan.')
            except OperationalError as error:
                if not _busy(error):
                    raise
                status=503
                form.add_error(None,'Penyimpanan sedang sibuk. Coba kirim kembali sebentar lagi.')
            else:
                if result.pk == request.user.pk and (password_only or not result.is_active):
                    logout(request)
                    messages.success(request,'Akun diperbarui. Silakan masuk kembali.')
                    response=redirect('accounts:login')
                elif result.pk == request.user.pk and result.role != Role.ADMIN:
                    messages.success(request,'Peran akun Anda sudah diperbarui.')
                    response=redirect('accounts:home')
                else:
                    messages.success(request,'Password berhasil direset.' if password_only else 'Akun berhasil disimpan.')
                    response=redirect('accounts:user_edit',user_id=result.pk)
                response.status_code=303
                return response
    context=dict(form=form,target=target,creating=creating,reload_url=request.path)
    response=render(request,'accounts/user_password.html' if password_only else 'accounts/user_form.html',context,status=status)
    if status==503:
        response['Retry-After']='1'
    return response


@sensitive_post_parameters('initial_password','new_password','confirm_password','action_token','csrfmiddlewaretoken')
@login_required
@require_http_methods(['GET','POST'])
def user_create(request: HttpRequest) -> HttpResponse:
    require_role(request.user,Role.ADMIN)
    return _account_form(request,None)


@sensitive_post_parameters('initial_password','new_password','confirm_password','action_token','csrfmiddlewaretoken')
@login_required
@require_http_methods(['GET','POST'])
def user_edit(request: HttpRequest, user_id: int) -> HttpResponse:
    require_role(request.user,Role.ADMIN)
    return _account_form(request,get_object_or_404(User,pk=user_id))


@sensitive_post_parameters('initial_password','new_password','confirm_password','action_token','csrfmiddlewaretoken')
@login_required
@require_http_methods(['GET','POST'])
def user_password(request: HttpRequest, user_id: int) -> HttpResponse:
    require_role(request.user,Role.ADMIN)
    return _account_form(request,get_object_or_404(User,pk=user_id),password_only=True)
