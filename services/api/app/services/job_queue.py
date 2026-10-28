"""A simple job queue stored in the `jobs` table.

Workers claim jobs with SELECT ... FOR UPDATE SKIP LOCKED, so several
workers can run at the same time without ever taking the same job.
"""

from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job, JobStatus


class PermanentJobError(Exception):
    """An error that retrying cannot fix, for example a corrupt file."""


def claim_next_job(session: Session) -> Job | None:
    """Take the oldest job that is due, mark it running and return it."""
    job = session.scalars(
        select(Job)
        .where(Job.status == JobStatus.QUEUED, Job.run_after <= func.now())
        .order_by(Job.run_after, Job.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).first()
    if job is None:
        return None

    job.status = JobStatus.RUNNING
    job.attempts += 1
    job.locked_at = func.now()
    session.commit()
    return job


def complete_job(session: Session, job: Job) -> None:
    job.status = JobStatus.DONE
    job.locked_at = None
    job.last_error = None
    session.commit()


def fail_job(session: Session, job: Job, error: Exception) -> None:
    """Retry later with a growing delay, or give up for good.

    Gives up when the error is permanent or the job has used all its attempts.
    The delay doubles each time: 30 s, 60 s, 120 s, ...
    """
    if isinstance(error, PermanentJobError) or job.attempts >= job.max_attempts:
        job.status = JobStatus.FAILED
    else:
        delay = settings.job_retry_base_seconds * 2 ** (job.attempts - 1)
        job.status = JobStatus.QUEUED
        job.run_after = func.now() + timedelta(seconds=delay)
    job.last_error = str(error) or type(error).__name__
    job.locked_at = None
    session.commit()


def requeue_stale_jobs(session: Session) -> int:
    """Put back jobs stuck in 'running' because a worker died mid-job."""
    cutoff = func.now() - timedelta(minutes=settings.stale_job_minutes)
    result = session.execute(
        update(Job)
        .where(Job.status == JobStatus.RUNNING, Job.locked_at < cutoff)
        .values(status=JobStatus.QUEUED, locked_at=None)
    )
    session.commit()
    return result.rowcount
