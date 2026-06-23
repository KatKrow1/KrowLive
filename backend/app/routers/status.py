"""Job status endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.db import get_supabase
from app.schemas import JobStatusResponse
from app.services.jobs import get_active_job

logger = logging.getLogger("krowlive.status")

router = APIRouter(tags=["status"])


@router.get("/status", response_model=JobStatusResponse)
def get_status():
    try:
        db = get_supabase()
        job = get_active_job(db)
        if not job:
            return JobStatusResponse(status="idle", message="Ready", progress=0)
        return JobStatusResponse(
            id=job.get("id"),
            job_type=job.get("job_type", "discovery"),
            status=job.get("status", "idle"),
            progress=job.get("progress", 0),
            message=job.get("message"),
            total_items=job.get("total_items", 0),
            processed_items=job.get("processed_items", 0),
            error=job.get("error"),
            started_at=job.get("started_at"),
            completed_at=job.get("completed_at"),
        )
    except Exception as exc:
        logger.exception("Failed to fetch job status")
        raise HTTPException(status_code=500, detail=f"Could not fetch status: {exc}") from exc
