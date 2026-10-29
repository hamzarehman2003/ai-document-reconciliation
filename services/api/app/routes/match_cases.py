"""3-way match cases: one per invoice, with the problems found."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionDep
from app.models import MatchCase, MatchStatus
from app.schemas.match import MatchCaseDetail, MatchCaseOut
from app.services.matching import lock_matching, match_all

router = APIRouter(prefix="/api/match-cases", tags=["match cases"])


@router.get("")
def list_match_cases(
    session: SessionDep,
    status: MatchStatus | None = None,
    invoice_id: int | None = None,
    limit: int = 50,
) -> list[MatchCaseOut]:
    """Recently checked invoices first. Optionally one status or one invoice."""
    query = (
        select(MatchCase)
        # Load related rows in a few queries, not one query per case.
        .options(
            selectinload(MatchCase.invoice),
            selectinload(MatchCase.goods_receipts),
            selectinload(MatchCase.discrepancies),
        )
        .order_by(MatchCase.updated_at.desc())
        .limit(min(limit, 200))
    )
    if status is not None:
        query = query.where(MatchCase.status == status)
    if invoice_id is not None:
        query = query.where(MatchCase.invoice_id == invoice_id)
    return [MatchCaseOut.from_case(case) for case in session.scalars(query)]


@router.get("/{case_id}")
def get_match_case(session: SessionDep, case_id: int) -> MatchCaseDetail:
    case = session.get(MatchCase, case_id)
    if case is None:
        raise HTTPException(404, "Match case not found.")
    return MatchCaseDetail.from_case(case)


@router.post("/refresh")
def refresh_match_cases(session: SessionDep) -> dict[str, int]:
    """Check every processed invoice again (after changing rules or tolerances)."""
    lock_matching(session)  # never at the same time as the worker's matching
    counts = match_all(session)
    session.commit()
    return {status.value: count for status, count in counts.items()}
