"""The plain data the rules work on, and what they return.

No database and no AI here: the rules take simple values and return findings,
so they are easy to test and easy to explain to a client.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


class Code(StrEnum):
    """What can be wrong. The dataset generator injects the same codes."""

    QTY_EXCEEDS_RECEIVED = "QTY_EXCEEDS_RECEIVED"
    PRICE_MISMATCH = "PRICE_MISMATCH"
    ITEM_NOT_ON_PO = "ITEM_NOT_ON_PO"
    LINE_TOTAL_MISMATCH = "LINE_TOTAL_MISMATCH"
    TOTAL_MISMATCH = "TOTAL_MISMATCH"
    MISSING_PO_REFERENCE = "MISSING_PO_REFERENCE"
    VENDOR_MISMATCH = "VENDOR_MISMATCH"
    DUPLICATE_INVOICE = "DUPLICATE_INVOICE"


class Severity(StrEnum):
    ERROR = "error"  # money is at risk: do not pay before checking
    WARNING = "warning"  # needs a look, but may be fine


@dataclass(frozen=True)
class LineData:
    position: int
    sku: str | None
    description: str
    quantity: Decimal | None  # billed (invoice), ordered (PO), received (receipt)
    unit_price: Decimal | None = None
    line_total: Decimal | None = None


@dataclass(frozen=True)
class DocumentData:
    document_id: int | None
    number: str | None
    vendor_name: str | None
    po_reference: str | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    total: Decimal | None = None
    lines: list[LineData] = field(default_factory=list)


@dataclass(frozen=True)
class Reference:
    """A value on a document that a finding is about (for highlighting)."""

    document_id: int | None
    field: str  # e.g. "total" or "line_items.3.quantity"


@dataclass(frozen=True)
class Finding:
    code: Code
    severity: Severity
    message: str
    details: dict[str, str] = field(default_factory=dict)
    references: list[Reference] = field(default_factory=list)


@dataclass(frozen=True)
class Tolerances:
    """How much difference is still accepted."""

    price_percent: Decimal = Decimal("0")
    quantity_percent: Decimal = Decimal("0")
    amount: Decimal = Decimal("0.01")  # rounding differences in totals
