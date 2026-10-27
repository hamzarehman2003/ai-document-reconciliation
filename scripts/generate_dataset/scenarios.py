"""Build linked document sets (order, receipt, invoice) and inject one mistake.

Everything here is pure logic: no files are read or written, and all randomness
comes from the `rng` argument, so the same seed always gives the same sets.
"""

import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from scripts.generate_dataset.models import (
    Company,
    DocumentSet,
    GoodsReceipt,
    Invoice,
    LineItem,
    PurchaseOrder,
    ReceiptLine,
    Scenario,
    Vendor,
)
from scripts.generate_dataset.vendors import catalog_for

CENT = Decimal("0.01")
FIRST_ORDER_DATE = date(2026, 1, 5)
PAYMENT_TERMS_DAYS = 30
ORDER_QUANTITIES = [2, 4, 5, 6, 8, 10, 12, 15, 20, 24, 25, 30, 40, 50, 60, 100]
PARTIAL_DELIVERY_CHANCE = 0.25

# Roughly how often each scenario appears (relative weights).
SCENARIO_WEIGHTS: dict[Scenario, int] = {
    Scenario.CLEAN: 40,
    Scenario.QTY_EXCEEDS_RECEIVED: 12,
    Scenario.PRICE_MISMATCH: 12,
    Scenario.TOTAL_MISMATCH: 8,
    Scenario.LINE_TOTAL_MISMATCH: 8,
    Scenario.MISSING_PO_REFERENCE: 8,
    Scenario.DUPLICATE_INVOICE: 6,
    Scenario.VENDOR_MISMATCH: 6,
}


def money(value: Decimal) -> Decimal:
    """Round to cents the way accounting software does (half up)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def make_line(
    sku: str, description: str, quantity: int, unit_price: Decimal
) -> LineItem:
    return LineItem(
        sku=sku,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        line_total=money(unit_price * quantity),
    )


def calculate_totals(
    lines: list[LineItem], tax_rate: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (subtotal, tax, total) from the line totals as written."""
    subtotal = sum((line.line_total for line in lines), Decimal("0"))
    tax = money(subtotal * tax_rate)
    return subtotal, tax, subtotal + tax


def generate_sets(
    count: int,
    rng: random.Random,
    buyer: Company,
    vendors: list[Vendor],
    staff: list[str],
) -> list[DocumentSet]:
    """Generate `count` document sets, each with a randomly chosen scenario."""
    sets: list[DocumentSet] = []
    for number in range(1, count + 1):
        scenario = rng.choices(
            list(SCENARIO_WEIGHTS), weights=list(SCENARIO_WEIGHTS.values())
        )[0]
        if scenario is Scenario.DUPLICATE_INVOICE and not sets:
            scenario = Scenario.CLEAN  # nothing to duplicate yet
        sets.append(
            build_document_set(number, scenario, rng, buyer, vendors, staff, sets)
        )
    return sets


def build_document_set(
    number: int,
    scenario: Scenario,
    rng: random.Random,
    buyer: Company,
    vendors: list[Vendor],
    staff: list[str],
    previous_sets: list[DocumentSet],
) -> DocumentSet:
    """Build one order, its goods receipt and its invoice for a given scenario."""
    original: DocumentSet | None = None
    if scenario is Scenario.DUPLICATE_INVOICE:
        if not previous_sets:
            raise ValueError("A duplicate invoice needs an earlier set to copy.")
        original = rng.choice(previous_sets)
        vendor = original.invoice.vendor
    else:
        vendor = rng.choice(vendors)

    order_date = FIRST_ORDER_DATE + timedelta(days=3 * (number - 1) + rng.randint(0, 2))
    order = _build_purchase_order(number, order_date, buyer, vendor, rng)
    receipt = _build_goods_receipt(number, order, staff, rng)

    # A correct invoice bills exactly what was received, at the ordered price.
    lines = [
        make_line(
            line.sku, line.description, received.quantity_received, line.unit_price
        )
        for line, received in zip(order.lines, receipt.lines, strict=True)
    ]
    invoice_vendor = vendor
    po_reference: str | None = order.number
    total_error = Decimal("0")
    index = rng.randrange(len(lines))
    line = lines[index]
    is_partial = any(r.quantity_received < r.quantity_ordered for r in receipt.lines)
    note = (
        "Partial delivery, billed correctly." if is_partial else "Everything matches."
    )

    match scenario:
        case Scenario.QTY_EXCEEDS_RECEIVED:
            extra = rng.randint(2, max(2, line.quantity // 4))
            lines[index] = make_line(
                line.sku, line.description, line.quantity + extra, line.unit_price
            )
            note = (
                f"{line.sku}: billed {line.quantity + extra}, received {line.quantity}."
            )
        case Scenario.PRICE_MISMATCH:
            increase = Decimal(rng.choice(["1.05", "1.08", "1.10", "1.15"]))
            new_price = money(line.unit_price * increase)
            lines[index] = make_line(
                line.sku, line.description, line.quantity, new_price
            )
            note = f"{line.sku}: billed at {new_price}, ordered at {line.unit_price}."
        case Scenario.LINE_TOTAL_MISMATCH:
            error = Decimal(rng.choice(["10.00", "25.00", "50.00", "100.00"]))
            lines[index] = line.model_copy(
                update={"line_total": line.line_total + error}
            )
            note = f"{line.sku}: line total is {error} more than quantity x price."
        case Scenario.TOTAL_MISMATCH:
            total_error = Decimal(rng.choice(["15.00", "40.00", "99.00", "120.00"]))
            note = f"Invoice total is {total_error} more than subtotal + tax."
        case Scenario.MISSING_PO_REFERENCE:
            po_reference = None
            note = "Invoice does not mention the purchase order number."
        case Scenario.DUPLICATE_INVOICE:
            assert original is not None
            note = f"Same invoice number as {original.set_id}."
        case Scenario.VENDOR_MISMATCH:
            invoice_vendor = rng.choice(
                [v for v in vendors if v.vendor_id != vendor.vendor_id]
            )
            note = f"Ordered from {vendor.name}, invoiced by {invoice_vendor.name}."

    if original is not None:
        invoice_number = original.invoice.number
    else:
        used = {s.invoice.number for s in previous_sets}
        invoice_number = _new_invoice_number(invoice_vendor, rng, used)

    subtotal, tax, total = calculate_totals(lines, order.tax_rate)
    issue_date = receipt.receipt_date + timedelta(days=rng.randint(0, 4))
    invoice = Invoice(
        number=invoice_number,
        issue_date=issue_date,
        due_date=issue_date + timedelta(days=PAYMENT_TERMS_DAYS),
        po_number=po_reference,
        buyer=buyer,
        vendor=invoice_vendor,
        currency=order.currency,
        lines=lines,
        subtotal=subtotal,
        tax_rate=order.tax_rate,
        tax=tax,
        total=total + total_error,
    )
    return DocumentSet(
        set_id=f"SET-{number:04d}",
        scenario=scenario,
        expected_codes=[] if scenario is Scenario.CLEAN else [scenario],
        note=note,
        purchase_order=order,
        goods_receipt=receipt,
        invoice=invoice,
    )


def _build_purchase_order(
    number: int,
    order_date: date,
    buyer: Company,
    vendor: Vendor,
    rng: random.Random,
) -> PurchaseOrder:
    items = rng.sample(catalog_for(vendor), k=rng.randint(3, 8))
    lines = [
        make_line(
            item.sku, item.description, rng.choice(ORDER_QUANTITIES), item.unit_price
        )
        for item in items
    ]
    subtotal, tax, total = calculate_totals(lines, vendor.tax_rate)
    return PurchaseOrder(
        number=f"PO-2026-{number:04d}",
        issue_date=order_date,
        buyer=buyer,
        vendor=vendor,
        currency=vendor.currency,
        lines=lines,
        subtotal=subtotal,
        tax_rate=vendor.tax_rate,
        tax=tax,
        total=total,
    )


def _build_goods_receipt(
    number: int,
    order: PurchaseOrder,
    staff: list[str],
    rng: random.Random,
) -> GoodsReceipt:
    short_line = -1
    if rng.random() < PARTIAL_DELIVERY_CHANCE:
        short_line = rng.randrange(len(order.lines))

    lines = []
    for index, line in enumerate(order.lines):
        received = line.quantity
        if index == short_line:
            received -= rng.randint(1, max(1, line.quantity // 3))
        lines.append(
            ReceiptLine(
                sku=line.sku,
                description=line.description,
                quantity_ordered=line.quantity,
                quantity_received=received,
            )
        )
    return GoodsReceipt(
        number=f"GRN-2026-{number:04d}",
        receipt_date=order.issue_date + timedelta(days=rng.randint(3, 10)),
        po_number=order.number,
        buyer=order.buyer,
        vendor=order.vendor,
        received_by=rng.choice(staff),
        lines=lines,
    )


def _new_invoice_number(vendor: Vendor, rng: random.Random, used: set[str]) -> str:
    while True:
        number = f"{vendor.invoice_prefix}-{rng.randint(10000, 99999)}"
        if number not in used:
            return number
