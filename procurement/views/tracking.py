# filepath: procurement/views/tracking.py
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import QueryDict
from django.shortcuts import render
from django.views.decorators.http import require_safe

from procurement.forms.tracking import TrackingFilterForm
from procurement.selectors import order_tracking_query, request_tracking_query


def _list(request, *, orders: bool):
    form = TrackingFilterForm(request.GET,orders_only=orders)
    valid = form.is_valid()
    filters = form.cleaned_data if valid else {}
    query = order_tracking_query if orders else request_tracking_query
    queryset = query(request.user,query=filters.get('q',''),kind=filters.get('kind',''),stage=filters.get('stage',''))
    if not valid:
        queryset = queryset.none()
    page = Paginator(queryset,25).get_page(request.GET.get('page'))
    params = QueryDict(mutable=True)
    for key,value in filters.items():
        if value:
            params[key] = value
    context = dict(page_obj=page,filter_form=form,has_filters=any(request.GET.get(key) for key in ('q','kind','stage')),
                   previous_url='',next_url='')
    for condition,key,number in ((page.has_previous(),'previous_url',page.number-1),(page.has_next(),'next_url',page.number+1)):
        if condition:
            params['page'] = str(number)
            context[key] = '?'+params.urlencode()
    return render(request,'procurement/order_list.html' if orders else 'procurement/request_list.html',context,status=200 if valid else 400)


@login_required
@require_safe
def request_list(request):
    return _list(request,orders=False)


@login_required
@require_safe
def order_list(request):
    return _list(request,orders=True)


def audit_context(target, params) -> dict:
    page = Paginator(target.audit_events.order_by('created_at','pk'),25).get_page(params.get('history_page'))
    return dict(audit_page=page)
