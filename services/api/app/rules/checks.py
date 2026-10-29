"""One small function per rule. Each returns a list of findings (empty = fine)."""

import re
from decimal import ROUND_HALF_UP, Decimal

from app.rules.types import (
    Code,
    DocumentData,
    Finding,
    LineData,
    Reference,
    Severity,
    Tolerances,
)

COMPANY_SUFFIXES = {
    "ltd",
    "limited",
    "inc",
    "co",
    "llc",
    "gmbh",
    "plc",
    "corp",
    "company",
}
CENT = Decimal("0.01")


def check_missing_po_reference(invoice: DocumentData) -> list[Finding]:
    if invoice.po_reference:
        return []
    return [
        Finding(
            Code.MISSING_PO_REFERENCE,
            Severity.WARNING,
            "The invoice does not mention a purchase order number.",
        )
    ]


def check_vendor(invoice: DocumentData, order: DocumentData) -> list[Finding]:
    if not invoice.vendor_name or not order.vendor_name:
        return []
    if company_key(invoice.vendor_name) == company_key(order.vendor_name):
        return []
    return [
        Finding(
            Code.VENDOR_MISMATCH,
            Severity.ERROR,
            f"The invoice is from {invoice.vendor_name}, but purchase order "
            f"{order.number} was placed with {order.vendor_name}.",
            {"invoice_vendor": invoice.vendor_name, "po_vendor": order.vendor_name},
            [
                Reference(invoice.document_id, "vendor_name"),
                Reference(order.document_id, "vendor_name"),
            ],
        )
    ]


def check_duplicate(
    invoice: DocumentData, earlier: list[DocumentData]
) -> list[Finding]:
    if not invoice.number:
        return []
    for other in earlier:
        same_number = (
            other.number or ""
        ).strip().casefold() == invoice.number.strip().casefold()
        same_vendor = company_key(other.vendor_name or "") == company_key(
            invoice.vendor_name or ""
        )
        if same_number and same_vendor and other.document_id != invoice.document_id:
            return [
                Finding(
                    Code.DUPLICATE_INVOICE,
                    Severity.ERROR,
                    f"Invoice {invoice.number} from {invoice.vendor_name} was already "
                    f"received before (document {other.document_id}).",
                    {"earlier_document_id": str(other.document_id)},
                    [
                        Reference(invoice.document_id, "document_number"),
                        Reference(other.document_id, "document_number"),
                    ],
                )
            ]
    return []


def check_line_totals(invoice: DocumentData, tolerances: Tolerances) -> list[Finding]:
    findings = []
    for line in invoice.lines:
        if line.quantity is None or line.unit_price is None or line.line_total is None:
            continue
        expected = money(line.quantity * line.unit_price)
        if abs(expected - line.line_total) > tolerances.amount:
            findings.append(
                Finding(
                    Code.LINE_TOTAL_MISMATCH,
                    Severity.ERROR,
                    f"{label(line)}: {qty(line.quantity)} × {line.unit_price:,.2f} = "
                    f"{expected:,.2f}, but the line total says {line.line_total:,.2f}.",
                    {"expected": str(expected), "printed": str(line.line_total)},
                    [
                        Reference(
                            invoice.document_id,
                            f"line_items.{line.position}.line_total",
                        )
                    ],
                )
            )
    return findings


def check_totals(invoice: DocumentData, tolerances: Tolerances) -> list[Finding]:
    findings = []
    line_totals = [
        line.line_total for line in invoice.lines if line.line_total is not None
    ]
    if invoice.subtotal is not None and line_totals:
        lines_sum = sum(line_totals, Decimal("0"))
        if abs(lines_sum - invoice.subtotal) > tolerances.amount:
            findings.append(
                Finding(
                    Code.TOTAL_MISMATCH,
                    Severity.ERROR,
                    f"The line totals add up to {lines_sum:,.2f}, but the subtotal "
                    f"says {invoice.subtotal:,.2f}.",
                    {"expected": str(lines_sum), "printed": str(invoice.subtotal)},
                    [Reference(invoice.document_id, "subtotal")],
                )
            )
    if None not in (invoice.subtotal, invoice.tax, invoice.total):
        expected = invoice.subtotal + invoice.tax
        if abs(expected - invoice.total) > tolerances.amount:
            findings.append(
                Finding(
                    Code.TOTAL_MISMATCH,
                    Severity.ERROR,
                    f"Subtotal {invoice.subtotal:,.2f} + tax {invoice.tax:,.2f} = "
                    f"{expected:,.2f}, but the total says {invoice.total:,.2f}.",
                    {"expected": str(expected), "printed": str(invoice.total)},
                    [Reference(invoice.document_id, "total")],
                )
            )
    return findings


def check_prices(
    invoice: DocumentData, order: DocumentData, tolerances: Tolerances
) -> list[Finding]:
    """Every invoiced item must be on the PO, at the PO price."""
    ordered = {line_key(line): line for line in order.lines}
    findings = []
    for line in invoice.lines:
        po_line = ordered.get(line_key(line))
        if po_line is None:
            findings.append(
                Finding(
                    Code.ITEM_NOT_ON_PO,
                    Severity.ERROR,
                    f"{label(line)} is billed but is not on purchase order "
                    f"{order.number}.",
                    {"sku": line.sku or ""},
                    [Reference(invoice.document_id, f"line_items.{line.position}.sku")],
                )
            )
            continue
        if line.unit_price is None or po_line.unit_price is None:
            continue
        allowed = po_line.unit_price * tolerances.price_percent / 100
        if abs(line.unit_price - po_line.unit_price) > allowed:
            findings.append(
                Finding(
                    Code.PRICE_MISMATCH,
                    Severity.ERROR,
                    f"{label(line)}: billed at {line.unit_price:,.2f}, but the "
                    f"purchase order price is {po_line.unit_price:,.2f}.",
                    {
                        "sku": line.sku or "",
                        "billed": str(line.unit_price),
                        "ordered": str(po_line.unit_price),
                    },
                    [
                        Reference(
                            invoice.document_id,
                            f"line_items.{line.position}.unit_price",
                        ),
                        Reference(
                            order.document_id,
                            f"line_items.{po_line.position}.unit_price",
                        ),
                    ],
                )
            )
    return findings


def check_quantities(
    invoice: DocumentData, receipts: list[DocumentData], tolerances: Tolerances
) -> list[Finding]:
    """Nothing may be billed beyond what actually arrived.

    A delivery can be split over several goods receipts, so the received
    quantities of all receipts for the order are added up.
    """
    received: dict[str, Decimal] = {}
    received_on: dict[str, list[Reference]] = {}
    for receipt in receipts:
        for receipt_line in receipt.lines:
            key = line_key(receipt_line)
            received[key] = received.get(key, Decimal("0")) + (
                receipt_line.quantity or Decimal("0")
            )
            received_on.setdefault(key, []).append(
                Reference(
                    receipt.document_id,
                    f"line_items.{receipt_line.position}.quantity",
                )
            )

    findings = []
    for line in invoice.lines:
        if line.quantity is None:
            continue
        key = line_key(line)
        received_qty = received.get(key, Decimal("0"))  # not received = 0
        allowed = received_qty * (1 + tolerances.quantity_percent / 100)
        if line.quantity <= allowed:
            continue
        references = [
            Reference(invoice.document_id, f"line_items.{line.position}.quantity"),
            *received_on.get(key, []),
        ]
        if key not in received:
            message = (
                f"{label(line)}: billed {qty(line.quantity)}, but it is not on any "
                "goods receipt."
            )
        else:
            message = (
                f"{label(line)}: billed {qty(line.quantity)}, but only "
                f"{qty(received_qty)} received."
            )
        findings.append(
            Finding(
                Code.QTY_EXCEEDS_RECEIVED,
                Severity.ERROR,
                message,
                {
                    "sku": line.sku or "",
                    "billed": qty(line.quantity),
                    "received": qty(received_qty),
                },
                references,
            )
        )
    return findings


# --- Helpers ---


def company_key(name: str) -> str:
    """'Northfield Packaging Co.' and 'NORTHFIELD PACKAGING' compare equal."""
    words = re.sub(r"[^\w\s&]", " ", name.casefold()).split()
    return " ".join(word for word in words if word not in COMPANY_SUFFIXES)


def line_key(line: LineData) -> str:
    """Lines on different documents are matched by SKU (or description if none)."""
    return (line.sku or line.description).strip().casefold()


def label(line: LineData) -> str:
    return line.sku or line.description


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def qty(value: Decimal) -> str:
    """Decimal('10.000') → '10', Decimal('2.500') → '2.5'"""
    return format(value.normalize(), "f")
