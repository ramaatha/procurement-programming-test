# filepath: config/urls.py
from django.urls import include, path
from config.views import favicon

urlpatterns = [path('favicon.ico',favicon),path("", include("accounts.urls")), path("", include("procurement.urls"))]
handler400 = 'config.views.bad_request'
handler403 = 'config.views.permission_denied'
handler404 = 'config.views.page_not_found'
handler500 = 'config.views.server_error'
