"""The work done for each uploaded document.

For now: open the file and count its pages. AI extraction is added here next.
"""

from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image
from sqlalchemy.orm import Session

from app.models import Document, DocumentStatus
from app.services.job_queue import PermanentJobError
from app.storage import LocalStorage


def process_document(
    session: Session, storage: LocalStorage, payload: dict[str, Any]
) -> None:
    """Handler for 'process_document' jobs."""
    document = session.get(Document, payload["document_id"])
    if document is None:
        raise PermanentJobError(f"Document {payload['document_id']} does not exist.")

    document.status = DocumentStatus.PROCESSING
    document.error_message = None
    session.commit()  # so the app can already show "processing"

    path = storage.path(document.storage_key)
    if not path.is_file():
        raise PermanentJobError("The uploaded file is missing from storage.")

    document.page_count = count_pages(path, document.content_type)
    document.status = DocumentStatus.PROCESSED
    session.commit()


def mark_document_failed(
    session: Session, payload: dict[str, Any], message: str
) -> None:
    """Called when a 'process_document' job has given up for good."""
    document = session.get(Document, payload.get("document_id"))
    if document is not None:
        document.status = DocumentStatus.FAILED
        document.error_message = message
        session.commit()


def count_pages(path: Path, content_type: str) -> int:
    """Number of pages in a PDF; images count as one page."""
    if content_type == "application/pdf":
        try:
            with pymupdf.open(path) as pdf:
                pages = pdf.page_count
        except Exception as error:
            raise PermanentJobError("The PDF is damaged and cannot be read.") from error
        if pages == 0:
            raise PermanentJobError("The PDF has no pages.")
        return pages

    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as error:
        raise PermanentJobError("The image is damaged and cannot be read.") from error
    return 1
