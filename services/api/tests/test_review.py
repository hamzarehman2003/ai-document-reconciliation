"""Approving, rejecting and reopening match cases."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditAction,
    AuditEvent,
    AuditObject,
    DocumentType,
    MatchCase,
    ReviewStatus,
)
from app.services.matching import update_matches
from factories import add_document, add_three_way_set, unique


def case_for(session: Session, *, received: str, billed: str = "8") -> MatchCase:
    """A checked invoice. received 8 + billed 8 → matched; billed more → problem."""
    _, _, invoice = add_three_way_set(
        session, ordered="10", received=received, billed=billed
    )
    update_matches(session, invoice)
    return invoice.match_case


def decide(client: TestClient, case: MatchCase, decision: str, note: str | None = None):
    body = {"decision": decision, "note": note, "reviewer": "Sara (AP team)"}
    return client.post(f"/api/match-cases/{case.id}/decision", json=body)


def actions(session: Session, case: MatchCase) -> list[AuditAction]:
    return list(
        session.scalars(
            select(AuditEvent.action)
            .where(
                AuditEvent.object_type == AuditObject.MATCH_CASE,
                AuditEvent.object_id == case.id,
            )
            .order_by(AuditEvent.id)
        )
    )


def test_approve_a_matched_invoice(client: TestClient, session: Session) -> None:
    case = case_for(session, received="8")

    response = decide(client, case, "approve")

    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "approved"
    assert body["reviewed_by"] == "Sara (AP team)"
    assert body["reviewed_at"] is not None
    assert AuditAction.CASE_APPROVED in actions(session, case)


def test_approving_an_invoice_with_problems_needs_a_note(
    client: TestClient, session: Session
) -> None:
    case = case_for(session, received="8", billed="10")  # billed 10, received 8

    without_note = decide(client, case, "approve")
    with_note = decide(client, case, "approve", "2 extra boxes arrive on Monday")

    assert without_note.status_code == 422
    assert "why it is approved anyway" in without_note.json()["detail"]
    assert with_note.status_code == 200
    assert with_note.json()["review_note"] == "2 extra boxes arrive on Monday"


def test_cannot_approve_while_documents_are_missing(
    client: TestClient, session: Session
) -> None:
    invoice = add_document(
        session,
        DocumentType.INVOICE,
        unique("INV"),
        quantity="1",
        po_reference=unique("PO"),
    )
    update_matches(session, invoice)

    response = decide(client, invoice.match_case, "approve", "looks fine")

    assert response.status_code == 409
    assert "Wait for the purchase order" in response.json()["detail"]


def test_reject_needs_a_note_and_reopen_clears_the_decision(
    client: TestClient, session: Session
) -> None:
    case = case_for(session, received="8")

    assert decide(client, case, "reject").status_code == 422
    rejected = decide(client, case, "reject", "Duplicate of a paid invoice").json()
    reopened = decide(client, case, "reopen").json()

    assert rejected["review_status"] == "rejected"
    assert reopened["review_status"] == "pending"
    assert reopened["reviewed_by"] is None
    assert actions(session, case)[-2:] == [
        AuditAction.CASE_REJECTED,
        AuditAction.CASE_REOPENED,
    ]


def test_decision_is_reset_when_the_match_result_changes(session: Session) -> None:
    order, _, invoice = add_three_way_set(
        session, ordered="10", received="8", billed="10"
    )
    update_matches(session, invoice)
    case = invoice.match_case
    case.review_status = ReviewStatus.APPROVED  # approved despite "only 8 received"

    # The rest of the delivery arrives: the problem the reviewer saw is gone.
    late_receipt = add_document(
        session,
        DocumentType.GOODS_RECEIPT,
        unique("GRN"),
        quantity="2",
        po_reference=order.document_number,
    )
    update_matches(session, late_receipt)

    assert case.review_status is ReviewStatus.PENDING
    assert AuditAction.DECISION_RESET in actions(session, case)


def test_decision_is_kept_when_a_recheck_finds_the_same(session: Session) -> None:
    case = case_for(session, received="8")
    case.review_status = ReviewStatus.APPROVED

    update_matches(session, case.invoice)

    assert case.review_status is ReviewStatus.APPROVED


@pytest.mark.parametrize("decision", ["approve", "maybe"])
def test_unknown_case_or_decision(client: TestClient, decision: str) -> None:
    response = client.post(
        "/api/match-cases/999999/decision", json={"decision": decision}
    )
    assert response.status_code == (404 if decision == "approve" else 422)
