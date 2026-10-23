# filepath: procurement/stages.py
from procurement.models import OrderStatus, RequestStatus


STAGE_LABELS = {code: label.title() for code, label in (*RequestStatus.choices, *OrderStatus.choices)}
STAGE_LABELS[OrderStatus.CLOSED_SHORT] = 'Selesai Dengan Kekurangan'


def stage_label(code: str) -> str:
    return STAGE_LABELS.get(code,'Tahap Tidak Dikenal')


def audit_label(event) -> str:
    if event.action == 'request.review':
        return {'APPROVE':'Disetujui','REQUEST_CHANGES':'Diminta Revisi','REJECT':'Ditolak'}.get(event.changes.get('decision'),'Keputusan Review')
    if event.action == 'order.close':
        return 'Sisa PO Ditutup' if event.changes.get('status') == OrderStatus.CLOSED_SHORT else 'PO Dibatalkan'
    return {
        'request.create':'Draft Dibuat','request.edit':'Draft Diperbarui','request.submit':'Permintaan Diajukan',
        'request.cancel':'Permintaan Dibatalkan','request.revision':'Dikembalikan Untuk Revisi',
        'quotation.create':'Penawaran Dibuat','quotation.edit':'Penawaran Diperbarui',
        'quotation.select':'Vendor Dipilih','order.issue':'PO Diterbitkan','receipt.post':'Penerimaan Dicatat',
    }.get(event.action,'Perubahan Pengadaan')
