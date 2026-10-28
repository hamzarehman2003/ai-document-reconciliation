import io
from collections.abc import Callable
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app import worker
from app.models import Document, DocumentStatus, Job, JobStatus
from app.services.document_processing import mark_document_failed
from app.services.job_queue import requeue_stale_jobs
from app.storage import LocalStorage
from app.worker import JobHandler, process_next_job

PDF = "application/pdf"


@pytest.fixture(autouse=True)
def empty_queue(session: Session) -> None:
    """Hide jobs already in the dev database, so tests only see their own.

    This happens inside the test transaction, so it is rolled back afterwards.
    """
    session.execute(
        update(Job)
        .where(Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
        .values(status=JobStatus.DONE)
    )


def upload_one(client: TestClient, filename: str, content: bytes, kind: str) -> int:
    response = client.post("/api/batches", files=[("files", (filename, content, kind))])
    assert response.status_code == 201, response.text
    return response.json()["results"][0]["document_id"]


def make_png() -> bytes:
    info = PngInfo()
    info.add_text("id", str(uuid4()))  # makes every PNG unique
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, format="PNG", pnginfo=info)
    return buffer.getvalue()


def job_for(session: Session, document_id: int) -> Job:
    return session.scalars(
        select(Job).where(Job.payload["document_id"].as_integer() == document_id)
    ).one()


def test_uploaded_pdf_is_processed(
    client: TestClient,
    session: Session,
    storage: LocalStorage,
    make_pdf: Callable[[], bytes],
) -> None:
    document_id = upload_one(client, "INV-1.pdf", make_pdf(), PDF)

    job = process_next_job(session, storage)

    assert job is not None
    assert job.status is JobStatus.DONE
    assert job.attempts == 1
    document = session.get(Document, document_id)
    assert document.status is DocumentStatus.PROCESSED
    assert document.page_count == 1


def test_uploaded_image_is_processed(
    client: TestClient, session: Session, storage: LocalStorage
) -> None:
    document_id = upload_one(client, "receipt.png", make_png(), "image/png")

    process_next_job(session, storage)

    document = session.get(Document, document_id)
    assert document.status is DocumentStatus.PROCESSED
    assert document.page_count == 1


def test_returns_none_when_nothing_is_waiting(
    session: Session, storage: LocalStorage
) -> None:
    assert process_next_job(session, storage) is None


def test_temporary_error_is_retried_then_gives_up(
    client: TestClient,
    session: Session,
    storage: LocalStorage,
    make_pdf: Callable[[], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def always_busy(session: Session, storage: LocalStorage, payload: Any) -> None:
        raise RuntimeError("Gemini is busy, try again later.")

    monkeypatch.setitem(
        worker.HANDLERS,
        "process_document",
        JobHandler(run=always_busy, on_give_up=mark_document_failed),
    )
    document_id = upload_one(client, "INV-2.pdf", make_pdf(), PDF)
    job = job_for(session, document_id)

    process_next_job(session, storage)

    session.refresh(job)
    assert job.status is JobStatus.QUEUED
    assert job.attempts == 1
    assert job.last_error == "Gemini is busy, try again later."
    assert job.run_after > session.scalar(select(func.now()))  # pushed later

    for _ in range(2):  # attempts 2 and 3, made due straight away
        job.run_after = func.now()
        session.commit()
        process_next_job(session, storage)

    session.refresh(job)
    assert job.status is JobStatus.FAILED
    assert job.attempts == 3
    document = session.get(Document, document_id)
    assert document.status is DocumentStatus.FAILED
    assert document.error_message == "Gemini is busy, try again later."


def test_corrupt_pdf_fails_without_retrying(
    client: TestClient, session: Session, storage: LocalStorage
) -> None:
    corrupt = f"%PDF-1.7 not really a pdf {uuid4()}".encode()
    document_id = upload_one(client, "broken.pdf", corrupt, PDF)

    job = process_next_job(session, storage)

    assert job.status is JobStatus.FAILED
    assert job.attempts == 1
    document = session.get(Document, document_id)
    assert document.status is DocumentStatus.FAILED
    assert document.error_message == "The PDF is damaged and cannot be read."


def test_unknown_job_kind_fails(session: Session, storage: LocalStorage) -> None:
    session.add(Job(kind="mystery", payload={}))
    session.commit()

    job = process_next_job(session, storage)

    assert job.status is JobStatus.FAILED
    assert job.last_error == "Unknown job kind 'mystery'."


def test_stuck_job_is_put_back_in_the_queue(session: Session) -> None:
    stuck = Job(
        kind="process_document",
        payload={"document_id": 1},
        status=JobStatus.RUNNING,
        attempts=1,
        locked_at=func.now() - timedelta(minutes=30),
    )
    session.add(stuck)
    session.commit()

    assert requeue_stale_jobs(session) == 1

    session.refresh(stuck)
    assert stuck.status is JobStatus.QUEUED
    assert stuck.locked_at is None


def test_list_jobs_filters_by_status(
    client: TestClient, make_pdf: Callable[[], bytes]
) -> None:
    document_id = upload_one(client, "INV-3.pdf", make_pdf(), PDF)

    jobs = client.get("/api/jobs", params={"status": "queued"}).json()

    assert any(job["payload"] == {"document_id": document_id} for job in jobs)
    assert all(job["status"] == "queued" for job in jobs)
