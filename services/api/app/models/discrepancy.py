"""One problem found by the matching rules, explained in plain words."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, text_enum
from app.rules.types import Code, Severity

if TYPE_CHECKING:
    from app.models.match_case import MatchCase


class Discrepancy(Base):
    __tablename__ = "discrepancies"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("match_cases.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[Code] = mapped_column(text_enum(Code))
    severity: Mapped[Severity] = mapped_column(text_enum(Severity))
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Values the problem is about: [{"document_id": 161, "field": "total"}, ...]
    refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    case: Mapped["MatchCase"] = relationship(back_populates="discrepancies")
