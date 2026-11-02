"""Tell automations (n8n) when something happens: outgoing webhooks.

The event is queued as a job in the same transaction as the action, so it is
sent only if the action was saved, and a failed send is retried by the worker
(n8n may be off for a while). The message is built when it is sent.
"""

import json
import urllib.error
import urllib.request
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job, MatchCase
from app.services.job_queue import PermanentJobError
from app.services.summary import summarize
from app.storage import LocalStorage

SEND_WEBHOOK_JOB = "send_webhook"
TIMEOUT_SECONDS = 10


class Event(StrEnum):
    CASE_APPROVED = "case.approved"
    CASE_NEEDS_REVIEW = "case.needs_review"


def queue_event(session: Session, event: Event, case: MatchCase) -> None:
    """Send the event to n8n soon. Does nothing when no webhook URL is set."""
    if settings.n8n_webhook_url:
        session.add(
            Job(
                kind=SEND_WEBHOOK_JOB,
                payload={"event": event.value, "case_id": case.id},
            )
        )


def send_webhook(session: Session, storage: LocalStorage, payload: dict) -> None:
    """The worker's job: POST the event as JSON to n8n."""
    if not settings.n8n_webhook_url:
        return  # switched off since the event was queued
    case = session.get(MatchCase, payload["case_id"])
    if case is None:
        raise PermanentJobError("The match case no longer exists.")
    body = json.dumps(event_body(Event(payload["event"]), case)).encode()
    post(settings.n8n_webhook_url, body)


def event_body(event: Event, case: MatchCase) -> dict[str, Any]:
    """What n8n receives: enough for a sheet row or an alert, without a lookup."""
    invoice = case.invoice
    summary = summarize(case)
    return {
        "event": event.value,
        "case_id": case.id,
        "invoice_id": invoice.id,
        "invoice_number": invoice.document_number,
        "vendor": invoice.vendor_name,
        "invoice_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
        "currency": invoice.currency,
        "total": str(invoice.total) if invoice.total is not None else None,
        "po_number": invoice.po_reference,
        "verdict": summary.verdict.value,
        "summary": summary.text,
        "problems": [
            {"code": problem.code.value, "message": problem.message}
            for problem in case.discrepancies
        ],
        "reviewed_by": case.reviewed_by,
        "reviewed_at": case.reviewed_at.isoformat() if case.reviewed_at else None,
        "review_note": case.review_note,
        "link": f"{settings.web_url}/review/{invoice.id}",
    }


def post(url: str, body: bytes) -> None:
    """POST with the shared secret. A 4xx won't get better by retrying; anything
    else (n8n down, 5xx, timeout) raises normally, so the worker retries later."""
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Secret": settings.webhook_secret.get_secret_value(),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS):
            pass
    except urllib.error.HTTPError as error:
        if 400 <= error.code < 500:
            raise PermanentJobError(
                f"n8n refused the event ({error.code}). Check N8N_WEBHOOK_URL, "
                "WEBHOOK_SECRET and that the workflow is active."
            ) from error
        raise
