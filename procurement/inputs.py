# filepath: procurement/inputs.py
from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class RequestLineInput:
    name: str
    unit: str
    quantity: str
    unit_price: str


@dataclass(frozen=True)
class DraftInput:
    kind: str
    title: str
    reason: str
    destination: str
    needed_on: date | None
    items: tuple[RequestLineInput, ...]


@dataclass(frozen=True)
class QuoteLineInput:
    revision_item_id: UUID
    unit_price: str


@dataclass(frozen=True)
class QuotationInput:
    vendor_id: UUID
    reference: str
    quoted_on: date
    valid_until: date
    fulfillment_days: int
    items: tuple[QuoteLineInput, ...]


@dataclass(frozen=True)
class ReceiptLineInput:
    order_item_id: UUID
    accepted: str
    rejected: str
    rejection_reason: str


@dataclass(frozen=True)
class ReceiptInput:
    reference: str
    notes: str
    evidence_type: str
    service_started_on: date | None
    service_ended_on: date | None
    items: tuple[ReceiptLineInput, ...]
