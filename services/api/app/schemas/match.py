"""Response shapes for 3-way match cases."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import MatchCase, MatchStatus, ReviewStatus
from app.rules.types import Code, Severity
from app.schemas.document import DocumentOut
from app.services.review import Decision
from app.services.summary import Verdict, summarize


class DecisionRequest(BaseModel):
    decision: Decision
    note: str | None = Field(default=None, max_length=1000)


class DiscrepancyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: Code
    severity: Severity
    message: str
    details: dict[str, Any]
    refs: list[dict[str, Any]]  # [{"document_id": 161, "field": "total"}, ...]


class MatchCaseOut(BaseModel):
    """A case with its problems (shown on the invoice)."""

    id: int
    status: MatchStatus
    invoice_id: int
    invoice_number: str | None
    vendor_name: str | None
    invoice_date: date | None
    currency: str | None
    total: Decimal | None
    po_number: str | None
    purchase_order_id: int | None
    goods_receipt_ids: list[int]
    # Documents still missing for a full check, even when problems were found.
    waiting_for: list[str]
    review_status: ReviewStatus
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_note: str | None
    updated_at: datetime
    discrepancies: list[DiscrepancyOut]
    # Where the invoice stands, in one sentence (fixed wording: services/summary.py).
    verdict: Verdict
    summary: str

    @classmethod
    def from_case(cls, case: MatchCase) -> "MatchCaseOut":
        summary = summarize(case)
        return cls(
            id=case.id,
            status=case.status,
            invoice_id=case.invoice_id,
            invoice_number=case.invoice.document_number,
            vendor_name=case.invoice.vendor_name,
            invoice_date=case.invoice.issue_date,
            currency=case.invoice.currency,
            total=case.invoice.total,
            po_number=case.invoice.po_reference,
            purchase_order_id=case.purchase_order_id,
            goods_receipt_ids=[receipt.id for receipt in case.goods_receipts],
            waiting_for=case.waiting_for,
            review_status=case.review_status,
            reviewed_by=case.reviewed_by,
            reviewed_at=case.reviewed_at,
            review_note=case.review_note,
            updated_at=case.updated_at,
            discrepancies=[
                DiscrepancyOut.model_validate(d) for d in case.discrepancies
            ],
            verdict=summary.verdict,
            summary=summary.text,
        )


class MatchCaseDetail(MatchCaseOut):
    """A case with its documents, for the match screen."""

    invoice: DocumentOut
    purchase_order: DocumentOut | None
    goods_receipts: list[DocumentOut]

    @classmethod
    def from_case(cls, case: MatchCase) -> "MatchCaseDetail":
        return cls(
            **MatchCaseOut.from_case(case).model_dump(),
            invoice=DocumentOut.model_validate(case.invoice),
            purchase_order=(
                DocumentOut.model_validate(case.purchase_order)
                if case.purchase_order
                else None
            ),
            goods_receipts=[DocumentOut.model_validate(r) for r in case.goods_receipts],
        )
