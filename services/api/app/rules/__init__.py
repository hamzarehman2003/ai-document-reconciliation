"""3-way matching rules: invoice ↔ purchase order ↔ goods receipt.

Plain Python, no database and no AI: simple data in, findings out.
"""

from app.rules.checks import (
    check_duplicate,
    check_line_totals,
    check_missing_po_reference,
    check_prices,
    check_quantities,
    check_totals,
    check_vendor,
)
from app.rules.types import (
    Code,
    DocumentData,
    Finding,
    LineData,
    Reference,
    Severity,
    Tolerances,
)

__all__ = [
    "Code",
    "DocumentData",
    "Finding",
    "LineData",
    "Reference",
    "Severity",
    "Tolerances",
    "check_invoice",
]


def check_invoice(
    invoice: DocumentData,
    purchase_order: DocumentData | None,
    receipts: list[DocumentData],
    earlier_invoices: list[DocumentData],
    tolerances: Tolerances | None = None,
) -> list[Finding]:
    """Run every rule that the available documents allow.

    Quantities are only checked once at least one goods receipt is in.
    """
    tolerances = tolerances or Tolerances()
    findings = [
        *check_missing_po_reference(invoice),
        *check_duplicate(invoice, earlier_invoices),
        *check_line_totals(invoice, tolerances),
        *check_totals(invoice, tolerances),
    ]
    if purchase_order is not None:
        findings += check_vendor(invoice, purchase_order)
        findings += check_prices(invoice, purchase_order, tolerances)
    if receipts:
        findings += check_quantities(invoice, receipts, tolerances)
    return findings
