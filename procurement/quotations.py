# filepath: procurement/quotations.py
from datetime import date

from django.core.exceptions import ValidationError

from common.numbers import document_total, line_total
from procurement.models import Quotation, RequestRevision


def quotation_issues(quote: Quotation, revision: RequestRevision, today: date) -> list[str]:
    issues = []
    if quote.revision_id != revision.pk:
        return ['Penawaran berasal dari revisi lain.']
    if not quote.vendor.is_active:
        issues.append('Vendor nonaktif.')
    if not quote.quoted_on <= today <= quote.valid_until:
        issues.append('Penawaran belum berlaku atau sudah kedaluwarsa.')
    expected = {item.pk: item for item in revision.items.all()}
    rows = list(quote.items.all())
    if not expected or len(rows) != len(expected) or {row.revision_item_id for row in rows} != set(expected):
        issues.append('Rincian penawaran tidak sesuai revisi.')
        return issues
    try:
        totals = [line_total(expected[row.revision_item_id].qty_milli, row.unit_price_minor) for row in rows]
        total = document_total(totals)
    except ValidationError:
        issues.append('Nilai penawaran tidak valid.')
        return issues
    if any(row.unit_price_minor <= 0 or row.line_total_minor != total_line for row, total_line in zip(rows, totals)) or total != quote.total_minor:
        issues.append('Total penawaran tidak konsisten dengan rincian.')
    if total > revision.estimated_total_minor:
        issues.append('Total penawaran melebihi plafon revisi.')
    return issues
