"""One plain sentence that says where an invoice stands.

Built from the match result and the decision with fixed wording, not by an AI:
the rules already decided, so the sentence only has to say it, and can't make
up a number or a name. No database access: it reads the case that is passed in.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.models import MatchCase, MatchStatus, ReviewStatus
from app.rules.types import Severity

MISSING_LABELS = {"purchase_order": "purchase order", "goods_receipt": "goods receipt"}


class Verdict(StrEnum):
    CLEAR = "clear"  # everything matches, ready to approve
    NEEDS_REVIEW = "needs_review"  # problems found
    WAITING = "waiting"  # documents missing, nothing wrong so far
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Summary:
    verdict: Verdict
    text: str


def summarize(case: MatchCase) -> Summary:
    """The verdict and one sentence for the invoice page and the review queue."""
    if case.review_status is ReviewStatus.APPROVED:
        text = f"Approved for payment by {case.reviewed_by}{_on(case.reviewed_at)}"
        problems = len(case.discrepancies)
        if problems:
            text += f", despite {_count(problems, 'problem')}"
        return Summary(Verdict.APPROVED, text + ".")

    if case.review_status is ReviewStatus.REJECTED:
        text = f"Rejected by {case.reviewed_by}{_on(case.reviewed_at)}"
        # The note is quoted as written, so no full stop is added after it.
        text += f": “{case.review_note}”" if case.review_note else "."
        return Summary(Verdict.REJECTED, text)

    missing = _missing(case)
    if case.status is MatchStatus.NEEDS_REVIEW:
        # The most serious problem first; the rest are listed below the banner.
        problems = sorted(
            case.discrepancies, key=lambda d: d.severity != Severity.ERROR
        )
        text = f"Needs review: {_count(len(problems), 'problem')}."
        if problems:
            text += f" {problems[0].message}"
        if len(problems) > 1:
            text += f" Plus {len(problems) - 1} more."
        if missing:
            text += f" The {missing} {_is(missing)} also still missing."
        return Summary(Verdict.NEEDS_REVIEW, text)

    if case.status is MatchStatus.WAITING or missing:
        return Summary(
            Verdict.WAITING,
            f"Waiting: the {missing} for {case.invoice.po_reference} "
            f"{_has(missing)} not been uploaded yet. The invoice is checked again "
            "when it arrives.",
        )

    receipts = "goods receipt" if len(case.goods_receipts) == 1 else "goods receipts"
    return Summary(
        Verdict.CLEAR,
        "All clear: quantities, prices and totals match "
        f"{case.invoice.po_reference} and its {receipts}. Ready to approve.",
    )


def _missing(case: MatchCase) -> str:
    """'purchase order', 'goods receipt', or both joined with 'and' ('' if none)."""
    return " and ".join(MISSING_LABELS[item] for item in case.waiting_for)


def _is(missing: str) -> str:
    return "are" if " and " in missing else "is"


def _has(missing: str) -> str:
    return "have" if " and " in missing else "has"


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}{'' if number == 1 else 's'}"


def _on(moment: datetime | None) -> str:
    """' on 29 Oct 2026' (no leading zero on any system)."""
    return "" if moment is None else f" on {moment.day} {moment:%b %Y}"
