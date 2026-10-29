"""Look at single documents, correct their values, or process them again."""

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionDep
from app.models import Document, DocumentStatus, Job, JobStatus
from app.schemas.document import CorrectionRequest, DocumentDetail
from app.schemas.job import JobOut
from app.services.corrections import CorrectionError, correct_field
from app.services.matching import queue_matching
from app.services.pages import render_page_png
from app.services.uploads import PROCESS_DOCUMENT_JOB
from app.storage import StorageDep

router = APIRouter(prefix="/api/documents", tags=["documents"])


def get_document_or_404(session: Session, document_id: int) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "Document not found.")
    return document


@router.get("/{document_id}")
def get_document(session: SessionDep, document_id: int) -> DocumentDetail:
    """A document with the data the AI read from it and its line items."""
    return DocumentDetail.from_document(get_document_or_404(session, document_id))


@router.patch("/{document_id}/fields")
def correct_document_field(
    session: SessionDep, document_id: int, request: CorrectionRequest
) -> DocumentDetail:
    """Correct a value the AI misread. The 3-way match is then checked again."""
    document = get_document_or_404(session, document_id)
    if document.status is not DocumentStatus.PROCESSED:
        raise HTTPException(409, "Wait until the document is processed.")
    try:
        correct_field(
            session,
            document,
            request.field,
            request.value,
            request.reviewer,
            request.note,
        )
    except CorrectionError as error:
        raise HTTPException(422, str(error)) from error
    queue_matching(session, document)
    session.commit()
    session.refresh(document)
    return DocumentDetail.from_document(document)


@router.get("/{document_id}/file")
def get_document_file(
    session: SessionDep, storage: StorageDep, document_id: int
) -> FileResponse:
    """The original uploaded file, shown in the browser instead of downloaded."""
    document = get_document_or_404(session, document_id)
    path = storage.path(document.storage_key)
    if not path.is_file():
        raise HTTPException(404, "The file is missing from storage.")
    return FileResponse(
        path,
        media_type=document.content_type,
        filename=document.filename,
        content_disposition_type="inline",
    )


@router.get(
    "/{document_id}/pages/{page_number}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}}}},
)
def get_page_image(
    session: SessionDep, storage: StorageDep, document_id: int, page_number: int
) -> Response:
    """One page as an image, for the page viewer (evidence boxes are drawn on it)."""
    document = get_document_or_404(session, document_id)
    path = storage.path(document.storage_key)
    if not path.is_file():
        raise HTTPException(404, "The file is missing from storage.")

    if document.content_type != "application/pdf":  # a photo is its own single page
        if page_number != 1:
            raise HTTPException(404, f"The document has no page {page_number}.")
        return FileResponse(path, media_type=document.content_type)
    try:
        image = render_page_png(path, page_number)
    except IndexError as error:
        raise HTTPException(404, str(error)) from error
    return Response(image, media_type="image/png")


@router.post("/{document_id}/reprocess", status_code=202)
def reprocess_document(session: SessionDep, document_id: int) -> JobOut:
    """Queue the document to be processed again (uses the cache if possible)."""
    document = get_document_or_404(session, document_id)
    waiting = session.scalars(
        select(Job).where(
            Job.kind == PROCESS_DOCUMENT_JOB,
            Job.payload["document_id"].as_integer() == document_id,
            Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
        )
    ).first()
    if waiting is not None:
        raise HTTPException(409, f"Already waiting to be processed (job {waiting.id}).")

    job = Job(kind=PROCESS_DOCUMENT_JOB, payload={"document_id": document_id})
    document.status = DocumentStatus.UPLOADED
    document.error_message = None
    session.add(job)
    session.commit()
    return JobOut.model_validate(job)
