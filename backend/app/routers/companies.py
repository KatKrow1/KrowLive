"""Company listing and detail endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db import get_supabase
from app.schemas import Company, CompanyListResponse, Executive, SocialLinks

logger = logging.getLogger("krowlive.companies")

router = APIRouter(prefix="/companies", tags=["companies"])


def _parse_social_links(raw: Any) -> SocialLinks:
    if not raw or not isinstance(raw, dict):
        return SocialLinks()
    return SocialLinks(
        linkedin=raw.get("linkedin"),
        twitter=raw.get("twitter"),
        instagram=raw.get("instagram"),
        facebook=raw.get("facebook"),
    )


def _row_to_company(row: dict[str, Any]) -> Company:
    data = dict(row)
    execs = data.pop("executives", []) or []
    social = _parse_social_links(data.get("social_links"))
    signals = data.get("tech_stack_signals") or []
    if not isinstance(signals, list):
        signals = []
    return Company(
        **{k: v for k, v in data.items() if k not in {"social_links", "tech_stack_signals"}},
        social_links=social,
        tech_stack_signals=[str(s) for s in signals],
        executives=[
            Executive(
                id=e.get("id"),
                company_id=e.get("company_id"),
                name=e.get("name"),
                title=e.get("title"),
                email=e.get("email"),
                phone=e.get("phone"),
                linkedin_url=e.get("linkedin_url"),
                consent_status=e.get("consent_status", "unknown"),
            )
            for e in execs
        ],
    )


@router.get("", response_model=CompanyListResponse)
def list_companies(
    industry: str | None = None,
    country: str | None = Query(None, pattern="^(CA|AU)$"),
    state: str | None = None,
    city: str | None = None,
    search: str | None = None,
    min_score: int | None = Query(None, ge=0, le=100),
    source: str | None = Query(None, pattern="^(google_places|csv_upload)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        db = get_supabase()
        query = db.table("companies").select("*, executives(*)", count="exact")

        if industry:
            query = query.ilike("category", f"%{industry}%")
        if country:
            query = query.eq("country", country)
        if state:
            query = query.ilike("state", f"%{state}%")
        if city:
            query = query.ilike("city", f"%{city}%")
        if search:
            query = query.ilike("name", f"%{search}%")
        if min_score is not None:
            query = query.gte("lead_score", min_score)
        if source:
            query = query.eq("source", source)

        start = (page - 1) * page_size
        end = start + page_size - 1
        response = query.order("lead_score", desc=True).order("updated_at", desc=True).range(start, end).execute()

        items = [_row_to_company(dict(row)) for row in (response.data or [])]
        return CompanyListResponse(
            items=items,
            total=response.count or len(items),
            page=page,
            page_size=page_size,
        )
    except Exception as exc:
        logger.exception("Failed to list companies")
        raise HTTPException(status_code=500, detail=f"Could not list companies: {exc}") from exc


@router.get("/stats")
def company_stats(country: str | None = Query(None, pattern="^(CA|AU)$")):
    try:
        db = get_supabase()
        query = db.table("companies").select("id, lead_score, country, category, state", count="exact")
        if country:
            query = query.eq("country", country)
        response = query.execute()
        rows = response.data or []
        total = response.count or len(rows)

        scores = [r["lead_score"] for r in rows if r.get("lead_score") is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0

        ca_count = sum(1 for r in rows if r.get("country") == "CA")
        au_count = sum(1 for r in rows if r.get("country") == "AU")

        categories: dict[str, int] = {}
        for row in rows:
            cat = row.get("category") or "Unknown"
            categories[cat] = categories.get(cat, 0) + 1
        top_industry = max(categories, key=categories.get) if categories else "N/A"

        return {
            "total_companies": total,
            "avg_lead_score": avg_score,
            "canada_count": ca_count,
            "australia_count": au_count,
            "top_industry": top_industry,
        }
    except Exception as exc:
        logger.exception("Failed to fetch company stats")
        raise HTTPException(status_code=500, detail=f"Could not fetch stats: {exc}") from exc


@router.get("/chart/by-state")
def chart_by_state(country: str | None = Query(None, pattern="^(CA|AU)$")):
    try:
        db = get_supabase()
        query = db.table("companies").select("state, country")
        if country:
            query = query.eq("country", country)
        rows = query.execute().data or []
        counts: dict[str, int] = {}
        for row in rows:
            label = row.get("state") or "Unknown"
            counts[label] = counts.get(label, 0) + 1
        return [{"state": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
    except Exception as exc:
        logger.exception("Failed to build chart data")
        raise HTTPException(status_code=500, detail=f"Could not build chart: {exc}") from exc
