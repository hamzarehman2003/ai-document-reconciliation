"""The audit log: what happened, who did it, and when."""

from fastapi import APIRouter
from sqlalchemy import and_, or_, select

from app.db import SessionDep
from app.models import AuditEvent, AuditObject, MatchCase
from app.schemas.audit import AuditEventOut

router = APIRouter(prefix="/api/audit-events", tags=["audit log"])


@router.get("")
def list_audit_events(
    session: SessionDep,
    object_type: AuditObject | None = None,
    object_id: int | None = None,
    document_id: int | None = None,
    limit: int = 100,
) -> list[AuditEventOut]:
    """Newest first. `document_id` gives a document's full history, including
    its 3-way match case (approvals, status changes)."""
    query = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(min(limit, 500))
    if object_type is not None:
        query = query.where(AuditEvent.object_type == object_type)
    if object_id is not None:
        query = query.where(AuditEvent.object_id == object_id)
    if document_id is not None:
        case_ids = select(MatchCase.id).where(MatchCase.invoice_id == document_id)
        query = query.where(
            or_(
                and_(
                    AuditEvent.object_type == AuditObject.DOCUMENT,
                    AuditEvent.object_id == document_id,
                ),
                and_(
                    AuditEvent.object_type == AuditObject.MATCH_CASE,
                    AuditEvent.object_id.in_(case_ids),
                ),
            )
        )
    return [AuditEventOut.model_validate(event) for event in session.scalars(query)]
