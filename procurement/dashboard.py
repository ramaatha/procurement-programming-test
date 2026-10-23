# filepath: procurement/dashboard.py
from accounts.models import Role
from procurement.policies import active_actor
from procurement.selectors import visible_orders, visible_requests


def work_queue(actor) -> dict:
    current = active_actor(actor.pk)
    orders = current.role == Role.RECEIVER
    if orders:
        queryset = visible_orders(current).filter(status__in=['ISSUED','PARTIALLY_RECEIVED']).order_by('issued_at','pk')
        title = 'Pesanan Menunggu Penerimaan'
    else:
        queryset = visible_requests(current)
        if current.role == Role.APPROVER:
            queryset = queryset.filter(status='SUBMITTED').exclude(requester_id=current.pk)
            title = 'Permintaan Menunggu Keputusan'
        elif current.role == Role.PROCUREMENT:
            queryset = queryset.filter(status='APPROVED',order__isnull=True)
            title = 'Permintaan Siap Diproses'
        elif current.role == Role.REQUESTER:
            queryset = queryset.filter(status__in=['DRAFT','CHANGES_REQUESTED'])
            title = 'Draft Dan Permintaan Yang Perlu Revisi'
        else:
            queryset = queryset.none()
            title = 'Administrasi Akun Dan Vendor'
        queryset = queryset.order_by('created_at','pk')
    return dict(queue=queryset[:8],queue_title=title,queue_orders=orders)
