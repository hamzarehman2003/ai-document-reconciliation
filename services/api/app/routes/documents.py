"""Look at single documents and download the original file."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import SessionDep
from app.models import Document
from app.schemas.document import DocumentOut
from app.storage import StorageDep

router = APIRouter(prefix="/api/documents", tags=["documents"])


def get_document_or_404(session: Session, document_id: int) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "Document not found.")
    return document


@router.get("/{document_id}")
def get_document(session: SessionDep, document_id: int) -> DocumentOut:
    return DocumentOut.model_validate(get_document_or_404(session, document_id))


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
