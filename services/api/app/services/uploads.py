"""Turn uploaded files into a batch, documents and processing jobs."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePath

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditObject, Batch, Document, Job
from app.schemas.batch import UploadOutcome, UploadResult
from app.services.audit import Actor, record
from app.storage import LocalStorage

# The first bytes of each allowed file type ("magic numbers").
FILE_SIGNATURES = {
    b"%PDF-": "application/pdf",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
}
PROCESS_DOCUMENT_JOB = "process_document"


@dataclass
class IncomingFile:
    filename: str
    content: bytes


class NoFilesAcceptedError(Exception):
    """Raised when every file in an upload was rejected or a duplicate."""

    def __init__(self, results: list[UploadResult]) -> None:
        super().__init__("No files were accepted.")
        self.results = results


def detect_file_type(content: bytes) -> str | None:
    """Return the real content type from the file's first bytes, or None."""
    for signature, content_type in FILE_SIGNATURES.items():
        if content.startswith(signature):
            return content_type
    return None


def display_name(filename: str) -> str:
    """The file's own name without any folders, for showing to users."""
    return PurePath(filename.replace("\\", "/")).name[:255] or "file"


def safe_filename(filename: str) -> str:
    """A name that is safe on disk: no folders, no '../', only plain characters."""
    name = re.sub(r"[^A-Za-z0-9._-]", "_", display_name(filename)).strip("._")
    return name[:100] or "file"


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def create_batch_from_uploads(
    session: Session,
    storage: LocalStorage,
    files: list[IncomingFile],
    batch_name: str,
    max_upload_mb: int,
    uploaded_by: Actor,
) -> tuple[Batch, list[UploadResult]]:
    """Validate the files, store the good ones and queue a job for each.

    Returns the new batch and one result per file, in upload order.
    Raises NoFilesAcceptedError if nothing could be accepted.
    """
    existing = _find_existing(session, [sha256(file.content) for file in files])
    seen_in_upload: dict[str, str] = {}
    results: list[UploadResult] = []
    to_store: list[tuple[UploadResult, IncomingFile, str, str]] = []

    for file in files:
        name = display_name(file.filename)
        problem, content_type = _check_file(file, max_upload_mb)
        checksum = sha256(file.content)
        if problem:
            result = UploadResult(
                filename=name, outcome=UploadOutcome.REJECTED, detail=problem
            )
        elif checksum in existing:
            result = UploadResult(
                filename=name,
                outcome=UploadOutcome.DUPLICATE,
                existing_document_id=existing[checksum],
                detail=f"Already uploaded as document {existing[checksum]}.",
            )
        elif checksum in seen_in_upload:
            result = UploadResult(
                filename=name,
                outcome=UploadOutcome.DUPLICATE,
                detail=f"Same file as {seen_in_upload[checksum]} in this upload.",
            )
        else:
            seen_in_upload[checksum] = name
            result = UploadResult(filename=name, outcome=UploadOutcome.ACCEPTED)
            to_store.append((result, file, checksum, content_type))
        results.append(result)

    if not to_store:
        raise NoFilesAcceptedError(results)

    batch = Batch(name=batch_name)
    session.add(batch)
    saved_keys: list[str] = []
    try:
        for result, file, checksum, content_type in to_store:
            document = Document(
                batch=batch,
                filename=result.filename,
                content_type=content_type,
                size_bytes=len(file.content),
                checksum=checksum,
                storage_key="",
            )
            session.add(document)
            session.flush()  # the database assigns batch.id and document.id

            document.storage_key = (
                f"batches/{batch.id}/{document.id}_{safe_filename(file.filename)}"
            )
            storage.save(document.storage_key, file.content)
            saved_keys.append(document.storage_key)

            session.add(
                Job(kind=PROCESS_DOCUMENT_JOB, payload={"document_id": document.id})
            )
            record(
                session,
                uploaded_by,
                AuditAction.DOCUMENT_UPLOADED,
                AuditObject.DOCUMENT,
                document.id,
                {"filename": document.filename, "batch_id": batch.id},
            )
            result.document_id = document.id
        session.commit()
    except Exception:
        # All or nothing: undo the database changes and remove written files.
        session.rollback()
        for key in saved_keys:
            storage.delete(key)
        raise
    return batch, results


def _check_file(file: IncomingFile, max_upload_mb: int) -> tuple[str | None, str]:
    """Return (problem, content_type). problem is None when the file is fine."""
    if not file.content:
        return "The file is empty.", ""
    if len(file.content) > max_upload_mb * 1024 * 1024:
        return f"The file is larger than {max_upload_mb} MB.", ""
    content_type = detect_file_type(file.content)
    if content_type is None:
        return "Only PDF, PNG or JPEG files are allowed.", ""
    return None, content_type


def _find_existing(session: Session, checksums: list[str]) -> dict[str, int]:
    """Map checksum → id for files that are already in the database."""
    rows = session.execute(
        select(Document.checksum, Document.id).where(Document.checksum.in_(checksums))
    )
    return {checksum: document_id for checksum, document_id in rows}
