"""Response shapes for documents.

Money and quantities are Decimals, sent as strings ("1234.50") so no
precision is lost on the way to the browser.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models import Document, DocumentStatus, DocumentType


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    filename: str
    content_type: str
    size_bytes: int
    doc_type: DocumentType
    status: DocumentStatus
    page_count: int | None
    error_message: str | None
    document_number: str | None
    vendor_name: str | None
    buyer_name: str | None
    issue_date: date | None
    due_date: date | None
    po_reference: str | None
    currency: str | None
    subtotal: Decimal | None
    tax: Decimal | None
    total: Decimal | None
    created_at: datetime
    updated_at: datetime


class LineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    sku: str | None
    description: str
    quantity: Decimal | None
    quantity_ordered: Decimal | None
    unit_price: Decimal | None
    line_total: Decimal | None


class ExtractionInfo(BaseModel):
    """How the data was read: which model, and what it cost."""

    model_config = ConfigDict(from_attributes=True)

    model: str
    prompt_version: str
    input_tokens: int | None
    output_tokens: int | None
    duration_ms: int | None
    created_at: datetime


class EvidenceOut(BaseModel):
    """Where a value was found: page number and a box as fractions (0-1) of the page."""

    model_config = ConfigDict(from_attributes=True)

    field: str
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    source: str
    confidence: float | None


class DocumentDetail(DocumentOut):
    line_items: list[LineItemOut]
    latest_extraction: ExtractionInfo | None
    evidence: list[EvidenceOut]

    @classmethod
    def from_document(cls, document: Document) -> "DocumentDetail":
        latest = document.extractions[-1] if document.extractions else None
        return cls(
            **DocumentOut.model_validate(document).model_dump(),
            line_items=[LineItemOut.model_validate(i) for i in document.line_items],
            latest_extraction=ExtractionInfo.model_validate(latest) if latest else None,
            evidence=[EvidenceOut.model_validate(e) for e in document.evidence],
        )
