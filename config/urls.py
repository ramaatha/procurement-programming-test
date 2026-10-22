# filepath: config/urls.py
from django.urls import include, path

urlpatterns = [path("", include("accounts.urls"))]
