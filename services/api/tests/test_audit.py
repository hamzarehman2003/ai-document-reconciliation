"""The audit log: every step of a document's life is recorded."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.matching import update_matches
from factories import add_three_way_set

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
        json={"decision": "approve", "reviewer": "Sara (AP team)"},
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
