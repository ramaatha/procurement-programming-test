from procurement.inputs import ReceiptInput, ReceiptLineInput
from procurement.models import EvidenceType


def receipt_data(order, accepted='6', rejected='2', reason='Kemasan rusak', **changes):
    values = dict(reference='SJ-001', notes='Pemeriksaan di lokasi', evidence_type=EvidenceType.GOODS_DELIVERY,
                  service_started_on=None, service_ended_on=None,
                  items=(ReceiptLineInput(order.items.get().pk, accepted, rejected, reason),))
    values.update(changes)
    return ReceiptInput(**values)
