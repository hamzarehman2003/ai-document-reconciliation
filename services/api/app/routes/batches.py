"""Upload files as a batch, and look at batches."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import WithJsonSchema
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import CurrentUserDep
from app.config import settings
from app.db import SessionDep
from app.models import Batch
from app.schemas.batch import BatchDetail, BatchSummary, UploadResponse
from app.services.audit import Actor
from app.services.uploads import (
    IncomingFile,
    NoFilesAcceptedError,
    create_batch_from_uploads,
)
from app.storage import LocalStorage, StorageDep

router = APIRouter(prefix="/api/batches", tags=["batches"])

# Marks each file as binary in the API docs, so /docs shows a file picker
# for every item (FastAPI leaves this out for lists of files).
BinaryFile = Annotated[
    UploadFile, WithJsonSchema({"type": "string", "format": "binary"})
]


@router.post("", status_code=201)
def upload_batch(
    session: SessionDep,
    storage: StorageDep,
    user: CurrentUserDep,
    files: Annotated[list[BinaryFile], File(description="PDF, PNG or JPEG files")],
    name: Annotated[str | None, Form(max_length=200)] = None,
) -> UploadResponse:
    """Upload invoices, purchase orders and receipts. Each file is queued."""
    batch_name = name or f"Upload {datetime.now():%d %b %Y %H:%M}"
    return store_uploads(session, storage, files, batch_name, user.actor)


def store_uploads(
    session: Session,
    storage: LocalStorage,
    files: list[UploadFile],
    batch_name: str,
    uploaded_by: Actor,
) -> UploadResponse:
    """The upload flow shared by this page's upload and automations (n8n):
    the same limits, checks and answers, whoever sends the files."""
    if len(files) > settings.max_files_per_batch:
        raise HTTPException(
            400, f"Upload at most {settings.max_files_per_batch} files at once."
        )

    incoming = [
        IncomingFile(filename=file.filename or "file", content=file.file.read())
        for file in files
    ]
    try:
        batch, results = create_batch_from_uploads(
            session,
            storage,
            incoming,
            batch_name,
            settings.max_upload_mb,
            uploaded_by=uploaded_by,
        )
    except NoFilesAcceptedError as error:
        raise HTTPException(
            400,
            {
                "message": "No files were accepted.",
                "results": [result.model_dump() for result in error.results],
            },
        ) from error
    return UploadResponse(batch=BatchDetail.from_batch(batch), results=results)


@router.get("")
def list_batches(session: SessionDep, limit: int = 20) -> list[BatchSummary]:
    """The most recent batches, newest first."""
    batches = session.scalars(
        select(Batch)
        .options(selectinload(Batch.documents))
        .order_by(Batch.id.desc())
        .limit(min(limit, 100))
    )
    return [BatchSummary.from_batch(batch) for batch in batches]


@router.get("/{batch_id}")
def get_batch(session: SessionDep, batch_id: int) -> BatchDetail:
    batch = session.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(404, "Batch not found.")
    return BatchDetail.from_batch(batch)
