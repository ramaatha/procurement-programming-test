# filepath: procurement/stages.py
from procurement.models import OrderStatus, RequestStatus


STAGE_LABELS = dict(RequestStatus.choices) | dict(OrderStatus.choices)
STAGE_LABELS[OrderStatus.CLOSED_SHORT] = 'Selesai dengan kekurangan'


def stage_label(code: str) -> str:
    return STAGE_LABELS.get(code,'Tahap tidak dikenal')


def audit_label(event) -> str:
    if event.action == 'request.review':
        return {'APPROVE':'Disetujui','REQUEST_CHANGES':'Diminta revisi','REJECT':'Ditolak'}.get(event.changes.get('decision'),'Keputusan review')
    if event.action == 'order.close':
        return 'Sisa PO ditutup' if event.changes.get('status') == OrderStatus.CLOSED_SHORT else 'PO dibatalkan'
    return {
        'request.create':'Draft dibuat','request.edit':'Draft diperbarui','request.submit':'Permintaan diajukan',
        'request.cancel':'Permintaan dibatalkan','request.revision':'Dikembalikan untuk revisi',
        'quotation.create':'Penawaran dibuat','quotation.edit':'Penawaran diperbarui',
        'quotation.select':'Vendor dipilih','order.issue':'PO diterbitkan','receipt.post':'Penerimaan dicatat',
    }.get(event.action,'Perubahan pengadaan')
