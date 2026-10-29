"""A person's decision on a match case: approve (OK to pay), reject, or reopen."""

from enum import StrEnum

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditObject, MatchCase, ReviewStatus
from app.services.audit import record


class Decision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REOPEN = "reopen"


class ReviewNotAllowedError(Exception):
    """The decision can't be made right now (shown to the user)."""


class NoteRequiredError(ValueError):
    """The decision needs a note explaining it (shown to the user)."""


def decide(
    session: Session,
    case: MatchCase,
    decision: Decision,
    reviewer: str,
    note: str | None = None,
) -> MatchCase:
    """Record the decision on the case and in the audit log. Does not commit."""
    note = (note or "").strip() or None
    match decision:
        case Decision.APPROVE:
            if case.waiting_for:
                raise ReviewNotAllowedError(
                    "Wait for the purchase order and goods receipt before approving: "
                    "nobody has confirmed what was ordered and delivered yet."
                )
            if case.discrepancies and note is None:
                raise NoteRequiredError(
                    "This invoice has problems. Add a note explaining why it is "
                    "approved anyway."
                )
            case.review_status = ReviewStatus.APPROVED
            action = AuditAction.CASE_APPROVED
        case Decision.REJECT:
            if note is None:
                raise NoteRequiredError(
                    "Add a note explaining why the invoice is rejected."
                )
            case.review_status = ReviewStatus.REJECTED
            action = AuditAction.CASE_REJECTED
        case Decision.REOPEN:
            case.review_status = ReviewStatus.PENDING
            action = AuditAction.CASE_REOPENED

    reviewed = decision is not Decision.REOPEN
    case.reviewed_by = reviewer if reviewed else None
    case.reviewed_at = func.now() if reviewed else None
    case.review_note = note if reviewed else None
    record(
        session,
        reviewer,
        action,
        AuditObject.MATCH_CASE,
        case.id,
        {"note": note, "match_status": case.status.value},
    )
    return case
