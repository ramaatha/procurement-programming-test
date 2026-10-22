# filepath: accounts/views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

from accounts.forms import LoginForm


class AccountLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "registration/login.html"
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
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/home.html")
