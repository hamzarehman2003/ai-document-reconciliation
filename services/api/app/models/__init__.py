"""All database models. Importing this package registers every table with Base."""

from app.models.base import Base
from app.models.batch import Batch
from app.models.discrepancy import Discrepancy
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.extraction import Extraction
from app.models.field_evidence import FieldEvidence
from app.models.job import Job, JobStatus
from app.models.line_item import LineItem
from app.models.match_case import MatchCase, MatchStatus

__all__ = [
    "Base",
    "Batch",
    "Discrepancy",
    "Document",
    "DocumentStatus",
    "DocumentType",
    "Extraction",
    "FieldEvidence",
    "Job",
    "JobStatus",
    "LineItem",
    "MatchCase",
    "MatchStatus",
]
