"""FastAPI application entry point."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.db import check_database

app = FastAPI(title="InvoiceIQ API", version="0.1.0")


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ok", "error"]


@app.get("/api/health")
def health() -> HealthResponse:
    """Report whether the API is running and can reach the database."""
    database = "ok" if check_database() else "error"
    return HealthResponse(status="ok", database=database)
