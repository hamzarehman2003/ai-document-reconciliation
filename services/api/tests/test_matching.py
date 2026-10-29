from collections.abc import Callable
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import (
    Batch,
    Document,
    DocumentStatus,
    DocumentType,
    Job,
    JobStatus,
    LineItem,
    MatchStatus,
)
from app.services import matching
from app.services.matching import MATCH_DOCUMENT_JOB, update_matches

VENDOR = "Apex Office Supplies"
PDF = "application/pdf"


def unique(prefix: str) -> str:
    """Document numbers that can't clash with documents in the dev database."""
    return f"{prefix}-{uuid4().hex[:8].upper()}"


def add_document(
    session: Session,
    doc_type: DocumentType,
    number: str,
    *,
    quantity: str,
    po_reference: str | None = None,
    vendor: str = VENDOR,
    line_total: str | None = None,
) -> Document:
    """A processed document with one line: SKU A-1 at 5.00 each."""
    quantity_value = Decimal(quantity)
    total = Decimal(line_total) if line_total else quantity_value * Decimal("5.00")
    document = Document(
        batch=Batch(name="Test"),
        filename=f"{number}.pdf",
        content_type=PDF,
        size_bytes=1,
        checksum=uuid4().hex,
        storage_key="x",
        status=DocumentStatus.PROCESSED,
        doc_type=doc_type,
        document_number=number,
        vendor_name=vendor,
        po_reference=po_reference,
        subtotal=total,
        tax=Decimal("0"),
        total=total,
        line_items=[
            LineItem(
                position=1,
                sku="A-1",
                description="Copy paper",
                quantity=quantity_value,
                unit_price=Decimal("5.00"),
                line_total=total,
            )
        ],
    )
    session.add(document)
    session.flush()
    return document


def codes(document: Document) -> list[str]:
    return [problem.code.value for problem in document.match_case.discrepancies]


def test_invoice_waits_for_its_po_and_receipt_then_matches(session: Session) -> None:
    po_number = unique("PO")
    invoice = add_document(
        session,
        DocumentType.INVOICE,
        unique("INV"),
        quantity="8",
        po_reference=po_number,
    )

    update_matches(session, invoice)
    assert invoice.match_case.status is MatchStatus.WAITING
    assert invoice.match_case.waiting_for == ["purchase_order", "goods_receipt"]

    order = add_document(session, DocumentType.PURCHASE_ORDER, po_number, quantity="10")
    update_matches(session, order)
    assert invoice.match_case.status is MatchStatus.WAITING  # receipt still missing

    receipt = add_document(
        session,
        DocumentType.GOODS_RECEIPT,
        unique("GRN"),
        quantity="8",
        po_reference=po_number,
    )
    update_matches(session, receipt)
    case = invoice.match_case
    assert case.status is MatchStatus.MATCHED  # partial delivery, billed correctly
    assert case.purchase_order_id == order.id
    assert case.goods_receipts == [receipt]
    assert case.discrepancies == []


def test_overbilling_is_found_whatever_the_upload_order(session: Session) -> None:
    po_number = unique("PO")
    receipt = add_document(
        session,
        DocumentType.GOODS_RECEIPT,
        unique("GRN"),
        quantity="8",
        po_reference=po_number,
    )
    add_document(session, DocumentType.PURCHASE_ORDER, po_number, quantity="10")
    invoice = add_document(
        session,
        DocumentType.INVOICE,
        unique("INV"),
        quantity="10",
        po_reference=po_number,
    )

    update_matches(session, invoice)

    case = invoice.match_case
    assert case.status is MatchStatus.NEEDS_REVIEW
    [problem] = case.discrepancies
    assert problem.code.value == "QTY_EXCEEDS_RECEIVED"
    assert problem.message == "A-1: billed 10, but only 8 received."
    assert {"document_id": receipt.id, "field": "line_items.1.quantity"} in problem.refs


def test_delivery_split_over_two_receipts(session: Session) -> None:
    po_number = unique("PO")
    add_document(session, DocumentType.PURCHASE_ORDER, po_number, quantity="10")
    first = add_document(
        session,
        DocumentType.GOODS_RECEIPT,
        unique("GRN"),
        quantity="6",
        po_reference=po_number,
    )
    second = add_document(
        session,
        DocumentType.GOODS_RECEIPT,
        unique("GRN"),
        quantity="4",
        po_reference=po_number,
    )
    invoice = add_document(
        session,
        DocumentType.INVOICE,
        unique("INV"),
        quantity="10",
        po_reference=po_number,
    )

    update_matches(session, invoice)

    assert invoice.match_case.status is MatchStatus.MATCHED  # 6 + 4 = 10 received
    assert invoice.match_case.goods_receipts == [first, second]


def test_duplicate_is_found_whatever_the_processing_order(session: Session) -> None:
    number = unique("INV")
    first = add_document(session, DocumentType.INVOICE, number, quantity="1")
    second = add_document(session, DocumentType.INVOICE, number, quantity="1")
    first.status = DocumentStatus.PROCESSING  # e.g. its job is waiting for a retry
    session.flush()

    update_matches(session, second)  # the later invoice finishes first
    assert "DUPLICATE_INVOICE" not in codes(second)  # nothing to compare with yet

    first.status = DocumentStatus.PROCESSED
    update_matches(session, first)  # the earlier one finishes: both are re-checked

    assert "DUPLICATE_INVOICE" not in codes(first)
    assert "DUPLICATE_INVOICE" in codes(second)


def test_po_read_differently_on_reprocessing_updates_its_invoices(
    session: Session,
) -> None:
    po_number = unique("PO")
    order = add_document(session, DocumentType.PURCHASE_ORDER, po_number, quantity="10")
    add_document(
        session,
        DocumentType.GOODS_RECEIPT,
        unique("GRN"),
        quantity="8",
        po_reference=po_number,
    )
    invoice = add_document(
        session,
        DocumentType.INVOICE,
        unique("INV"),
        quantity="8",
        po_reference=po_number,
    )
    update_matches(session, invoice)
    assert invoice.match_case.status is MatchStatus.MATCHED

    order.document_number = unique("PO")  # now read as another order number
    update_matches(session, order)

    assert invoice.match_case.purchase_order_id is None
    assert invoice.match_case.waiting_for == ["purchase_order"]


def test_failed_receipt_no_longer_counts(session: Session) -> None:
    po_number = unique("PO")
    add_document(session, DocumentType.PURCHASE_ORDER, po_number, quantity="10")
    receipt = add_document(
        session,
        DocumentType.GOODS_RECEIPT,
        unique("GRN"),
        quantity="10",
        po_reference=po_number,
    )
    invoice = add_document(
        session,
        DocumentType.INVOICE,
        unique("INV"),
        quantity="10",
        po_reference=po_number,
    )
    update_matches(session, invoice)

    receipt.status = DocumentStatus.FAILED  # e.g. reprocessing failed for good
    update_matches(session, receipt)

    assert invoice.match_case.goods_receipts == []
    assert invoice.match_case.status is MatchStatus.WAITING


def test_problems_found_and_still_waiting_for_documents(
    client: TestClient, session: Session
) -> None:
    invoice = add_document(
        session,
        DocumentType.INVOICE,
        unique("INV"),
        quantity="8",
        po_reference=unique("PO"),
        line_total="45.00",  # 8 × 5.00 is 40.00
    )
    update_matches(session, invoice)

    [case] = client.get("/api/match-cases", params={"invoice_id": invoice.id}).json()

    assert case["status"] == "needs_review"
    assert case["waiting_for"] == ["purchase_order", "goods_receipt"]


def test_document_that_is_no_longer_an_invoice_loses_its_case(session: Session) -> None:
    document = add_document(session, DocumentType.INVOICE, unique("INV"), quantity="1")
    update_matches(session, document)

    document.doc_type = DocumentType.UNKNOWN  # e.g. read differently after reprocessing
    update_matches(session, document)

    assert document.match_case is None


def test_matching_runs_as_its_own_job_and_can_fail_safely(
    client: TestClient,
    session: Session,
    run_jobs: Callable[[], int],
    make_pdf: Callable[[], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session.execute(  # hide jobs from the dev database (rolled back afterwards)
        update(Job)
        .where(Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
        .values(status=JobStatus.DONE)
    )

    def broken(session: Session, document: Document) -> None:
        raise RuntimeError("a bug in a rule")

    monkeypatch.setattr(matching, "update_matches", broken)
    response = client.post(
        "/api/batches", files=[("files", ("inv.pdf", make_pdf(), PDF))]
    )
    document_id = response.json()["results"][0]["document_id"]

    run_jobs()

    document = session.get(Document, document_id)
    assert document.status is DocumentStatus.PROCESSED  # extraction is kept
    match_job = session.scalars(
        select(Job).where(
            Job.kind == MATCH_DOCUMENT_JOB,
            Job.payload["document_id"].as_integer() == document_id,
        )
    ).one()
    assert match_job.status is JobStatus.QUEUED  # will be retried on its own
    assert match_job.last_error == "a bug in a rule"


def test_match_case_api(client: TestClient, session: Session) -> None:
    po_number = unique("PO")
    add_document(session, DocumentType.PURCHASE_ORDER, po_number, quantity="10")
    invoice = add_document(
        session,
        DocumentType.INVOICE,
        unique("INV"),
        quantity="10",
        po_reference=po_number,
        vendor="Bluewater Electronics",
    )
    update_matches(session, invoice)

    [case] = client.get("/api/match-cases", params={"invoice_id": invoice.id}).json()
    assert case["status"] == "needs_review"
    assert [d["code"] for d in case["discrepancies"]] == ["VENDOR_MISMATCH"]
    assert case["waiting_for"] == ["goods_receipt"]

    detail = client.get(f"/api/match-cases/{case['id']}").json()
    assert detail["invoice"]["vendor_name"] == "Bluewater Electronics"
    assert detail["purchase_order"]["document_number"] == po_number
    assert detail["goods_receipts"] == []

    counts = client.post("/api/match-cases/refresh").json()
    assert set(counts) == {"matched", "needs_review", "waiting"}
    assert client.get("/api/match-cases/999999").status_code == 404
