"""A record of one AI extraction: what the model returned, and what it cost.

Used for auditing, tracking token usage, and as a cache: the same file
(same checksum) with the same prompt version is never sent to the AI twice.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(20))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    duration_ms: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="extractions")
