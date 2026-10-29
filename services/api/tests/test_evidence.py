from datetime import date
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Document, Job, JobStatus, LineItem
from app.services.evidence import (
    amount_variants,
    date_variants,
    find_evidence,
    normalize,
    quantity_variants,
)
from app.services.page_text import OCR, PDF_TEXT, TextLine, Word, read_page_lines
from app.storage import LocalStorage
from app.worker import process_next_job

PDF = "application/pdf"


@pytest.fixture(autouse=True)
def empty_queue(session: Session) -> None:
    """Hide jobs from the dev database (rolled back after each test)."""
    session.execute(
        update(Job)
        .where(Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
        .values(status=JobStatus.DONE)
    )


def line(y: float, *texts: str) -> TextLine:
    """A fake text line: words side by side at height y."""
    words = [
        Word(text, x0=0.1 * i, y0=y, x1=0.1 * i + 0.08, y1=y + 0.02)
        for i, text in enumerate(texts)
    ]
    return TextLine(page=1, words=words, source=PDF_TEXT)


def pdf_with_lines(*lines: str, scanned: bool = False) -> bytes:
    """A one-page PDF with the given text; scanned=True turns it into a picture."""
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        for index, text in enumerate(lines):
            page.insert_text((72, 80 + 40 * index), text, fontsize=16)
        if not scanned:
            return pdf.tobytes()
        picture = page.get_pixmap(dpi=150).tobytes("png")
    with pymupdf.open() as scan:
        page = scan.new_page()
        page.insert_image(page.rect, stream=picture)
        return scan.tobytes()


# --- Ways of writing a value ---


def test_value_variants() -> None:
    assert {"1,234.50", "1234.50", "1.234,50", "1234,50"} == amount_variants(
        Decimal("1234.5")
    )
    assert quantity_variants(Decimal("10.000")) == {"10"}
    assert quantity_variants(Decimal("16.250")) == {"16.25", "16,25"}
    variants = date_variants(date(2026, 1, 5))
    for written in ["2026-01-05", "05/01/2026", "01/05/2026", "January 5, 2026"]:
        assert normalize(written) in variants
    assert normalize(".AOS-1002") == "aos-1002"  # a speck of dust read as a dot


# --- Finding values on a page ---


def make_document(**fields: object) -> Document:
    return Document(
        filename="x.pdf",
        content_type=PDF,
        size_bytes=1,
        checksum="x",
        storage_key="x",
        **fields,
    )


def test_finds_header_values_in_any_format() -> None:
    document = make_document(
        document_number="CPF-84364",
        vendor_name="Cedar & Pine Furniture",
        issue_date=date(2026, 1, 30),
        total=Decimal("30706.76"),
    )
    lines = [
        line(0.05, "Cedar", "&", "Pine", "Furniture"),
        line(0.10, "Invoice", "Number", "CPF-84364"),
        line(0.12, "Invoice", "date", "30.01.2026"),
        line(0.80, "Total", "due", "30.706,76", "€"),
    ]

    found = {e.field: e for e in find_evidence(document, lines)}

    assert found["vendor_name"].text == "Cedar & Pine Furniture"
    assert found["document_number"].y0 == pytest.approx(0.10)
    assert found["issue_date"].text == "30.01.2026"
    assert found["total"].text == "30.706,76"


def test_line_item_values_are_searched_in_their_own_row() -> None:
    document = make_document()
    document.line_items = [
        LineItem(
            position=1,
            sku="SIP-24",
            description="Hex bolts (box of 24)",
            quantity_ordered=Decimal("24"),
            quantity=Decimal("24"),
        )
    ]
    lines = [
        line(0.30, "SIP-24", "Hex", "bolts", "(box", "of", "24)", "24", "24"),
        line(0.40, "SIP-99", "Other", "item", "24", "24"),  # another row: ignored
    ]

    found = {e.field: e for e in find_evidence(document, lines)}

    # Same number in two columns: ordered is the left one, received the right one.
    assert found["line_items.1.quantity_ordered"].x0 == pytest.approx(0.6)
    assert found["line_items.1.quantity"].x0 == pytest.approx(0.7)


def test_value_not_on_the_page_gets_no_evidence() -> None:
    document = make_document(document_number="INV-999", total=Decimal("10.00"))

    found = find_evidence(document, [line(0.1, "Invoice", "INV-123")])

    assert found == []


# --- Reading words: PDF text and OCR ---


def test_digital_pdf_words_come_from_the_pdf(tmp_path: Path) -> None:
    path = tmp_path / "invoice.pdf"
    path.write_bytes(pdf_with_lines("Invoice No. INV-48213"))

    lines = read_page_lines(path, PDF, max_pages=5)

    assert lines[0].source == PDF_TEXT
    assert [w.text for w in lines[0].words] == ["Invoice", "No.", "INV-48213"]


def test_scanned_pdf_is_read_with_ocr(tmp_path: Path) -> None:
    path = tmp_path / "scan.pdf"
    path.write_bytes(
        pdf_with_lines("Invoice No. INV-48213", "Total $1,234.50", scanned=True)
    )

    lines = read_page_lines(path, PDF, max_pages=5)

    words = {w.text: w for found in lines for w in found.words}
    assert all(found.source == OCR for found in lines)
    assert "INV-48213" in words
    assert "$1,234.50" in words
    assert words["INV-48213"].y0 < words["$1,234.50"].y0  # first line is above
    assert words["INV-48213"].confidence > 0.8


# --- End to end: the worker saves evidence, the API serves it ---


def test_processing_saves_evidence_and_serves_page_images(
    client: TestClient, session: Session, storage: LocalStorage
) -> None:
    # The fake AI answers number AOS-68878 and total 1333.26 (see tests/fakes.py).
    content = pdf_with_lines("Invoice AOS-68878", "Total due $1,333.26")
    response = client.post("/api/batches", files=[("files", ("inv.pdf", content, PDF))])
    document_id = response.json()["results"][0]["document_id"]

    process_next_job(session, storage)

    body = client.get(f"/api/documents/{document_id}").json()
    fields = {e["field"]: e for e in body["evidence"]}
    assert fields["document_number"]["text"] == "AOS-68878"
    assert fields["total"]["text"] == "$1,333.26"
    assert fields["total"]["source"] == "pdf_text"
    assert "vendor_name" not in fields  # the fake vendor isn't printed on this page

    page = client.get(f"/api/documents/{document_id}/pages/1")
    assert page.status_code == 200
    assert page.content.startswith(b"\x89PNG")
    assert client.get(f"/api/documents/{document_id}/pages/2").status_code == 404
