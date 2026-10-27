"""Response shapes for batches and uploads."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from app.models import Batch, DocumentStatus
from app.schemas.document import DocumentOut


class UploadOutcome(StrEnum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


class UploadResult(BaseModel):
    """What happened to one uploaded file."""

    filename: str
    outcome: UploadOutcome
    document_id: int | None = None
    existing_document_id: int | None = None
    detail: str | None = None


class BatchSummary(BaseModel):
    id: int
    name: str
    created_at: datetime
    document_count: int
    status_counts: dict[DocumentStatus, int]

    @classmethod
    def from_batch(cls, batch: Batch) -> "BatchSummary":
        return cls(**_summary_fields(batch))


class BatchDetail(BatchSummary):
    documents: list[DocumentOut]

    @classmethod
    def from_batch(cls, batch: Batch) -> "BatchDetail":
        documents = [DocumentOut.model_validate(d) for d in batch.documents]
        return cls(**_summary_fields(batch), documents=documents)


class UploadResponse(BaseModel):
    batch: BatchDetail
    results: list[UploadResult]


def _summary_fields(batch: Batch) -> dict[str, object]:
    counts = {status: 0 for status in DocumentStatus}
    for document in batch.documents:
        counts[document.status] += 1
    return {
        "id": batch.id,
        "name": batch.name,
        "created_at": batch.created_at,
        "document_count": len(batch.documents),
        "status_counts": counts,
    }
