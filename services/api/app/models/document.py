"""An uploaded file and where it is in the processing pipeline."""

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, text_enum

if TYPE_CHECKING:
    from app.models.batch import Batch


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

    batch: Mapped["Batch"] = relationship(back_populates="documents")
