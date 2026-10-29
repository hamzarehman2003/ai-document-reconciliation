"""The numbers behind the dashboard screen."""

from fastapi import APIRouter

from app.db import SessionDep
from app.schemas.dashboard import Dashboard
from app.services.dashboard import build_dashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(session: SessionDep) -> Dashboard:
    """Documents, match results, money at risk, top problems, AI use, activity."""
    return build_dashboard(session)
