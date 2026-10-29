"""Response shape for audit log events."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import AuditAction, AuditEvent, AuditObject
from app.services.audit import Subject


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    actor: str
    action: AuditAction
    object_type: AuditObject
    object_id: int
    details: dict[str, Any]
    # "CPF-84364 · Cedar & Pine Furniture" (or the file name), and the document to open:
    # for a match case, its invoice. None if the object no longer exists.
    subject: str | None = None
    document_id: int | None = None

    @classmethod
    def from_event(cls, event: AuditEvent, subject: Subject | None) -> "AuditEventOut":
        out = cls.model_validate(event)
        if subject is not None:
            out.subject = subject.label
            out.document_id = subject.document_id
        return out
