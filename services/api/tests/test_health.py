import pytest
from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def test_health_when_database_is_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "check_database", lambda: True)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_when_database_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "check_database", lambda: False)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "error"}
