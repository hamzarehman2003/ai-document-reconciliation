import random
from decimal import Decimal
from pathlib import Path
from typing import Any

import pymupdf
import pytest
from faker import Faker

from scripts.generate_dataset.models import DocumentSet, Scenario
from scripts.generate_dataset.render_pdf import format_amount, render_invoice
from scripts.generate_dataset.scan import make_scanned_copy
from scripts.generate_dataset.scenarios import build_document_set, generate_sets
from scripts.generate_dataset.vendors import (
    build_buyer,
    build_receiving_staff,
    build_vendors,
)


@pytest.fixture
def companies() -> dict[str, Any]:
    fake = Faker("en_GB")
    fake.seed_instance(7)
    return {
        "buyer": build_buyer(fake),
        "vendors": build_vendors(fake),
        "staff": build_receiving_staff(fake),
    }


def find_problems(
    document_set: DocumentSet, earlier: list[DocumentSet]
) -> list[Scenario]:
    """A tiny version of the matching rules, used to check the answer keys."""
    order = document_set.purchase_order
    receipt = document_set.goods_receipt
    invoice = document_set.invoice
    received = {line.sku: line.quantity_received for line in receipt.lines}
    ordered_price = {line.sku: line.unit_price for line in order.lines}

    problems = set()
    for line in invoice.lines:
        if line.quantity > received[line.sku]:
            problems.add(Scenario.QTY_EXCEEDS_RECEIVED)
        if line.unit_price != ordered_price[line.sku]:
            problems.add(Scenario.PRICE_MISMATCH)
        if line.line_total != line.unit_price * line.quantity:
            problems.add(Scenario.LINE_TOTAL_MISMATCH)
    if invoice.total != invoice.subtotal + invoice.tax:
        problems.add(Scenario.TOTAL_MISMATCH)
    if invoice.po_number is None:
        problems.add(Scenario.MISSING_PO_REFERENCE)
    if invoice.vendor.vendor_id != order.vendor.vendor_id:
        problems.add(Scenario.VENDOR_MISMATCH)
    seen = {(s.invoice.vendor.vendor_id, s.invoice.number) for s in earlier}
    if (invoice.vendor.vendor_id, invoice.number) in seen:
        problems.add(Scenario.DUPLICATE_INVOICE)
    return sorted(problems)


@pytest.mark.parametrize("scenario", list(Scenario))
def test_each_scenario_breaks_only_its_own_rule(
    companies: dict[str, Any], scenario: Scenario
) -> None:
    rng = random.Random(1)
    earlier = generate_sets(3, rng, **companies)

    for number in range(10):  # several attempts with different random choices
        document_set = build_document_set(
            100 + number, scenario, rng, previous_sets=earlier, **companies
        )
        assert find_problems(document_set, earlier) == document_set.expected_codes


def test_receipt_never_exceeds_order(companies: dict[str, Any]) -> None:
    for document_set in generate_sets(40, random.Random(2), **companies):
        for line in document_set.goods_receipt.lines:
            assert 0 < line.quantity_received <= line.quantity_ordered


def test_order_totals_add_up(companies: dict[str, Any]) -> None:
    for document_set in generate_sets(40, random.Random(3), **companies):
        order = document_set.purchase_order
        assert order.subtotal == sum(line.line_total for line in order.lines)
        assert order.total == order.subtotal + order.tax


def test_same_seed_gives_same_sets(companies: dict[str, Any]) -> None:
    first = generate_sets(20, random.Random(42), **companies)
    second = generate_sets(20, random.Random(42), **companies)
    assert [s.model_dump() for s in first] == [s.model_dump() for s in second]


def test_amount_formats(companies: dict[str, Any]) -> None:
    us_vendor, eu_vendor = companies["vendors"][0], companies["vendors"][3]
    assert format_amount(Decimal("1234.5"), "USD", us_vendor.style) == "$1,234.50"
    assert format_amount(Decimal("1234.5"), "EUR", eu_vendor.style) == "1.234,50 €"


def test_digital_pdf_has_text_and_scan_does_not(
    companies: dict[str, Any], tmp_path: Path
) -> None:
    invoice = generate_sets(1, random.Random(5), **companies)[0].invoice
    digital = tmp_path / "invoice.pdf"
    scanned = tmp_path / "invoice_scan.pdf"

    render_invoice(invoice, digital)
    make_scanned_copy(digital, scanned, random.Random(5))

    with pymupdf.open(digital) as pdf:
        assert invoice.number in pdf[0].get_text()
    with pymupdf.open(scanned) as pdf:
        assert pdf[0].get_text().strip() == ""
