"""Read a document with the AI and save what it found.

The AI only reads. Checking that the numbers make sense is done later by
plain Python rules, never by the AI.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.llm import get_extractor
from app.llm.prompt import PROMPT_VERSION
from app.llm.schema import DocumentExtraction
from app.models import Document, DocumentType, Extraction, LineItem
from app.services.pages import prepare_document
from app.storage import LocalStorage

CENT = Decimal("0.01")
THOUSANDTH = Decimal("0.001")


def extract_document(
    session: Session, storage: LocalStorage, document: Document
) -> None:
    """Fill in the document's fields and line items from the AI (or the cache).

    Does not commit: the caller decides when the work is saved.
    """
    cached = find_cached_extraction(session, document.checksum)
    if cached is not None:
        data = DocumentExtraction.model_validate(cached.data)
    else:
        prepared = prepare_document(
            storage.path(document.storage_key),
            document.content_type,
            settings.max_pages,
        )
        result = get_extractor().extract(prepared)
        data = result.data
        session.add(
            Extraction(
                document=document,
                checksum=document.checksum,
                model=result.model,
                prompt_version=PROMPT_VERSION,
                data=data.model_dump(mode="json"),
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                duration_ms=result.duration_ms,
            )
        )
    apply_extraction(document, data)


def find_cached_extraction(session: Session, checksum: str) -> Extraction | None:
    """The latest extraction of this exact file with the current prompt."""
    return session.scalars(
        select(Extraction)
        .where(
            Extraction.checksum == checksum,
            Extraction.prompt_version == PROMPT_VERSION,
        )
        .order_by(Extraction.id.desc())
        .limit(1)
    ).first()


def apply_extraction(document: Document, data: DocumentExtraction) -> None:
    """Copy the AI's answer onto the document, cleaning every value."""
    document.doc_type = DocumentType(data.doc_type)
    document.document_number = clean_text(data.document_number, 100)
    document.vendor_name = clean_text(data.vendor_name, 200)
    document.buyer_name = clean_text(data.buyer_name, 200)
    document.issue_date = parse_date(data.issue_date)
    document.due_date = parse_date(data.due_date)
    document.po_reference = clean_text(data.po_reference, 100)
    document.currency = clean_currency(data.currency)
    document.subtotal = to_decimal(data.subtotal, CENT)
    document.tax = to_decimal(data.tax, CENT)
    document.total = to_decimal(data.total, CENT)
    # Replacing the list deletes the old line items (delete-orphan).
    document.line_items = [
        LineItem(
            position=position,
            sku=clean_text(item.sku, 100),
            description=clean_text(item.description, 500) or "",
            quantity=to_decimal(item.quantity, THOUSANDTH),
            quantity_ordered=to_decimal(item.quantity_ordered, THOUSANDTH),
            unit_price=to_decimal(item.unit_price, CENT),
            line_total=to_decimal(item.line_total, CENT),
        )
        for position, item in enumerate(data.line_items, start=1)
    ]


def clean_text(value: str | None, max_length: int) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()[:max_length]


def parse_date(value: str | None) -> date | None:
    """'2026-01-23' → date. Anything unreadable becomes None, not an error."""
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def clean_currency(value: str | None) -> str | None:
    code = (value or "").strip().upper()
    return code if len(code) == 3 and code.isalpha() else None


def to_decimal(value: float | None, step: Decimal) -> Decimal | None:
    """Exact decimal from the AI's number, rounded half up (1234.505 → 1234.51)."""
    if value is None:
        return None
    return Decimal(str(value)).quantize(step, rounding=ROUND_HALF_UP)
