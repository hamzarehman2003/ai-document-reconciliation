"""Where an extracted value appears on the page (for click-to-highlight).

The box is stored as fractions of the page size (0 to 1), so it fits the
page image at any zoom level.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class FieldEvidence(Base):
    __tablename__ = "field_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    # e.g. "total" or "line_items.3.unit_price"
    field: Mapped[str] = mapped_column(String(60))
    page: Mapped[int]  # 1, 2, 3...
    x0: Mapped[float] = mapped_column(Float)
    y0: Mapped[float] = mapped_column(Float)
    x1: Mapped[float] = mapped_column(Float)
    y1: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(String(300))  # the text found on the page
    source: Mapped[str] = mapped_column(String(20))  # "pdf_text" or "ocr"
    confidence: Mapped[float | None] = mapped_column(Float)  # OCR only

    document: Mapped["Document"] = relationship(back_populates="evidence")
