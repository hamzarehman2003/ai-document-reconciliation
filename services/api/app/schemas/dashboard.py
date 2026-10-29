"""Response shape for the dashboard numbers."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models import DocumentType, MatchStatus, ReviewStatus


class DocumentStats(BaseModel):
    total: int
    processed: int
    failed: int
    in_progress: int  # uploaded or being processed
    by_type: dict[DocumentType, int]  # processed documents only


class InvoiceStats(BaseModel):
    total: int  # invoices with a 3-way match case
    by_match_status: dict[MatchStatus, int]
    by_review_status: dict[ReviewStatus, int]
    # Matched ÷ (matched + needs review): the share that needed no human.
    match_rate: float | None


class AmountByCurrency(BaseModel):
    currency: str
    amount: Decimal
    invoices: int


class ProblemCount(BaseModel):
    code: str
    count: int


class AiStats(BaseModel):
    documents_read: int
    average_seconds: float | None
    input_tokens: int
    output_tokens: int


class DayActivity(BaseModel):
    day: date
    uploaded: int
    approved: int


class Dashboard(BaseModel):
    documents: DocumentStats
    invoices: InvoiceStats
    # Invoices with problems nobody has decided on yet. Currencies are never mixed.
    money_at_risk: list[AmountByCurrency]
    approved_amount: list[AmountByCurrency]
    top_problems: list[ProblemCount]
    ai: AiStats
    corrections: int
    daily: list[DayActivity]  # the last 14 days, oldest first, zeros included
