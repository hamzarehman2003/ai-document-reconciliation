"""Response shape for audit log events."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import AuditAction, AuditObject


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    actor: str
    action: AuditAction
    object_type: AuditObject
    object_id: int
    details: dict[str, Any]
