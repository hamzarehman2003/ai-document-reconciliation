"""Response shape for background jobs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import JobStatus


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    payload: dict[str, Any]
    status: JobStatus
    attempts: int
    max_attempts: int
    run_after: datetime
    locked_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
