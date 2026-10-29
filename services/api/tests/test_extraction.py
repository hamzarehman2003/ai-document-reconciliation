from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.llm.base import PermanentExtractionError
from app.models import (
    Document,
    DocumentStatus,
    DocumentType,
    Extraction,
    Job,
    JobStatus,
)
from app.services.extraction import (
    CENT,
    clean_currency,
    clean_text,
    parse_date,
    to_decimal,
)
from app.services.pages import prepare_document
from app.storage import LocalStorage
from app.worker import process_next_job
from fakes import FakeExtractor

PDF = "application/pdf"


@pytest.fixture(autouse=True)
def empty_queue(session: Session) -> None:
    """Hide jobs from the dev database (rolled back after each test)."""
    session.execute(
        update(Job)
        .where(Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
        .values(status=JobStatus.DONE)
    )


def upload_pdf(client: TestClient, content: bytes) -> int:
    response = client.post("/api/batches", files=[("files", ("doc.pdf", content, PDF))])
    assert response.status_code == 201, response.text
    return response.json()["results"][0]["document_id"]


# --- Cleaning the AI's values (no database needed) ---


def test_values_are_cleaned() -> None:
    assert to_decimal(1234.5, CENT) == Decimal("1234.50")
    assert to_decimal(1234.505, CENT) == Decimal("1234.51")  # rounds half up
    assert to_decimal(None, CENT) is None
    assert parse_date("2026-01-23") == date(2026, 1, 23)
    assert parse_date("23/01/2026") is None  # not ISO → empty, not a crash
    assert parse_date(None) is None
    assert clean_currency(" eur ") == "EUR"
    assert clean_currency("€") is None
    assert clean_text("   ", 10) is None
    assert clean_text("  AOS-1  ", 10) == "AOS-1"


# --- Processing with the (fake) AI ---


def test_processing_saves_fields_line_items_and_extraction(
    client: TestClient,
    session: Session,
    storage: LocalStorage,
    make_pdf: Callable[[], bytes],
    fake_extractor: FakeExtractor,
) -> None:
    document_id = upload_pdf(client, make_pdf())

    job = process_next_job(session, storage)

    assert job.status is JobStatus.DONE
    document = session.get(Document, document_id)
    assert document.status is DocumentStatus.PROCESSED
    assert document.doc_type is DocumentType.INVOICE
    assert document.document_number == "AOS-68878"
    assert document.po_reference == "PO-2026-0001"
    assert document.currency == "USD"
    assert document.issue_date == date(2026, 1, 12)
    assert document.subtotal == Decimal("1234.50")
    assert [item.sku for item in document.line_items] == ["AOS-1001", "AOS-1008"]
    assert document.line_items[1].quantity == Decimal("16.250")
    extraction = document.extractions[0]
    assert extraction.model == "fake-model"
    assert extraction.input_tokens == 1000

    body = client.get(f"/api/documents/{document_id}").json()
    assert body["vendor_name"] == "Apex Office Supplies"
    assert body["total"] == "1333.26"
    assert len(body["line_items"]) == 2
    assert body["latest_extraction"]["model"] == "fake-model"


def test_reprocessing_uses_the_cache(
    client: TestClient,
    session: Session,
    storage: LocalStorage,
    make_pdf: Callable[[], bytes],
    fake_extractor: FakeExtractor,
) -> None:
    document_id = upload_pdf(client, make_pdf())
    process_next_job(session, storage)

    response = client.post(f"/api/documents/{document_id}/reprocess")
    assert response.status_code == 202
    process_next_job(session, storage)

    assert fake_extractor.calls == 1  # second time came from the cache
    count = session.scalar(
        select(func.count())
        .select_from(Extraction)
        .where(Extraction.document_id == document_id)
    )
    assert count == 1
    document = session.get(Document, document_id)
    assert document.status is DocumentStatus.PROCESSED
    assert len(document.line_items) == 2  # replaced, not doubled


def test_reprocess_refuses_when_already_waiting(
    client: TestClient, make_pdf: Callable[[], bytes]
) -> None:
    document_id = upload_pdf(client, make_pdf())  # upload already queued a job

    response = client.post(f"/api/documents/{document_id}/reprocess")

    assert response.status_code == 409


def test_busy_ai_is_retried(
    client: TestClient,
    session: Session,
    storage: LocalStorage,
    make_pdf: Callable[[], bytes],
    fake_extractor: FakeExtractor,
) -> None:
    fake_extractor.error = RuntimeError("503 UNAVAILABLE: model overloaded")
    upload_pdf(client, make_pdf())

    job = process_next_job(session, storage)

    assert job.status is JobStatus.QUEUED
    assert job.last_error == "503 UNAVAILABLE: model overloaded"


def test_permanent_ai_error_fails_the_document(
    client: TestClient,
    session: Session,
    storage: LocalStorage,
    make_pdf: Callable[[], bytes],
    fake_extractor: FakeExtractor,
) -> None:
    fake_extractor.error = PermanentExtractionError("The Gemini API key is not valid.")
    document_id = upload_pdf(client, make_pdf())

    job = process_next_job(session, storage)

    assert job.status is JobStatus.FAILED
    document = session.get(Document, document_id)
    assert document.status is DocumentStatus.FAILED
    assert document.error_message == "The Gemini API key is not valid."


# --- Preparing pages for the AI ---


def test_prepare_digital_pdf(tmp_path: Path, make_pdf: Callable[[], bytes]) -> None:
    path = tmp_path / "doc.pdf"
    path.write_bytes(make_pdf())

    prepared = prepare_document(path, PDF, max_pages=5)

    assert len(prepared.images) == 1
    assert prepared.images[0].mime_type == "image/png"
    assert prepared.images[0].data.startswith(b"\x89PNG")
    assert "Test invoice" in prepared.text


def test_prepare_scanned_pdf_has_no_text(tmp_path: Path) -> None:
    image = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 50, 50), False)
    image.clear_with(255)
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_image(page.rect, stream=image.tobytes("png"))
        path = tmp_path / "scan.pdf"
        pdf.save(path)

    prepared = prepare_document(path, PDF, max_pages=5)

    assert len(prepared.images) == 1
    assert prepared.text == ""


def test_prepare_image_is_passed_through(tmp_path: Path) -> None:
    path = tmp_path / "receipt.jpg"
    path.write_bytes(b"\xff\xd8\xff fake jpeg bytes")

    prepared = prepare_document(path, "image/jpeg", max_pages=5)

    assert prepared.images[0].data == path.read_bytes()
    assert prepared.images[0].mime_type == "image/jpeg"
