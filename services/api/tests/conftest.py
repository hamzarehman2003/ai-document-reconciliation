"""Shared test fixtures.

Database tests need Postgres running and `alembic upgrade head` applied.
Every test runs inside a transaction that is rolled back at the end, and
uploads go to a temporary folder, so nothing is left behind.
"""

from collections.abc import Callable, Iterator
from pathlib import Path
from uuid import uuid4

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import check_database, engine, get_session
from app.main import app
from app.storage import LocalStorage, get_storage
from fakes import FakeExtractor


@pytest.fixture(autouse=True)
def fake_extractor(monkeypatch: pytest.MonkeyPatch) -> FakeExtractor:
    """Used by every test automatically, so tests never call the real AI."""
    fake = FakeExtractor()
    monkeypatch.setattr("app.services.extraction.get_extractor", lambda: fake)
    return fake


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


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "uploads")


@pytest.fixture
def client(session: Session, storage: LocalStorage) -> Iterator[TestClient]:
    """An API client that uses the test session and temporary storage."""
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_pdf() -> Callable[[], bytes]:
    """Return a function that builds a small, unique one-page PDF."""

    def build() -> bytes:
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((72, 72), f"Test invoice {uuid4()}")
            return pdf.tobytes()

    return build
