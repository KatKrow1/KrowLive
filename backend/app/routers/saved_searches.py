"""Saved search CRUD and incremental discovery runs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.connectors.google_places import place_result_to_company_dict, search_places
from app.db import get_supabase
from app.repositories.companies import CompanyRepository
from app.schemas import (
    CompanySummaryResponse,
    DiscoveryRequest,
    SavedSearchCreate,
    SavedSearchResponse,
    SavedSearchRunResponse,
)
from app.services.company_pipeline import process_company_record
from app.utils.url import canonical_website
from app.tasks.discovery import _resolve_city_targets

logger = logging.getLogger("krowlive.saved_searches")

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


def _row_to_response(row: dict) -> SavedSearchResponse:
    return SavedSearchResponse(
        id=row["id"],
        name=row["name"],
        industry=row["industry"],
        country=row["country"],
        states=row.get("states") or [],
        cities=row.get("cities") or [],
        max_results=row.get("max_results", 5),
        created_at=row.get("created_at"),
        last_run_at=row.get("last_run_at"),
        last_result_count=row.get("last_result_count", 0),
    )


@router.post("", response_model=SavedSearchResponse)
def create_saved_search(body: SavedSearchCreate):
    payload = {
        "name": body.name.strip(),
        "industry": body.industry.strip(),
        "country": body.country,
        "states": body.states,
        "cities": body.cities,
        "max_results": body.max_results,
    }
    result = get_supabase().table("saved_searches").insert(payload).execute()
    row = (result.data or [None])[0]
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create saved search")
    return _row_to_response(row)


@router.get("", response_model=list[SavedSearchResponse])
def list_saved_searches():
    rows = (
        get_supabase()
        .table("saved_searches")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    return [_row_to_response(r) for r in rows]


@router.delete("/{search_id}")
def delete_saved_search(search_id: str):
    get_supabase().table("saved_searches").delete().eq("id", search_id).execute()
    return {"deleted": search_id}


@router.post("/{search_id}/run", response_model=SavedSearchRunResponse)
def run_saved_search(search_id: str):
    db = get_supabase()
    rows = db.table("saved_searches").select("*").eq("id", search_id).limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Saved search not found")
    saved = rows[0]

    company_repo = CompanyRepository(db)
    known_before = company_repo.snapshot_websites()

    request = DiscoveryRequest(
        industry=saved["industry"],
        country=saved["country"],
        states=saved.get("states") or [],
        cities=saved.get("cities") or [],
        max_results=saved.get("max_results", 5),
    )
    targets = _resolve_city_targets(request)
    processed = 0
    new_websites: set[str] = set()

    for target in targets:
        try:
            places = search_places(
                industry=request.industry,
                city=target["city"],
                state=target["state"],
                country=target["country"],
                max_results=request.max_results,
            )
        except Exception as exc:
            logger.warning("Saved search Places error: %s", exc)
            continue

        for place in places:
            company = place_result_to_company_dict(place, request.industry)
            website_key = canonical_website(company.get("website", ""))
            was_known = website_key in known_before
            is_new, ok = process_company_record(db, company, source="google_places")
            processed += 1
            if ok and (is_new or not was_known):
                new_websites.add(website_key)
                known_before.add(website_key)

    new_companies_raw = company_repo.companies_by_websites(new_websites)
    new_companies = [
        CompanySummaryResponse(
            id=r["id"],
            name=r["name"],
            website=r.get("website"),
        )
        for r in new_companies_raw
    ]

    now = datetime.now(timezone.utc).isoformat()
    db.table("saved_searches").update(
        {"last_run_at": now, "last_result_count": len(new_companies)}
    ).eq("id", search_id).execute()

    return SavedSearchRunResponse(
        saved_search_id=search_id,
        new_companies=new_companies,
        new_count=len(new_companies),
        total_processed=processed,
    )
