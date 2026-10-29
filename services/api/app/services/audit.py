"""Write to the audit log.

The event is added to the caller's transaction, so it is saved only if the
action itself is saved: the log never claims something that didn't happen.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditEvent, AuditObject, Document, MatchCase

SYSTEM = "system"
# No login yet: people are named by the request, with this default.
DEFAULT_REVIEWER = "Demo reviewer"


@dataclass(frozen=True)
class Subject:
    """What an event is about, in words, and the document to open for it."""

    label: str
    document_id: int


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


def describe_subjects(
    session: Session, events: list[AuditEvent]
) -> dict[tuple[AuditObject, int], Subject]:
    """Name the document or invoice behind each event, in two queries in total.

    A match case is named after its invoice, so both link to the same document.
    Events whose object no longer exists are left out.
    """
    document_ids = {
        e.object_id for e in events if e.object_type == AuditObject.DOCUMENT
    }
    case_ids = {e.object_id for e in events if e.object_type == AuditObject.MATCH_CASE}
    subjects: dict[tuple[AuditObject, int], Subject] = {}

    documents = select(Document).where(Document.id.in_(document_ids))
    for document in session.scalars(documents):
        subjects[(AuditObject.DOCUMENT, document.id)] = _subject(document)

    cases = (
        select(MatchCase.id, Document)
        .join(MatchCase.invoice)
        .where(MatchCase.id.in_(case_ids))
    )
    for case_id, invoice in session.execute(cases):
        subjects[(AuditObject.MATCH_CASE, case_id)] = _subject(invoice)
    return subjects


def _subject(document: Document) -> Subject:
    # "CPF-84364 · Cedar & Pine Furniture", or the file name before the AI read it.
    parts = [document.document_number, document.vendor_name]
    label = " · ".join(part for part in parts if part) or document.filename
    return Subject(label=label, document_id=document.id)
