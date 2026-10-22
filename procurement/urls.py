# filepath: procurement/urls.py
from django.urls import path
from procurement.views import requests
from procurement.views import sourcing
from procurement.views import orders

app_name='procurement'
urlpatterns=[
    path('orders/',orders.order_list,name='order_list'),
    path('orders/<uuid:order_id>/',orders.order_detail,name='order_detail'),
    path('orders/<uuid:order_id>/print/',orders.order_print,name='order_print'),
    path('requests/<uuid:request_id>/issue-po/',orders.order_issue,name='order_issue'),
    path('vendors/',sourcing.vendor_list,name='vendor_list'),
    path('vendors/new/',sourcing.vendor_create,name='vendor_create'),
    path('vendors/<uuid:vendor_id>/edit/',sourcing.vendor_edit,name='vendor_edit'),
    path('requests/<uuid:request_id>/quotations/',sourcing.quotation_list,name='quotation_list'),
    path('requests/<uuid:request_id>/quotations/new/',sourcing.quotation_create,name='quotation_create'),
    path('requests/<uuid:request_id>/quotations/select/',sourcing.quotation_select,name='quotation_select'),
    path('requests/<uuid:request_id>/quotations/<uuid:quotation_id>/edit/',sourcing.quotation_edit,name='quotation_edit'),
    path('approvals/',requests.approval_list,name='approval_list'),
    path('requests/',requests.request_list,name='request_list'),
    path('requests/new/',requests.request_create,name='request_create'),
    path('requests/<uuid:request_id>/',requests.request_detail,name='request_detail'),
    path('requests/<uuid:request_id>/edit/',requests.request_edit,name='request_edit'),
    path('requests/<uuid:request_id>/submit/',requests.request_submit,name='request_submit'),
    path('requests/<uuid:request_id>/cancel/',requests.request_cancel,name='request_cancel'),
    path('requests/<uuid:request_id>/review/',requests.request_review,name='request_review'),
    path('requests/<uuid:request_id>/request-revision/',requests.request_return_revision,name='request_return_revision'),
    path('requests/<uuid:request_id>/revisions/<int:number>/',requests.request_revision,name='request_revision'),
]
