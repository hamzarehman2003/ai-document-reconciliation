"""Database connection."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3},
)

# Creates database sessions (one unit of work: read, change, commit).
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Give each request its own session, closed automatically afterwards."""
    with SessionLocal() as session:
        yield session


# Use in a route as `session: SessionDep` to receive a session.
SessionDep = Annotated[Session, Depends(get_session)]


def check_database() -> bool:
    """Return True if the database answers a simple query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True
