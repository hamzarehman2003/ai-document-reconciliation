"""Doors for automations such as n8n. They use an API key instead of a login."""

from typing import Annotated

from fastapi import APIRouter, File, Form

from app.auth import IntakeActorDep
from app.db import SessionDep
from app.routes.batches import BinaryFile, store_uploads
from app.schemas.batch import UploadResponse
from app.storage import StorageDep

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/inbound", status_code=201)
def inbound(
    session: SessionDep,
    storage: StorageDep,
    actor: IntakeActorDep,
    files: Annotated[list[BinaryFile], File(description="PDF, PNG or JPEG files")],
    sender: Annotated[str | None, Form(max_length=200)] = None,
    subject: Annotated[str | None, Form(max_length=200)] = None,
) -> UploadResponse:
    """Documents from an automation, e.g. an email inbox read by n8n.

    Exactly the same flow as the Upload page: checks, duplicates, AI reading,
    matching. Needs the `X-API-Key` header; the key can only upload.
    """
    return store_uploads(session, storage, files, batch_name(sender, subject), actor)


def batch_name(sender: str | None, subject: str | None) -> str:
    """'Email from billing@apex.com: Invoice AOS-68878', fitting the 200-char limit."""
    if not sender:
        return "Email intake"
    name = f"Email from {sender}"
    return (f"{name}: {subject}" if subject else name)[:200]
