"""Login: only valid Supabase tokens get in. A local key pair stands in for Supabase."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.auth import user_from_token
from app.config import settings
from app.main import app

PROJECT = "https://test-project.supabase.co"
PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_KEY = ec.generate_private_key(ec.SECP256R1())
USER_ID = "8c1f0000-0000-4000-8000-0000000000aa"


@pytest.fixture(autouse=True)
def supabase(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tokens are checked against our local public key instead of Supabase's."""
    monkeypatch.setattr(settings, "supabase_url", PROJECT)
    monkeypatch.setattr("app.auth.signing_key", lambda token: PRIVATE_KEY.public_key())


@pytest.fixture
def anonymous_client() -> Iterator[TestClient]:
    """A client without the signed-in test user."""
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        yield client


def make_token(key: ec.EllipticCurvePrivateKey = PRIVATE_KEY, **changes: Any) -> str:
    claims = {
        "sub": USER_ID,
        "email": "omar@example.com",
        "user_metadata": {"full_name": "Omar Haddad"},
        "aud": "authenticated",
        "iss": f"{PROJECT}/auth/v1",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    claims.update(changes)
    return jwt.encode(claims, key, algorithm="ES256")


def test_a_valid_token_gives_the_person() -> None:
    user = user_from_token(make_token())

    assert str(user.id) == USER_ID
    assert (user.email, user.name) == ("omar@example.com", "Omar Haddad")
    assert user.actor.user_id == user.id


def test_name_falls_back_to_the_email() -> None:
    user = user_from_token(make_token(user_metadata={}))

    assert user.name == "omar"


@pytest.mark.parametrize(
    "token",
    [
        make_token(exp=datetime.now(UTC) - timedelta(minutes=1)),  # expired
        make_token(aud="anon"),  # not a signed-in user
        make_token(iss="https://other.supabase.co/auth/v1"),  # another project
        make_token(key=OTHER_KEY),  # forged signature
    ],
    ids=["expired", "wrong-audience", "other-project", "forged"],
)
def test_bad_tokens_are_refused(anonymous_client: TestClient, token: str) -> None:
    response = anonymous_client.get(
        "/api/documents", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_requests_without_a_login_are_refused(anonymous_client: TestClient) -> None:
    for url in ("/api/documents", "/api/dashboard", "/api/exports/approved.csv"):
        assert anonymous_client.get(url).status_code == 401
    assert anonymous_client.get("/api/health").status_code == 200  # stays public
