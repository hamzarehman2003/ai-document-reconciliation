"""The audit log: who did what, when, and to which document or match case."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, text_enum


class AuditAction(StrEnum):
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_PROCESSED = "document_processed"
    DOCUMENT_FAILED = "document_failed"
    FIELD_CORRECTED = "field_corrected"
    MATCH_STATUS_CHANGED = "match_status_changed"
    CASE_APPROVED = "case_approved"
    CASE_REJECTED = "case_rejected"
    CASE_REOPENED = "case_reopened"
    DECISION_RESET = "decision_reset"
    CASE_EXPORTED = "case_exported"


class AuditObject(StrEnum):
    DOCUMENT = "document"
    MATCH_CASE = "match_case"


class AuditEvent(Base):
    __tablename__ = "audit_events"
    # History is always looked up per object.
    __table_args__ = (Index("ix_audit_events_object", "object_type", "object_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actor: Mapped[str] = mapped_column(String(100))  # "system" or a reviewer's name
    action: Mapped[AuditAction] = mapped_column(text_enum(AuditAction))
    object_type: Mapped[AuditObject] = mapped_column(text_enum(AuditObject))
    object_id: Mapped[int]
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
