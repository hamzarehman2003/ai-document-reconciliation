"""All database models. Importing this package registers every table with Base."""

from app.models.audit_event import AuditAction, AuditEvent, AuditObject
from app.models.base import Base
from app.models.batch import Batch
from app.models.discrepancy import Discrepancy
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.extraction import Extraction
from app.models.field_correction import FieldCorrection
from app.models.field_evidence import FieldEvidence
from app.models.job import Job, JobStatus
from app.models.line_item import LineItem
from app.models.match_case import MatchCase, MatchStatus, ReviewStatus

__all__ = [
    "AuditAction",
    "AuditEvent",
    "AuditObject",
    "Base",
    "Batch",
    "Discrepancy",
    "Document",
    "DocumentStatus",
    "DocumentType",
    "Extraction",
    "FieldCorrection",
    "FieldEvidence",
    "Job",
    "JobStatus",
    "LineItem",
    "MatchCase",
    "MatchStatus",
    "ReviewStatus",
]
