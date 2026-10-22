# filepath: accounts/urls.py
from django.urls import path

from accounts import views

app_name = "accounts"
urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.AccountLoginView.as_view(), name="login"),
    path("logout/", views.AccountLogoutView.as_view(), name="logout"),
]
