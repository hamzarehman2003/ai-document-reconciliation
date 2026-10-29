"""People correcting values the AI misread."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditAction,
    AuditEvent,
    Document,
    DocumentStatus,
    DocumentType,
    Job,
    MatchStatus,
)
from app.services.matching import MATCH_DOCUMENT_JOB, update_matches
from factories import add_document, add_three_way_set, unique
from fakes import FakeExtractor

PDF = "application/pdf"


def correct(
    client: TestClient, document: Document | int, field: str, value: str | None
):
    document_id = document if isinstance(document, int) else document.id
    return client.patch(
        f"/api/documents/{document_id}/fields",
        json={
            "field": field,
            "value": value,
            "reviewer": "Sara (AP team)",
            "note": "Checked the PDF",
        },
    )


def test_correct_a_total(client: TestClient, session: Session) -> None:
    invoice = add_document(session, DocumentType.INVOICE, unique("INV"), quantity="8")

    response = correct(client, invoice, "total", "45.00")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == "45.00"
    [correction] = body["corrections"]
    assert correction["field"] == "total"
    assert (correction["old_value"], correction["new_value"]) == ("40.00", "45.00")
    assert correction["corrected_by"] == "Sara (AP team)"
    event = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.action == AuditAction.FIELD_CORRECTED)
        .order_by(AuditEvent.id.desc())
    ).first()
    assert event.details == {"field": "total", "old": "40.00", "new": "45.00"}
    queued = session.scalars(
        select(Job).where(
            Job.kind == MATCH_DOCUMENT_JOB,
            Job.payload["document_id"].as_integer() == invoice.id,
        )
    ).all()
    assert len(queued) == 1  # the 3-way match will be checked again


def test_correct_a_line_item_and_clear_a_value(
    client: TestClient, session: Session
) -> None:
    invoice = add_document(session, DocumentType.INVOICE, unique("INV"), quantity="8")

    assert correct(client, invoice, "line_items.1.quantity", "7").status_code == 200
    body = correct(client, invoice, "po_reference", "").json()

    assert body["line_items"][0]["quantity"] == "7.000"
    assert body["po_reference"] is None  # empty = not on the document


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("issue_date", "31/01/2026", "Enter a date as YYYY-MM-DD."),
        ("total", "about 40", "Enter an amount like 1234.50."),
        ("currency", "Euro", "Enter a 3-letter currency code like EUR."),
        ("line_items.1.quantity", "-2", "A quantity can't be negative."),
        ("line_items.9.quantity", "2", "The document has no line item 9."),
        ("colour", "blue", "'colour' can't be corrected."),
    ],
)
def test_invalid_corrections_are_explained(
    client: TestClient, session: Session, field: str, value: str, message: str
) -> None:
    invoice = add_document(session, DocumentType.INVOICE, unique("INV"), quantity="8")

    response = correct(client, invoice, field, value)

    assert response.status_code == 422
    assert response.json()["detail"] == message


def test_only_processed_documents_can_be_corrected(
    client: TestClient, session: Session
) -> None:
    invoice = add_document(session, DocumentType.INVOICE, unique("INV"), quantity="8")
    invoice.status = DocumentStatus.PROCESSING
    session.flush()

    assert correct(client, invoice, "total", "1.00").status_code == 409


def test_correction_survives_reprocessing(
    client: TestClient,
    session: Session,
    run_jobs: Callable[[], int],
    make_pdf: Callable[[], bytes],
    fake_extractor: FakeExtractor,
    empty_queue: None,
) -> None:
    response = client.post(
        "/api/batches", files=[("files", ("inv.pdf", make_pdf(), PDF))]
    )
    document_id = response.json()["results"][0]["document_id"]
    run_jobs()  # the (fake) AI reads total 1333.26

    correct(client, document_id, "total", "1300.00")
    client.post(f"/api/documents/{document_id}/reprocess")
    run_jobs()  # read again: the AI still says 1333.26

    document = session.get(Document, document_id)
    session.refresh(document)
    assert str(document.total) == "1300.00"  # the person's fix wins


def test_correction_rechecks_the_match(
    client: TestClient,
    session: Session,
    run_jobs: Callable[[], int],
    empty_queue: None,
) -> None:
    _, _, invoice = add_three_way_set(session, ordered="10", received="8", billed="10")
    update_matches(session, invoice)
    assert invoice.match_case.status is MatchStatus.NEEDS_REVIEW

    # The AI misread the invoice: it really bills 8 boxes, 40.00.
    for field, value in [
        ("line_items.1.quantity", "8"),
        ("line_items.1.line_total", "40.00"),
        ("subtotal", "40.00"),
        ("total", "40.00"),
    ]:
        assert correct(client, invoice, field, value).status_code == 200
    run_jobs()

    session.refresh(invoice.match_case)
    assert invoice.match_case.status is MatchStatus.MATCHED
