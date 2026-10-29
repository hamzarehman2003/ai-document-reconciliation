"""The 3-way match of one invoice with its purchase order and goods receipts."""

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, text_enum

if TYPE_CHECKING:
    from app.models.discrepancy import Discrepancy
    from app.models.document import Document


class MatchStatus(StrEnum):
    MATCHED = "matched"  # invoice, PO and receipts agree
    NEEDS_REVIEW = "needs_review"  # at least one problem found
    WAITING = "waiting"  # no problem so far, but the PO or a receipt is missing


# A delivery can come in several parts, so one case can have several receipts.
match_case_receipts = Table(
    "match_case_receipts",
    Base.metadata,
    Column(
        "case_id",
        ForeignKey("match_cases.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "document_id",
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class MatchCase(TimestampMixin, Base):
    __tablename__ = "match_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), unique=True
    )
    purchase_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    status: Mapped[MatchStatus] = mapped_column(text_enum(MatchStatus))

    invoice: Mapped["Document"] = relationship(
        foreign_keys=[invoice_id], back_populates="match_case"
    )
    purchase_order: Mapped["Document | None"] = relationship(
        foreign_keys=[purchase_order_id]
    )
    goods_receipts: Mapped[list["Document"]] = relationship(
        secondary=match_case_receipts, order_by="Document.id"
    )
    discrepancies: Mapped[list["Discrepancy"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Discrepancy.id",
    )

    @property
    def waiting_for(self) -> list[str]:
        """What is still missing for a full check: purchase_order, goods_receipt."""
        if not self.invoice.po_reference:
            return []  # without a PO number there is nothing to wait for
        missing = []
        if self.purchase_order_id is None:
            missing.append("purchase_order")
        if not self.goods_receipts:
            missing.append("goods_receipt")
        return missing
