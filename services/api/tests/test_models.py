"""Database tests. They need Postgres running and `alembic upgrade head` applied.

Every test runs inside a transaction that is rolled back at the end,
so nothing is left behind in the database.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import check_database, engine
from app.models import Batch, Document, DocumentStatus, DocumentType, Job, JobStatus


@pytest.fixture
def session() -> Iterator[Session]:
    if not check_database():
        pytest.skip("Postgres is not running (docker compose up -d db)")
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection, join_transaction_mode="create_savepoint"
        ) as db_session:
            yield db_session
        transaction.rollback()


def make_document(filename: str) -> Document:
    return Document(
        filename=filename,
        content_type="application/pdf",
        size_bytes=1234,
        checksum="a" * 64,
        storage_key=f"uploads/{filename}",
    )


def test_new_rows_get_sensible_defaults(session: Session) -> None:
    batch = Batch(name="March invoices")
    batch.documents = [make_document("INV-1.pdf"), make_document("PO-1.pdf")]
    job = Job(kind="process_document", payload={"document_id": 1})
    session.add_all([batch, job])
    session.flush()
    session.refresh(batch)
    session.refresh(job)

    assert len(batch.documents) == 2
    document = batch.documents[0]
    assert document.status is DocumentStatus.UPLOADED
    assert document.doc_type is DocumentType.UNKNOWN
    assert document.created_at is not None
    assert job.status is JobStatus.QUEUED
    assert job.attempts == 0
    assert job.max_attempts == 3
    assert job.run_after is not None


def test_deleting_a_batch_deletes_its_documents(session: Session) -> None:
    batch = Batch(name="To be deleted")
    batch.documents = [make_document("INV-2.pdf"), make_document("INV-3.pdf")]
    session.add(batch)
    session.flush()
    batch_id = batch.id

    # Forget the loaded documents, so the database's ON DELETE CASCADE does the work.
    session.expunge_all()
    session.delete(session.get(Batch, batch_id))
    session.flush()

    remaining = session.scalar(
        select(func.count()).select_from(Document).where(Document.batch_id == batch_id)
    )
    assert remaining == 0
