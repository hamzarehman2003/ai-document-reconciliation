"""The matching rules, checked against the dataset generator's answer keys.

No database and no AI: generated documents are turned straight into rules input.
"""

import random
from decimal import Decimal

import pytest
from faker import Faker

from app.rules import (
    Code,
    DocumentData,
    LineData,
    Tolerances,
    check_invoice,
)
from app.rules.checks import company_key
from scripts.generate_dataset import models as generated
from scripts.generate_dataset.scenarios import generate_sets
from scripts.generate_dataset.vendors import (
    build_buyer,
    build_receiving_staff,
    build_vendors,
)


def as_invoice(index: int, invoice: generated.Invoice) -> DocumentData:
    return DocumentData(
        document_id=index,
        number=invoice.number,
        vendor_name=invoice.vendor.name,
        po_reference=invoice.po_number,
        subtotal=invoice.subtotal,
        tax=invoice.tax,
        total=invoice.total,
        lines=[as_line(i, line) for i, line in enumerate(invoice.lines, start=1)],
    )


def as_order(order: generated.PurchaseOrder) -> DocumentData:
    return DocumentData(
        document_id=None,
        number=order.number,
        vendor_name=order.vendor.name,
        lines=[as_line(i, line) for i, line in enumerate(order.lines, start=1)],
    )


def as_receipt(receipt: generated.GoodsReceipt) -> DocumentData:
    return DocumentData(
        document_id=None,
        number=receipt.number,
        vendor_name=receipt.vendor.name,
        po_reference=receipt.po_number,
        lines=[
            LineData(i, line.sku, line.description, Decimal(line.quantity_received))
            for i, line in enumerate(receipt.lines, start=1)
        ],
    )


def as_line(position: int, line: generated.LineItem) -> LineData:
    return LineData(
        position,
        line.sku,
        line.description,
        Decimal(line.quantity),
        line.unit_price,
        line.line_total,
    )


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_rules_find_exactly_the_injected_mistakes(seed: int) -> None:
    fake = Faker("en_GB")
    fake.seed_instance(seed)
    sets = generate_sets(
        100,
        random.Random(seed),
        build_buyer(fake),
        build_vendors(fake),
        build_receiving_staff(fake),
    )
    invoices = [as_invoice(index, s.invoice) for index, s in enumerate(sets)]

    for index, document_set in enumerate(sets):
        findings = check_invoice(
            invoices[index],
            as_order(document_set.purchase_order),
            [as_receipt(document_set.goods_receipt)],
            earlier_invoices=invoices[:index],
        )
        found = sorted({finding.code.value for finding in findings})
        expected = sorted(code.value for code in document_set.expected_codes)
        assert found == expected, f"{document_set.set_id}: {document_set.note}"


# --- Single rules ---


def invoice_with(*lines: LineData, **fields: object) -> DocumentData:
    values: dict = {
        "document_id": 10,
        "number": "INV-1",
        "vendor_name": "Apex Office Supplies",
        "po_reference": "PO-1",
    }
    values.update(fields)
    return DocumentData(lines=list(lines), **values)


VENDOR_NAME = "Apex Office Supplies"

ORDER = DocumentData(
    document_id=1,
    number="PO-1",
    vendor_name="Apex Office Supplies Ltd.",
    lines=[
        LineData(1, "A-1", "Paper", Decimal("10"), Decimal("5.00"), Decimal("50.00"))
    ],
)
RECEIPT = DocumentData(
    document_id=2,
    number="GRN-1",
    vendor_name="Apex Office Supplies",
    lines=[LineData(1, "A-1", "Paper", Decimal("8"))],
)


def codes(findings: list) -> list[str]:
    return [finding.code.value for finding in findings]


def test_partial_delivery_billed_correctly_is_fine() -> None:
    line = LineData(1, "A-1", "Paper", Decimal("8"), Decimal("5.00"), Decimal("40.00"))
    invoice = invoice_with(
        line, subtotal=Decimal("40.00"), tax=Decimal("0"), total=Decimal("40.00")
    )

    assert check_invoice(invoice, ORDER, [RECEIPT], []) == []


def test_billing_more_than_received() -> None:
    line = LineData(1, "A-1", "Paper", Decimal("10"), Decimal("5.00"), Decimal("50.00"))

    [finding] = check_invoice(invoice_with(line), ORDER, [RECEIPT], [])

    assert finding.code is Code.QTY_EXCEEDS_RECEIVED
    assert finding.message == "A-1: billed 10, but only 8 received."
    assert finding.details == {"sku": "A-1", "billed": "10", "received": "8"}


def test_quantity_tolerance_allows_small_overbilling() -> None:
    line = LineData(
        1, "A-1", "Paper", Decimal("8.4"), Decimal("5.00"), Decimal("42.00")
    )
    tolerances = Tolerances(quantity_percent=Decimal("5"))  # 8 × 1.05 = 8.4

    assert check_invoice(invoice_with(line), ORDER, [RECEIPT], [], tolerances) == []


def test_price_above_the_po_price() -> None:
    line = LineData(1, "A-1", "Paper", Decimal("8"), Decimal("5.50"), Decimal("44.00"))

    [finding] = check_invoice(invoice_with(line), ORDER, [RECEIPT], [])

    assert finding.code is Code.PRICE_MISMATCH
    assert "billed at 5.50, but the purchase order price is 5.00" in finding.message


def test_item_not_on_the_po() -> None:
    line = LineData(1, "Z-9", "Stapler", Decimal("1"), Decimal("9.00"), Decimal("9.00"))

    assert codes(check_invoice(invoice_with(line), ORDER, [], [])) == ["ITEM_NOT_ON_PO"]


def test_wrong_line_total_and_wrong_total() -> None:
    line = LineData(1, "A-1", "Paper", Decimal("8"), Decimal("5.00"), Decimal("45.00"))
    invoice = invoice_with(
        line, subtotal=Decimal("45.00"), tax=Decimal("9.00"), total=Decimal("60.00")
    )

    assert codes(check_invoice(invoice, None, [], [])) == [
        "LINE_TOTAL_MISMATCH",  # 8 × 5.00 is 40.00, not 45.00
        "TOTAL_MISMATCH",  # 45.00 + 9.00 is 54.00, not 60.00
    ]


def test_one_cent_rounding_is_accepted() -> None:
    line = LineData(1, "A-1", "Paper", Decimal("3"), Decimal("3.333"), Decimal("10.00"))

    assert check_invoice(invoice_with(line), None, [], []) == []


def test_missing_po_reference_is_a_warning() -> None:
    [finding] = check_invoice(invoice_with(po_reference=None), None, [], [])

    assert finding.code is Code.MISSING_PO_REFERENCE
    assert finding.severity.value == "warning"


def test_vendor_names_compare_without_suffixes() -> None:
    assert company_key("Apex Office Supplies Ltd.") == company_key(
        "APEX OFFICE SUPPLIES"
    )
    other = invoice_with(vendor_name="Bluewater Electronics")

    assert codes(check_invoice(other, ORDER, [], [])) == ["VENDOR_MISMATCH"]


def test_duplicate_invoice_number_from_the_same_vendor() -> None:
    earlier = invoice_with(document_id=3)
    same_number_other_vendor = invoice_with(document_id=4, vendor_name="Bluewater")

    assert codes(check_invoice(invoice_with(), None, [], [earlier])) == [
        "DUPLICATE_INVOICE"
    ]
    assert check_invoice(invoice_with(), None, [], [same_number_other_vendor]) == []


def test_delivery_split_over_two_receipts_is_added_up() -> None:
    first = DocumentData(
        3, "GRN-1", VENDOR_NAME, lines=[LineData(1, "A-1", "Paper", Decimal("6"))]
    )
    second = DocumentData(
        4, "GRN-2", VENDOR_NAME, lines=[LineData(1, "A-1", "Paper", Decimal("4"))]
    )
    line = LineData(1, "A-1", "Paper", Decimal("10"), Decimal("5.00"), Decimal("50.00"))
    invoice = invoice_with(
        line, subtotal=Decimal("50.00"), tax=Decimal("0"), total=Decimal("50.00")
    )

    assert check_invoice(invoice, ORDER, [first, second], []) == []  # 6 + 4 = 10
    [finding] = check_invoice(invoice, ORDER, [first], [])
    assert finding.message == "A-1: billed 10, but only 6 received."
