"""An uploaded file and where it is in the processing pipeline."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, text_enum

if TYPE_CHECKING:
    from app.models.batch import Batch
    from app.models.extraction import Extraction
    from app.models.field_evidence import FieldEvidence
    from app.models.line_item import LineItem
    from app.models.match_case import MatchCase

Money = Numeric(14, 2)


class DocumentType(StrEnum):
    UNKNOWN = "unknown"
    INVOICE = "invoice"
    PURCHASE_ORDER = "purchase_order"
    GOODS_RECEIPT = "goods_receipt"


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(500))
    doc_type: Mapped[DocumentType] = mapped_column(
        text_enum(DocumentType), default=DocumentType.UNKNOWN
    )
    status: Mapped[DocumentStatus] = mapped_column(
        text_enum(DocumentStatus), default=DocumentStatus.UPLOADED
    )
    page_count: Mapped[int | None]
    error_message: Mapped[str | None] = mapped_column(Text)

    # Filled in by AI extraction (empty until the document is processed).
    document_number: Mapped[str | None] = mapped_column(String(100))
    vendor_name: Mapped[str | None] = mapped_column(String(200))
    buyer_name: Mapped[str | None] = mapped_column(String(200))
    issue_date: Mapped[date | None]
    due_date: Mapped[date | None]
    po_reference: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str | None] = mapped_column(String(3))
    subtotal: Mapped[Decimal | None] = mapped_column(Money)
    tax: Mapped[Decimal | None] = mapped_column(Money)
    total: Mapped[Decimal | None] = mapped_column(Money)

    batch: Mapped["Batch"] = relationship(back_populates="documents")
    line_items: Mapped[list["LineItem"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="LineItem.position",
    )
    extractions: Mapped[list["Extraction"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Extraction.id",
    )
    evidence: Mapped[list["FieldEvidence"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="FieldEvidence.id",
    )
    # Only invoices have a match case.
    match_case: Mapped["MatchCase | None"] = relationship(
        foreign_keys="MatchCase.invoice_id",
        back_populates="invoice",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
