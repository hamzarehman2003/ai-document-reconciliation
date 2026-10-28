"""The background worker: takes jobs from the queue and runs them.

It runs as its own process, next to the API. From services/api:
    ../../venv/Scripts/python -m app.worker          # keep running
    ../../venv/Scripts/python -m app.worker --once   # process what's waiting, then exit
"""

import argparse
import logging
import signal
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Job, JobStatus
from app.services.document_processing import mark_document_failed, process_document
from app.services.job_queue import (
    PermanentJobError,
    claim_next_job,
    complete_job,
    fail_job,
    requeue_stale_jobs,
)
from app.services.uploads import PROCESS_DOCUMENT_JOB
from app.storage import LocalStorage, get_storage

logger = logging.getLogger("worker")

STALE_CHECK_SECONDS = 60


@dataclass(frozen=True)
class JobHandler:
    run: Callable[[Session, LocalStorage, dict[str, Any]], None]
    on_give_up: Callable[[Session, dict[str, Any], str], None] | None = None


# Which function runs each kind of job.
HANDLERS: dict[str, JobHandler] = {
    PROCESS_DOCUMENT_JOB: JobHandler(
        run=process_document, on_give_up=mark_document_failed
    ),
}


def process_next_job(session: Session, storage: LocalStorage) -> Job | None:
    """Claim one job and run it. Returns the job, or None if nothing is due."""
    job = claim_next_job(session)
    if job is None:
        return None

    logger.info(
        "Job %s (%s) started, attempt %s of %s",
        job.id,
        job.kind,
        job.attempts,
        job.max_attempts,
    )
    handler = HANDLERS.get(job.kind)
    try:
        if handler is None:
            raise PermanentJobError(f"Unknown job kind '{job.kind}'.")
        handler.run(session, storage, job.payload)
    except Exception as error:
        session.rollback()  # throw away half-finished changes
        fail_job(session, job, error)
        if job.status is JobStatus.FAILED:
            logger.error("Job %s failed for good: %s", job.id, error)
            if handler is not None and handler.on_give_up is not None:
                handler.on_give_up(session, job.payload, str(error))
        else:
            logger.warning("Job %s failed (%s); will retry later", job.id, error)
    else:
        complete_job(session, job)
        logger.info("Job %s done", job.id)
    return job


def run_worker(once: bool = False) -> None:
    """Keep processing jobs until stopped (or until the queue is empty with once)."""
    storage = get_storage()
    stopping = False

    def request_stop(signum: int, frame: object) -> None:
        nonlocal stopping
        stopping = True
        logger.info("Stopping after the current job... (Ctrl+C again to force)")
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    signal.signal(signal.SIGINT, request_stop)
    logger.info("Worker started. Waiting for jobs... (Ctrl+C to stop)")

    last_stale_check = float("-inf")
    while not stopping:
        if time.monotonic() - last_stale_check > STALE_CHECK_SECONDS:
            with SessionLocal() as session:
                requeued = requeue_stale_jobs(session)
            if requeued:
                logger.warning("Put %s stuck job(s) back in the queue", requeued)
            last_stale_check = time.monotonic()

        with SessionLocal() as session:
            job = process_next_job(session, storage)
        if job is None:
            if once:
                break
            time.sleep(settings.worker_poll_seconds)

    logger.info("Worker stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the background worker.")
    parser.add_argument(
        "--once", action="store_true", help="process waiting jobs, then exit"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    run_worker(once=args.once)


if __name__ == "__main__":
    main()
