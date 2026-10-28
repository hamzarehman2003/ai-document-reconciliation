"""See what is in the background job queue."""

from fastapi import APIRouter
from sqlalchemy import select

from app.db import SessionDep
from app.models import Job, JobStatus
from app.schemas.job import JobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    session: SessionDep, status: JobStatus | None = None, limit: int = 50
) -> list[JobOut]:
    """The most recent jobs, newest first. Optionally only one status."""
    query = select(Job).order_by(Job.id.desc()).limit(min(limit, 200))
    if status is not None:
        query = query.where(Job.status == status)
    return [JobOut.model_validate(job) for job in session.scalars(query)]
