# filepath: procurement/urls.py
from django.urls import path
from procurement.views import requests

app_name='procurement'
urlpatterns=[
    path('requests/',requests.request_list,name='request_list'),
    path('requests/new/',requests.request_create,name='request_create'),
    path('requests/<uuid:request_id>/',requests.request_detail,name='request_detail'),
    path('requests/<uuid:request_id>/edit/',requests.request_edit,name='request_edit'),
    path('requests/<uuid:request_id>/submit/',requests.request_submit,name='request_submit'),
    path('requests/<uuid:request_id>/cancel/',requests.request_cancel,name='request_cancel'),
    path('requests/<uuid:request_id>/revisions/<int:number>/',requests.request_revision,name='request_revision'),
]
