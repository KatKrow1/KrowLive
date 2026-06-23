"""Dashboard stats from normalized hierarchy tables."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.db import get_supabase
from app.services.hierarchy_service import HierarchyService

logger = logging.getLogger("krowlive.stats")

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(country: str | None = Query(None, pattern="^(CA|AU)$")):
    try:
        return HierarchyService(get_supabase()).dashboard_stats(country)
    except Exception as exc:
        logger.exception("Failed to fetch stats")
        raise HTTPException(status_code=500, detail=f"Could not fetch stats: {exc}") from exc
