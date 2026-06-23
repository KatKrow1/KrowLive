"""CSV upload endpoint — admin-only refresh of manually collected datasets.

NOT a customer-facing feature. Used to re-upload the same CSV so existing
companies (matched on the unique `website` column) get fresh scraped signals
and re-enrichment without creating duplicates.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, File, UploadFile

from app.connectors.csv_importer import import_csv
from app.db import get_supabase
from app.schemas import CsvUploadResult
from app.services.jobs import fail_job, finish_job, is_job_running, start_job, update_job

router = APIRouter(prefix="/upload", tags=["upload"])

_upload_result: CsvUploadResult | None = None


def _run_csv_upload(file_bytes: bytes) -> None:
    global _upload_result
    db = get_supabase()
    try:
        start_job(db, "csv_upload", 1, "Processing CSV upload")
        _upload_result = import_csv(db, file_bytes)
        finish_job(
            db,
            success=True,
            message=(
                f"CSV complete — {_upload_result.rows_new} new, "
                f"{_upload_result.rows_updated} updated, "
                f"{len(_upload_result.errors)} errors"
            ),
            error="; ".join(_upload_result.errors[:5]) if _upload_result.errors else None,
        )
        update_job(db, progress=100, processed_items=_upload_result.rows_processed)
    except Exception as exc:
        _upload_result = CsvUploadResult(errors=[str(exc)])
        fail_job(db, "CSV upload failed", str(exc))


@router.post("/csv", response_model=CsvUploadResult)
async def upload_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    db = get_supabase()
    if is_job_running(db):
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail="A job is already running")

    file_bytes = await file.read()
    background_tasks.add_task(_run_csv_upload, file_bytes)
    return CsvUploadResult(rows_processed=0, rows_new=0, rows_updated=0, errors=[])


@router.get("/csv/last", response_model=CsvUploadResult)
def last_csv_result():
    return _upload_result or CsvUploadResult()
