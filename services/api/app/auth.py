"""Who is calling: checks the Supabase login token sent with each request.

Supabase signs each token with its private key. We check the signature with the
project's public keys (downloaded once and cached), so the API needs no secret.
The web app's proxy puts the token in the `Authorization: Bearer ...` header.
"""

from functools import lru_cache
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.audit import Actor

AUDIENCE = "authenticated"  # Supabase puts this in the tokens of signed-in users
ALGORITHMS = ["ES256", "RS256"]


class User(BaseModel):
    id: UUID
    email: str
    name: str

    @property
    def actor(self) -> Actor:
        return Actor(name=self.name, user_id=self.id)


@lru_cache
def _public_keys() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")


def signing_key(token: str) -> Any:
    """The public key the token says it was signed with (tests replace this)."""
    return _public_keys().get_signing_key_from_jwt(token).key


def user_from_token(token: str) -> User:
    """Raise jwt.PyJWTError if the token is forged, expired or not for us."""
    claims = jwt.decode(
        token,
        signing_key(token),
        algorithms=ALGORITHMS,
        audience=AUDIENCE,
        issuer=f"{settings.supabase_url}/auth/v1",
        options={"require": ["exp", "sub"]},
    )
    email = claims.get("email") or ""
    metadata = claims.get("user_metadata") or {}
    name = metadata.get("full_name") or email.split("@")[0] or "Unknown user"
    return User(id=UUID(claims["sub"]), email=email, name=name[:100])


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not settings.supabase_url:
        raise HTTPException(503, "Login is not set up: SUPABASE_URL is missing.")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _not_logged_in("Please log in.")
    try:
        return user_from_token(token)
    except jwt.PyJWKClientConnectionError as error:
        raise HTTPException(503, "Can't reach the login service.") from error
    except (jwt.PyJWTError, ValueError) as error:
        raise _not_logged_in("Your login is not valid or has expired.") from error


def _not_logged_in(message: str) -> HTTPException:
    return HTTPException(401, message, headers={"WWW-Authenticate": "Bearer"})


CurrentUserDep = Annotated[User, Depends(get_current_user)]
