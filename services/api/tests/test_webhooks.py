"""The inbound webhook: automations like n8n upload documents with an API key."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuditAction, AuditEvent, Batch, Document, DocumentStatus

KEY = "test-intake-key-1234567890"
PDF = "application/pdf"
URL = "/api/webhooks/inbound"


@pytest.fixture(autouse=True)
def intake_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "intake_api_key", SecretStr(KEY))


def send(
    client: TestClient, pdf: bytes, key: str | None = KEY, **form: str
) -> tuple[int, dict]:
    headers = {"X-API-Key": key} if key else {}
    response = client.post(
        URL, headers=headers, files=[("files", ("inv.pdf", pdf, PDF))], data=form
    )
    return response.status_code, response.json()


def test_documents_from_an_email_go_through_the_normal_flow(
    client: TestClient, session: Session, make_pdf: Callable[[], bytes]
) -> None:
    status, body = send(
        client, make_pdf(), sender="billing@apex.com", subject="Invoice AOS-68878"
    )

    assert status == 201
    document = session.get(Document, body["results"][0]["document_id"])
    assert document.status is DocumentStatus.UPLOADED  # queued for the AI
    batch = session.get(Batch, document.batch_id)
    assert batch.name == "Email from billing@apex.com: Invoice AOS-68878"
    event = session.scalars(
        select(AuditEvent).where(
            AuditEvent.action == AuditAction.DOCUMENT_UPLOADED,
            AuditEvent.object_id == document.id,
        )
    ).one()
    assert (event.actor, event.actor_id) == ("n8n (email intake)", None)


def test_the_same_file_again_is_a_duplicate(
    client: TestClient, make_pdf: Callable[[], bytes]
) -> None:
    pdf = make_pdf()
    send(client, pdf)

    status, body = send(client, pdf)  # e.g. the same email read twice

    assert status == 400
    assert body["detail"]["results"][0]["outcome"] == "duplicate"


@pytest.mark.parametrize("key", [None, "wrong-key"], ids=["no-key", "wrong-key"])
def test_without_the_right_key_nothing_is_uploaded(
    client: TestClient, make_pdf: Callable[[], bytes], key: str | None
) -> None:
    status, _ = send(client, make_pdf(), key=key)

    assert status == 401


def test_switched_off_when_no_key_is_set(
    client: TestClient, make_pdf: Callable[[], bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "intake_api_key", SecretStr(""))

    status, _ = send(client, make_pdf(), key="")

    assert status == 503


def test_a_login_token_is_not_enough(
    client: TestClient, make_pdf: Callable[[], bytes]
) -> None:
    # The client is signed in as TEST_USER, but the webhook only accepts its key.
    status, _ = send(client, make_pdf(), key=None)

    assert status == 401
