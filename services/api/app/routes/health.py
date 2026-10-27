"""Health check route."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.db import check_database

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ok", "error"]


@router.get("/health")
def health() -> HealthResponse:
    """Report whether the API is running and can reach the database."""
    database = "ok" if check_database() else "error"
    return HealthResponse(status="ok", database=database)
