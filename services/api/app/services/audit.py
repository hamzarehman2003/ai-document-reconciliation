"""Write to the audit log.

The event is added to the caller's transaction, so it is saved only if the
action itself is saved: the log never claims something that didn't happen.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditAction, AuditEvent, AuditObject

SYSTEM = "system"
# No login yet: people are named by the request, with this default.
DEFAULT_REVIEWER = "Demo reviewer"


def record(
    session: Session,
    actor: str,
    action: AuditAction,
    object_type: AuditObject,
    object_id: int,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditEvent(
            actor=actor,
            action=action,
            object_type=object_type,
            object_id=object_id,
            details=details or {},
        )
    )
