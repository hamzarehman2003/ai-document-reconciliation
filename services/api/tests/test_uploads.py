from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Batch, Document, Job, JobStatus
from app.services.uploads import detect_file_type, safe_filename
from app.storage import LocalStorage

PDF = "application/pdf"


def upload(client: TestClient, *files: tuple[str, bytes, str]) -> dict:
    response = client.post(
        "/api/batches",
        files=[("files", file) for file in files],
        data={"name": "Test batch"},
    )
    return {"status": response.status_code, "body": response.json()}


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model))


# --- Small helpers (no database needed) ---


def test_detect_file_type_uses_first_bytes() -> None:
    assert detect_file_type(b"%PDF-1.7 ...") == "application/pdf"
    assert detect_file_type(b"\x89PNG\r\n\x1a\n...") == "image/png"
    assert detect_file_type(b"\xff\xd8\xff\xe0...") == "image/jpeg"
    assert detect_file_type(b"hello, I am a text file") is None


def test_safe_filename_removes_folders_and_odd_characters() -> None:
    assert safe_filename("../../evil.pdf") == "evil.pdf"
    assert safe_filename("C:\\Users\\me\\My Invoice (1).pdf") == "My_Invoice__1_.pdf"
    assert safe_filename("...") == "file"


# --- Uploads ---


def test_upload_creates_documents_and_queued_jobs(
    client: TestClient,
    session: Session,
    storage: LocalStorage,
    make_pdf: Callable[[], bytes],
) -> None:
    result = upload(
        client, ("INV-1.pdf", make_pdf(), PDF), ("PO-1.pdf", make_pdf(), PDF)
    )

    assert result["status"] == 201
    batch = result["body"]["batch"]
    assert batch["name"] == "Test batch"
    assert batch["document_count"] == 2
    assert batch["status_counts"]["uploaded"] == 2
    assert [r["outcome"] for r in result["body"]["results"]] == ["accepted"] * 2

    document_ids = [r["document_id"] for r in result["body"]["results"]]
    jobs = session.scalars(
        select(Job).where(Job.payload["document_id"].as_integer().in_(document_ids))
    ).all()
    assert len(jobs) == 2
    assert all(job.status is JobStatus.QUEUED for job in jobs)

    for document_id in document_ids:
        document = session.get(Document, document_id)
        assert storage.path(document.storage_key).is_file()


def test_same_file_again_is_a_duplicate(
    client: TestClient, session: Session, make_pdf: Callable[[], bytes]
) -> None:
    content = make_pdf()
    first = upload(client, ("INV-1.pdf", content, PDF))
    documents_before = count(session, Document)

    second = upload(client, ("INV-1 copy.pdf", content, PDF))

    assert second["status"] == 400
    result = second["body"]["detail"]["results"][0]
    assert result["outcome"] == "duplicate"
    assert result["existing_document_id"] == first["body"]["results"][0]["document_id"]
    assert count(session, Document) == documents_before


def test_same_file_twice_in_one_upload(
    client: TestClient, make_pdf: Callable[[], bytes]
) -> None:
    content = make_pdf()
    result = upload(client, ("a.pdf", content, PDF), ("b.pdf", content, PDF))

    assert result["status"] == 201
    outcomes = [r["outcome"] for r in result["body"]["results"]]
    assert outcomes == ["accepted", "duplicate"]
    assert result["body"]["batch"]["document_count"] == 1


def test_wrong_and_fake_files_are_rejected(
    client: TestClient, make_pdf: Callable[[], bytes]
) -> None:
    result = upload(
        client,
        ("good.pdf", make_pdf(), PDF),
        ("notes.txt", b"just some text", "text/plain"),
        ("fake.pdf", b"I am text pretending to be a PDF", PDF),
        ("empty.pdf", b"", PDF),
    )

    assert result["status"] == 201
    results = result["body"]["results"]
    assert [r["outcome"] for r in results] == [
        "accepted",
        "rejected",
        "rejected",
        "rejected",
    ]
    assert results[1]["detail"] == "Only PDF, PNG or JPEG files are allowed."
    assert results[3]["detail"] == "The file is empty."


def test_too_large_file_is_rejected(
    client: TestClient, make_pdf: Callable[[], bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "max_upload_mb", 0)

    result = upload(client, ("big.pdf", make_pdf(), PDF))

    detail = result["body"]["detail"]["results"][0]["detail"]
    assert detail == "The file is larger than 0 MB."


def test_nothing_accepted_creates_no_batch(
    client: TestClient, session: Session
) -> None:
    batches_before = count(session, Batch)

    result = upload(client, ("notes.txt", b"text", "text/plain"))

    assert result["status"] == 400
    assert result["body"]["detail"]["message"] == "No files were accepted."
    assert count(session, Batch) == batches_before


def test_unsafe_filename_is_stored_inside_the_batch_folder(
    client: TestClient,
    session: Session,
    storage: LocalStorage,
    make_pdf: Callable[[], bytes],
) -> None:
    result = upload(client, ("../../evil.pdf", make_pdf(), PDF))

    document = session.get(Document, result["body"]["results"][0]["document_id"])
    assert document.filename == "evil.pdf"
    stored = storage.path(document.storage_key).resolve()
    assert stored.is_relative_to(storage.root.resolve() / "batches")


# --- Reading back ---


def test_get_batch_and_original_file(
    client: TestClient, make_pdf: Callable[[], bytes]
) -> None:
    content = make_pdf()
    created = upload(client, ("INV-9.pdf", content, PDF))
    batch_id = created["body"]["batch"]["id"]
    document_id = created["body"]["results"][0]["document_id"]

    batch = client.get(f"/api/batches/{batch_id}").json()
    assert batch["documents"][0]["filename"] == "INV-9.pdf"
    assert batch["documents"][0]["status"] == "uploaded"

    listed = client.get("/api/batches").json()
    assert listed[0]["id"] == batch_id

    document = client.get(f"/api/documents/{document_id}").json()
    assert document["content_type"] == PDF

    file_response = client.get(f"/api/documents/{document_id}/file")
    assert file_response.status_code == 200
    assert file_response.content == content


def test_unknown_ids_return_404(client: TestClient) -> None:
    assert client.get("/api/batches/999999").status_code == 404
    assert client.get("/api/documents/999999").status_code == 404
    assert client.get("/api/documents/999999/file").status_code == 404


def test_list_documents_newest_first(
    client: TestClient, make_pdf: Callable[[], bytes]
) -> None:
    first = upload(client, ("first.pdf", make_pdf(), PDF))["body"]
    second = upload(client, ("second.pdf", make_pdf(), PDF))["body"]

    listed = client.get("/api/documents", params={"limit": 2}).json()

    assert [document["filename"] for document in listed] == ["second.pdf", "first.pdf"]
    assert listed[0]["id"] == second["results"][0]["document_id"]
    assert listed[1]["id"] == first["results"][0]["document_id"]
