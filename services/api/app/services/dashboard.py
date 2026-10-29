"""The numbers for the dashboard. Counted and summed by the database, not in Python."""

from datetime import date, timedelta
from enum import StrEnum

from sqlalchemy import ColumnElement, Date, cast, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.models import (
    AuditAction,
    AuditEvent,
    Discrepancy,
    Document,
    DocumentStatus,
    DocumentType,
    Extraction,
    FieldCorrection,
    MatchCase,
    MatchStatus,
    ReviewStatus,
)
from app.schemas.dashboard import (
    AiStats,
    AmountByCurrency,
    Dashboard,
    DayActivity,
    DocumentStats,
    InvoiceStats,
    ProblemCount,
)

DAYS_OF_ACTIVITY = 14
UNKNOWN_CURRENCY = "UNKNOWN"


def build_dashboard(session: Session) -> Dashboard:
    return Dashboard(
        documents=document_stats(session),
        invoices=invoice_stats(session),
        money_at_risk=amounts(
            session,
            MatchCase.status == MatchStatus.NEEDS_REVIEW,
            MatchCase.review_status == ReviewStatus.PENDING,
        ),
        approved_amount=amounts(
            session, MatchCase.review_status == ReviewStatus.APPROVED
        ),
        top_problems=[
            ProblemCount(code=code.value, count=count)
            for code, count in session.execute(
                select(Discrepancy.code, func.count())
                .group_by(Discrepancy.code)
                .order_by(func.count().desc(), Discrepancy.code)
            )
        ],
        ai=ai_stats(session),
        corrections=session.scalar(select(func.count(FieldCorrection.id))) or 0,
        daily=daily_activity(session),
    )


def document_stats(session: Session) -> DocumentStats:
    by_status = count_by(session, Document.status, DocumentStatus)
    by_type = count_by(
        session,
        Document.doc_type,
        DocumentType,
        Document.status == DocumentStatus.PROCESSED,
    )
    return DocumentStats(
        total=sum(by_status.values()),
        processed=by_status[DocumentStatus.PROCESSED],
        failed=by_status[DocumentStatus.FAILED],
        in_progress=by_status[DocumentStatus.UPLOADED]
        + by_status[DocumentStatus.PROCESSING],
        by_type=by_type,
    )


def invoice_stats(session: Session) -> InvoiceStats:
    by_match = count_by(session, MatchCase.status, MatchStatus)
    by_review = count_by(session, MatchCase.review_status, ReviewStatus)
    checked = by_match[MatchStatus.MATCHED] + by_match[MatchStatus.NEEDS_REVIEW]
    return InvoiceStats(
        total=sum(by_match.values()),
        by_match_status=by_match,
        by_review_status=by_review,
        match_rate=round(by_match[MatchStatus.MATCHED] / checked, 3)
        if checked
        else None,
    )


def amounts(
    session: Session, *conditions: ColumnElement[bool]
) -> list[AmountByCurrency]:
    """Invoice totals of the cases matching the conditions, per currency."""
    rows = session.execute(
        select(Document.currency, func.sum(Document.total), func.count())
        .join(MatchCase, MatchCase.invoice_id == Document.id)
        .where(*conditions)
        .group_by(Document.currency)
        .order_by(Document.currency)
    )
    return [
        AmountByCurrency(
            currency=currency or UNKNOWN_CURRENCY, amount=total or 0, invoices=count
        )
        for currency, total, count in rows
    ]


def ai_stats(session: Session) -> AiStats:
    count, average_ms, input_tokens, output_tokens = session.execute(
        select(
            func.count(Extraction.id),
            func.avg(Extraction.duration_ms),
            func.sum(Extraction.input_tokens),
            func.sum(Extraction.output_tokens),
        )
    ).one()
    return AiStats(
        documents_read=count,
        average_seconds=round(float(average_ms) / 1000, 1) if average_ms else None,
        input_tokens=input_tokens or 0,
        output_tokens=output_tokens or 0,
    )


def daily_activity(session: Session) -> list[DayActivity]:
    """Uploads and approvals per day, using the database's own "today"."""
    today: date = session.scalar(select(func.current_date()))
    first_day = today - timedelta(days=DAYS_OF_ACTIVITY - 1)

    uploaded = per_day(session, Document.created_at, first_day)
    approved = per_day(
        session,
        AuditEvent.created_at,
        first_day,
        AuditEvent.action == AuditAction.CASE_APPROVED,
    )
    days = [first_day + timedelta(days=offset) for offset in range(DAYS_OF_ACTIVITY)]
    return [
        DayActivity(
            day=day, uploaded=uploaded.get(day, 0), approved=approved.get(day, 0)
        )
        for day in days
    ]


def per_day(
    session: Session,
    timestamp: InstrumentedAttribute,
    first_day: date,
    *conditions: ColumnElement[bool],
) -> dict[date, int]:
    day = cast(timestamp, Date)
    rows = session.execute(
        select(day, func.count()).where(day >= first_day, *conditions).group_by(day)
    )
    return {day_value: count for day_value, count in rows}


def count_by(
    session: Session,
    column: InstrumentedAttribute,
    values: type[StrEnum],
    *conditions: ColumnElement[bool],
) -> dict:
    """How many rows have each value, with 0 for values that don't occur."""
    counts = dict.fromkeys(values, 0)
    rows = session.execute(
        select(column, func.count()).where(*conditions).group_by(column)
    )
    for value, count in rows:
        counts[value] = count
    return counts
