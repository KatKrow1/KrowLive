"""Company export, lead status, and re-scrape endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.db import get_supabase
from app.repositories.companies import CompanyRepository
from app.repositories.hierarchy import HierarchyRepository
from app.schemas import (
    BulkLeadStatusUpdate,
    CompanyDetailResponse,
    Executive,
    LeadStatusUpdate,
    LeadStatusValue,
)
from app.services.company_mapper import row_to_company
from app.services.company_pipeline import rescrape_company

logger = logging.getLogger("krowlive.companies")

router = APIRouter(tags=["companies"])


@router.get("/companies/export")
def export_companies_csv(
    format: str = Query(default="csv", pattern="^csv$"),
    country: str | None = None,
    state: str | None = None,
    state_id: int | None = None,
    industry: str | None = None,
    min_score: int | None = None,
    status: LeadStatusValue | None = None,
):
    try:
        repo = CompanyRepository(get_supabase())
        csv_data = repo.export_csv(
            country=country,
            state=state,
            state_id=state_id,
            industry=industry,
            min_score=min_score,
            status=status,
        )
        filename = "krowlive-companies.csv"
        return StreamingResponse(
            iter([csv_data]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.exception("CSV export failed")
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse)
def get_company(company_id: str):
    try:
        if not company_id.strip():
            raise HTTPException(status_code=404, detail="Company not found")
        db = get_supabase()
        row = HierarchyRepository(db).get_company(company_id)
        if not row:
            raise HTTPException(status_code=404, detail="Company not found")

        company = row_to_company(dict(row))
        lead_status = CompanyRepository(db).get_lead_status(company_id)
        company.lead_status = lead_status  # type: ignore[assignment]
        executives = [
            Executive(
                id=e.id,
                company_id=e.company_id,
                name=e.name,
                title=e.title,
                email=e.email,
                phone=e.phone,
                linkedin_url=e.linkedin_url,
                consent_status=e.consent_status,
                extraction_confidence=e.extraction_confidence,
                source_url=e.source_url,
                scraped_at=e.scraped_at,
            )
            for e in company.executives
        ]
        company.executives = []
        return CompanyDetailResponse(company=company, executives=executives)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to fetch company %s", company_id)
        raise HTTPException(status_code=500, detail=f"Could not fetch company: {exc}") from exc


@router.get("/companies/{company_id}/status")
def get_company_status(company_id: str):
    db = get_supabase()
    if not HierarchyRepository(db).get_company(company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    return {"company_id": company_id, "status": CompanyRepository(db).get_lead_status(company_id)}


@router.patch("/companies/{company_id}/status")
def update_company_status(company_id: str, body: LeadStatusUpdate):
    db = get_supabase()
    if not HierarchyRepository(db).get_company(company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    CompanyRepository(db).set_lead_status(company_id, body.status)
    return {"company_id": company_id, "status": body.status}


@router.patch("/companies/status/bulk")
def bulk_update_status(body: BulkLeadStatusUpdate):
    db = get_supabase()
    updated = CompanyRepository(db).bulk_set_lead_status(body.company_ids, body.status)
    return {"updated": updated, "status": body.status}


@router.post("/companies/{company_id}/rescrape", response_model=CompanyDetailResponse)
def rescrape_single_company(company_id: str):
    try:
        result = rescrape_company(get_supabase(), company_id)
        if not result:
            raise HTTPException(status_code=404, detail="Company not found or has no website")
        company = result["company"]
        company.lead_status = result.get("lead_status", "new")  # type: ignore[assignment]
        return CompanyDetailResponse(company=company, executives=result["executives"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Re-scrape failed for %s", company_id)
        raise HTTPException(status_code=500, detail=f"Re-scrape failed: {exc}") from exc
