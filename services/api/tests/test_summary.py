"""The one-line summary of where an invoice stands (no database needed)."""

from datetime import UTC, datetime

from app.models import Discrepancy, Document, MatchCase, MatchStatus, ReviewStatus
from app.rules.types import Code, Severity
from app.services.summary import Verdict, summarize

REVIEWED_AT = datetime(2026, 10, 29, 8, 17, tzinfo=UTC)
OVERBILLED = Discrepancy(
    code=Code.QTY_EXCEEDS_RECEIVED,
    severity=Severity.ERROR,
    message="CPF-15: billed 10, but only 8 received.",
)
TOTAL_OFF = Discrepancy(
    code=Code.TOTAL_MISMATCH,
    severity=Severity.WARNING,
    message="Subtotal 100.00 + tax 20.00 = 120.00, but the total says 121.00.",
)


def make_case(
    status: MatchStatus,
    *,
    po_reference: str | None = "PO-2026-0007",
    has_order: bool = True,
    receipts: int = 1,
    problems: tuple[Discrepancy, ...] = (),
    review: ReviewStatus = ReviewStatus.PENDING,
    note: str | None = None,
) -> MatchCase:
    """A case in memory, never saved."""
    reviewed = review is not ReviewStatus.PENDING
    return MatchCase(
        status=status,
        review_status=review,
        invoice=Document(po_reference=po_reference),
        purchase_order_id=1 if has_order else None,
        goods_receipts=[Document() for _ in range(receipts)],
        discrepancies=list(problems),
        reviewed_by="Sara (AP team)" if reviewed else None,
        reviewed_at=REVIEWED_AT if reviewed else None,
        review_note=note,
    )


def test_all_clear() -> None:
    summary = summarize(make_case(MatchStatus.MATCHED))

    assert summary.verdict is Verdict.CLEAR
    assert summary.text == (
        "All clear: quantities, prices and totals match PO-2026-0007 and its "
        "goods receipt. Ready to approve."
    )


def test_all_clear_with_a_delivery_in_parts() -> None:
    summary = summarize(make_case(MatchStatus.MATCHED, receipts=2))

    assert "and its goods receipts." in summary.text


def test_waiting_for_the_goods_receipt() -> None:
    summary = summarize(make_case(MatchStatus.WAITING, receipts=0))

    assert summary.verdict is Verdict.WAITING
    assert summary.text.startswith(
        "Waiting: the goods receipt for PO-2026-0007 has not been uploaded yet."
    )


def test_waiting_for_both_documents() -> None:
    summary = summarize(make_case(MatchStatus.WAITING, has_order=False, receipts=0))

    assert summary.text.startswith(
        "Waiting: the purchase order and goods receipt for PO-2026-0007 have not"
    )


def test_problems_put_the_most_serious_first() -> None:
    case = make_case(MatchStatus.NEEDS_REVIEW, problems=(TOTAL_OFF, OVERBILLED))

    summary = summarize(case)

    assert summary.verdict is Verdict.NEEDS_REVIEW
    assert summary.text == (
        "Needs review: 2 problems. CPF-15: billed 10, but only 8 received. Plus 1 more."
    )


def test_problems_and_a_missing_document() -> None:
    case = make_case(MatchStatus.NEEDS_REVIEW, receipts=0, problems=(OVERBILLED,))

    summary = summarize(case)

    assert summary.text == (
        "Needs review: 1 problem. CPF-15: billed 10, but only 8 received. "
        "The goods receipt is also still missing."
    )


def test_approved_despite_a_problem() -> None:
    case = make_case(
        MatchStatus.NEEDS_REVIEW,
        problems=(OVERBILLED,),
        review=ReviewStatus.APPROVED,
        note="Rest arrives Monday",
    )

    summary = summarize(case)

    assert summary.verdict is Verdict.APPROVED
    assert summary.text == (
        "Approved for payment by Sara (AP team) on 29 Oct 2026, despite 1 problem."
    )


def test_rejected_quotes_the_note() -> None:
    case = make_case(
        MatchStatus.NEEDS_REVIEW,
        problems=(OVERBILLED,),
        review=ReviewStatus.REJECTED,
        note="Asked for a credit note.",
    )

    summary = summarize(case)

    assert summary.verdict is Verdict.REJECTED
    assert summary.text == (
        "Rejected by Sara (AP team) on 29 Oct 2026: “Asked for a credit note.”"
    )
