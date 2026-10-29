"""The audit log: every step of a document's life is recorded."""

from collections.abc import Callable
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditObject
from app.services.audit import Actor, record
from app.services.matching import update_matches
from factories import TEST_USER, add_three_way_set

PDF = "application/pdf"


def test_a_documents_history_from_upload_to_match(
    client: TestClient,
    run_jobs: Callable[[], int],
    make_pdf: Callable[[], bytes],
    empty_queue: None,
) -> None:
    response = client.post(
        "/api/batches", files=[("files", ("inv.pdf", make_pdf(), PDF))]
    )
    document_id = response.json()["results"][0]["document_id"]
    run_jobs()

    events = client.get("/api/audit-events", params={"document_id": document_id}).json()

    actions = [event["action"] for event in reversed(events)]  # oldest first
    assert actions == [
        "document_uploaded",
        "document_processed",
        "match_status_changed",
    ]
    assert events[-1]["details"]["filename"] == "inv.pdf"
    assert events[0]["actor"] == "system"


def test_filter_by_object(client: TestClient, session: Session) -> None:
    _, _, invoice = add_three_way_set(session, ordered="10", received="8", billed="8")
    update_matches(session, invoice)
    case = invoice.match_case
    client.post(
        f"/api/match-cases/{case.id}/decision",
        json={"decision": "approve"},
    )

    events = client.get(
        "/api/audit-events", params={"object_type": "match_case", "object_id": case.id}
    ).json()

    assert [event["action"] for event in events] == [
        "case_approved",
        "match_status_changed",
    ]
    assert events[0]["actor"] == "Sara (AP team)"
    assert events[1]["details"] == {"from": None, "to": "matched"}


def test_events_name_the_invoice_they_are_about(
    client: TestClient, session: Session
) -> None:
    _, _, invoice = add_three_way_set(session, ordered="10", received="8", billed="8")
    update_matches(session, invoice)
    client.patch(
        f"/api/documents/{invoice.id}/fields",
        json={"field": "due_date", "value": "2026-04-01"},
    )
    client.post(
        f"/api/match-cases/{invoice.match_case.id}/decision",
        json={"decision": "approve"},
    )

    events = client.get("/api/audit-events", params={"document_id": invoice.id}).json()

    by_action = {event["action"]: event for event in events}
    expected = f"{invoice.document_number} · Apex Office Supplies"
    for action in ("field_corrected", "case_approved"):  # a document and a case event
        assert by_action[action]["subject"] == expected
        assert by_action[action]["document_id"] == invoice.id


def test_only_mine_keeps_what_the_signed_in_person_did(
    client: TestClient, session: Session
) -> None:
    _, _, invoice = add_three_way_set(session, ordered="10", received="8", billed="8")
    update_matches(session, invoice)  # done by the system
    record(  # done by someone else
        session,
        Actor("Omar", uuid4()),
        AuditAction.FIELD_CORRECTED,
        AuditObject.DOCUMENT,
        invoice.id,
    )
    client.post(
        f"/api/match-cases/{invoice.match_case.id}/decision",
        json={"decision": "approve"},
    )

    events = client.get(
        "/api/audit-events", params={"document_id": invoice.id, "mine": True}
    ).json()

    assert [event["action"] for event in events] == ["case_approved"]
    assert events[0]["actor"] == TEST_USER.name
