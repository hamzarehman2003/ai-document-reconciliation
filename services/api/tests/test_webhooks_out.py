"""Outgoing webhooks: tell n8n when an invoice is approved or needs review."""

import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job, MatchCase
from app.services.job_queue import PermanentJobError
from app.services.matching import update_matches
from app.services.webhooks import SEND_WEBHOOK_JOB, Event, event_body, send_webhook
from factories import add_three_way_set

URL = "http://n8n.test/webhook/invoiceiq-events"
SECRET = "test-webhook-secret"


@pytest.fixture(autouse=True)
def webhook_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "n8n_webhook_url", URL)
    monkeypatch.setattr(settings, "webhook_secret", SecretStr(SECRET))


def queued_events(session: Session, case: MatchCase) -> list[str]:
    jobs = session.scalars(
        select(Job)
        .where(Job.kind == SEND_WEBHOOK_JOB)
        .where(Job.payload["case_id"].as_integer() == case.id)
        .order_by(Job.id)
    )
    return [job.payload["event"] for job in jobs]


def matched_case(session: Session, billed: str = "8") -> MatchCase:
    _, _, invoice = add_three_way_set(
        session, ordered="10", received="8", billed=billed
    )
    update_matches(session, invoice)
    return invoice.match_case


def test_problems_found_queue_one_alert(session: Session) -> None:
    case = matched_case(session, billed="10")  # 10 billed, 8 received
    update_matches(session, case.invoice)  # checked again: still the same problem

    assert queued_events(session, case) == ["case.needs_review"]


def test_a_clean_match_sends_nothing(session: Session) -> None:
    case = matched_case(session)

    assert queued_events(session, case) == []


def test_approving_queues_an_event(client: TestClient, session: Session) -> None:
    case = matched_case(session)

    client.post(f"/api/match-cases/{case.id}/decision", json={"decision": "approve"})

    assert queued_events(session, case) == ["case.approved"]


def test_nothing_is_queued_when_switched_off(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "n8n_webhook_url", "")

    case = matched_case(session, billed="10")

    assert queued_events(session, case) == []


def test_the_message_has_what_a_sheet_row_or_alert_needs(session: Session) -> None:
    case = matched_case(session, billed="10")

    body = event_body(Event.CASE_NEEDS_REVIEW, case)

    assert body["event"] == "case.needs_review"
    assert body["vendor"] == "Apex Office Supplies"
    assert (body["currency"], body["total"]) == ("EUR", "50.00")
    assert body["verdict"] == "needs_review"
    assert body["summary"].startswith("Needs review: 1 problem.")
    assert [problem["code"] for problem in body["problems"]] == ["QTY_EXCEEDS_RECEIVED"]
    assert body["link"] == f"http://localhost:3001/review/{case.invoice_id}"
    json.dumps(body)  # everything can be sent as JSON


class FakeN8n:
    """Stands in for urlopen: remembers the request, or fails with a status."""

    def __init__(self, status: int = 200) -> None:
        self.status = status
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        self.requests.append(request)
        if self.status >= 400:
            raise urllib.error.HTTPError(
                request.full_url, self.status, "error", {}, io.BytesIO()
            )
        return io.BytesIO()  # a context manager, like a real response


def test_the_worker_posts_the_event_with_the_secret(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    n8n = FakeN8n()
    monkeypatch.setattr("urllib.request.urlopen", n8n)
    case = matched_case(session)

    send_webhook(session, None, {"event": "case.approved", "case_id": case.id})

    [request] = n8n.requests
    assert request.full_url == URL
    assert request.get_header("X-webhook-secret") == SECRET
    assert json.loads(request.data)["event"] == "case.approved"


def test_a_wrong_address_is_not_retried(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", FakeN8n(status=404))
    case = matched_case(session)

    with pytest.raises(PermanentJobError):
        send_webhook(session, None, {"event": "case.approved", "case_id": case.id})


def test_n8n_being_down_is_retried(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", FakeN8n(status=503))
    case = matched_case(session)

    # A normal error: the job queue retries it later with backoff.
    with pytest.raises(urllib.error.HTTPError):
        send_webhook(session, None, {"event": "case.approved", "case_id": case.id})
