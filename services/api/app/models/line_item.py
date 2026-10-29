"""One row of a document's item table (what was ordered, received or billed)."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.document import Money

if TYPE_CHECKING:
    from app.models.document import Document

Quantity = Numeric(14, 3)  # allows things like 2.5 metres


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]  # 1, 2, 3... in the order printed on the page
    sku: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[Decimal | None] = mapped_column(Quantity)
    quantity_ordered: Mapped[Decimal | None] = mapped_column(Quantity)  # receipts
    unit_price: Mapped[Decimal | None] = mapped_column(Money)
    line_total: Mapped[Decimal | None] = mapped_column(Money)

    document: Mapped["Document"] = relationship(back_populates="line_items")
