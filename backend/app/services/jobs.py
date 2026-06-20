"""Job row helpers — single-row progress tracker for discovery / upload."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import Client

logger = logging.getLogger("krowlive.jobs")

RUNNING_STATUS = "running"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_job_status(status: Any) -> str:
    if status is None:
        return "idle"
    return str(status).lower().strip()


def get_job_row(db: Client) -> dict[str, Any] | None:
    """Return the single canonical jobs row (oldest by id — the seeded tracker)."""
    response = (
        db.table("jobs")
        .select("*")
        .order("id", desc=False)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def is_job_running(db: Client) -> bool:
    """True only when the canonical job row has status = 'running'."""
    job = get_job_row(db)
    if not job:
        return False
    return normalize_job_status(job.get("status")) == RUNNING_STATUS


def get_latest_job(db: Client) -> dict[str, Any] | None:
    """Most recently touched job row (for /status display)."""
    response = (
        db.table("jobs")
        .select("*")
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


get_active_job = get_latest_job


def update_job(db: Client, **fields: Any) -> dict[str, Any] | None:
    try:
        job = get_job_row(db)
        if not job:
            inserted = (
                db.table("jobs")
                .insert({"job_type": fields.get("job_type", "discovery"), "status": "idle", "message": "Ready"})
                .execute()
            )
            job = inserted.data[0]

        fields = {**fields, "updated_at": _now_iso()}
        updated = db.table("jobs").update(fields).eq("id", job["id"]).execute()
        return updated.data[0] if updated.data else job
    except Exception as exc:
        logger.exception("Failed to update job row")
        raise RuntimeError(f"Job status update failed: {exc}") from exc


def start_job(db: Client, job_type: str, total_items: int, message: str) -> dict[str, Any]:
    return update_job(
        db,
        job_type=job_type,
        status=RUNNING_STATUS,
        progress=0,
        message=message,
        total_items=total_items,
        processed_items=0,
        error=None,
        started_at=_now_iso(),
        completed_at=None,
    )


def finish_job(db: Client, *, success: bool, message: str, error: str | None = None) -> dict[str, Any] | None:
    job = get_job_row(db)
    current_progress = job.get("progress", 0) if job else 0
    return update_job(
        db,
        status="completed" if success else "failed",
        progress=100 if success else current_progress,
        message=message,
        error=error,
        completed_at=_now_iso(),
    )


def fail_job(db: Client, message: str, error: str) -> None:
    """Always mark the job failed — safe to call from except/finally blocks."""
    try:
        finish_job(db, success=False, message=message, error=error)
    except Exception:
        logger.exception("Could not mark job as failed: %s", error)
