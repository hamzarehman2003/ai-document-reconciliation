"""Build ready-made test documents straight in the database (no upload, no AI)."""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Batch, Document, DocumentStatus, DocumentType, LineItem

VENDOR = "Apex Office Supplies"


def unique(prefix: str) -> str:
    """Document numbers that can't clash with documents in the dev database."""
    return f"{prefix}-{uuid4().hex[:8].upper()}"


def add_document(
    session: Session,
    doc_type: DocumentType,
    number: str,
    *,
    quantity: str,
    po_reference: str | None = None,
    vendor: str = VENDOR,
    line_total: str | None = None,
) -> Document:
    """A processed document with one line: SKU A-1 at 5.00 each."""
    quantity_value = Decimal(quantity)
    total = Decimal(line_total) if line_total else quantity_value * Decimal("5.00")
    document = Document(
        batch=Batch(name="Test"),
        filename=f"{number}.pdf",
        content_type="application/pdf",
        size_bytes=1,
        checksum=uuid4().hex,
        storage_key="x",
        status=DocumentStatus.PROCESSED,
        doc_type=doc_type,
        document_number=number,
        vendor_name=vendor,
        po_reference=po_reference,
        subtotal=total,
        tax=Decimal("0"),
        total=total,
        line_items=[
            LineItem(
                position=1,
                sku="A-1",
                description="Copy paper",
                quantity=quantity_value,
                unit_price=Decimal("5.00"),
                line_total=total,
            )
        ],
    )
    session.add(document)
    session.flush()
    return document


def add_three_way_set(
    session: Session, *, ordered: str, received: str, billed: str
) -> tuple[Document, Document, Document]:
    """A purchase order, its goods receipt and its invoice: (po, receipt, invoice)."""
    po_number = unique("PO")
    order = add_document(
        session, DocumentType.PURCHASE_ORDER, po_number, quantity=ordered
    )
    receipt = add_document(
        session,
        DocumentType.GOODS_RECEIPT,
        unique("GRN"),
        quantity=received,
        po_reference=po_number,
    )
    invoice = add_document(
        session,
        DocumentType.INVOICE,
        unique("INV"),
        quantity=billed,
        po_reference=po_number,
    )
    return order, receipt, invoice
