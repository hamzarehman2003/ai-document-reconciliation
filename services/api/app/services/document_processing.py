"""The work done for each uploaded document.

1. Check the file and count its pages.
2. Read its data with AI.
3. Find where each value is on the page (PDF text, or OCR for scans).
4. Queue the 3-way match: a separate job, so it runs only after this
   document is saved, and its errors never undo the extraction.
"""

import logging
from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image
from sqlalchemy.orm import Session

from app.config import settings
from app.llm.base import PermanentExtractionError
from app.models import Document, DocumentStatus, FieldEvidence, Job
from app.services.evidence import find_evidence
from app.services.extraction import extract_document
from app.services.job_queue import PermanentJobError
from app.services.matching import MATCH_DOCUMENT_JOB
from app.services.page_text import read_page_lines
from app.storage import LocalStorage

logger = logging.getLogger(__name__)


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
    try:
        extract_document(session, storage, document)
    except PermanentExtractionError as error:
        raise PermanentJobError(str(error)) from error
    document.evidence = locate_evidence(document, path)
    document.status = DocumentStatus.PROCESSED
    queue_matching(session, document)
    session.commit()


def queue_matching(session: Session, document: Document) -> None:
    """Saved together with the document, so the match always follows it."""
    session.add(Job(kind=MATCH_DOCUMENT_JOB, payload={"document_id": document.id}))


def locate_evidence(document: Document, path: Path) -> list[FieldEvidence]:
    """Where each value is on the page. A bonus: if it fails, keep the data anyway."""
    try:
        lines = read_page_lines(path, document.content_type, settings.max_pages)
    except Exception:
        logger.exception("Could not read the words of document %s", document.id)
        return []
    return find_evidence(document, lines)


def mark_document_failed(
    session: Session, payload: dict[str, Any], message: str
) -> None:
    """Called when a 'process_document' job has given up for good."""
    document = session.get(Document, payload.get("document_id"))
    if document is not None:
        document.status = DocumentStatus.FAILED
        document.error_message = message
        queue_matching(session, document)  # cases using it must be re-checked
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
