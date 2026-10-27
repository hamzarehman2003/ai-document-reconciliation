"""Shared base class for all database models."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Predictable names for constraints and indexes, so migrations stay readable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def text_enum(enum: type[StrEnum]) -> Enum:
    """Store an enum as plain text (its values), not as a Postgres enum type.

    Plain text means adding a new status later needs no special migration.
    """
    return Enum(
        enum,
        native_enum=False,
        length=30,
        values_callable=lambda members: [member.value for member in members],
    )


class TimestampMixin:
    """Adds created_at and updated_at columns, filled in by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
