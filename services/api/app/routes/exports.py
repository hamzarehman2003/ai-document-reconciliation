"""Download approved invoices for the accounting system."""

from datetime import date

from fastapi import APIRouter, Response
from sqlalchemy.orm import Session

from app.db import SessionDep
from app.models import MatchCase
from app.services.audit import DEFAULT_REVIEWER
from app.services.export import find_approved, record_export, to_csv, to_xlsx

router = APIRouter(prefix="/api/exports", tags=["exports"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/approved.xlsx",
    response_class=Response,
    responses={200: {"content": {XLSX: {}}}},
)
def export_excel(
    session: SessionDep,
    date_from: date | None = None,
    date_to: date | None = None,
    vendor: str | None = None,
    reviewer: str = DEFAULT_REVIEWER,
) -> Response:
    """Approved invoices as Excel: an Invoices sheet and a Line items sheet."""
    cases = find_approved(session, date_from, date_to, vendor)
    return _download(session, cases, reviewer, to_xlsx(cases), "xlsx", XLSX)


@router.get(
    "/approved.csv",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
def export_csv(
    session: SessionDep,
    date_from: date | None = None,
    date_to: date | None = None,
    vendor: str | None = None,
    reviewer: str = DEFAULT_REVIEWER,
) -> Response:
    """Approved invoices as CSV (one row per invoice)."""
    cases = find_approved(session, date_from, date_to, vendor)
    return _download(session, cases, reviewer, to_csv(cases), "csv", "text/csv")


def _download(
    session: Session,
    cases: list[MatchCase],
    reviewer: str,
    content: bytes,
    extension: str,
    media_type: str,
) -> Response:
    record_export(session, cases, reviewer, extension)
    session.commit()
    filename = f"approved-invoices-{date.today().isoformat()}.{extension}"
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
