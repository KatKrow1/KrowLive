"""Discovery endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.db import get_supabase
from app.schemas import DiscoveryRequest, JobStatusResponse
from app.services.jobs import is_job_running, start_job
from app.tasks.discovery import run_discovery_job

logger = logging.getLogger("krowlive.discovery")

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("/run", response_model=JobStatusResponse)
def run_discovery(request: DiscoveryRequest, background_tasks: BackgroundTasks):
    try:
        db = get_supabase()
        if is_job_running(db):
            raise HTTPException(status_code=409, detail="A job is already running")

        start_job(db, "discovery", 0, f"Discovery queued for {request.industry}")
        background_tasks.add_task(run_discovery_job, request)
        return JobStatusResponse(
            job_type="discovery",
            status="running",
            progress=0,
            message=f"Discovery queued for {request.industry}",
            total_items=0,
            processed_items=0,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to start discovery")
        raise HTTPException(status_code=500, detail=f"Could not start discovery: {exc}") from exc
