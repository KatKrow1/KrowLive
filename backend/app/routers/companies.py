"""Single company detail endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.db import get_supabase
from app.repositories.hierarchy import HierarchyRepository
from app.schemas import CompanyDetailResponse, Executive
from app.services.company_mapper import row_to_company

logger = logging.getLogger("krowlive.companies")

router = APIRouter(tags=["companies"])


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse)
def get_company(company_id: str):
    try:
        if not company_id.strip():
            raise HTTPException(status_code=404, detail="Company not found")
        row = HierarchyRepository(get_supabase()).get_company(company_id)
        if not row:
            raise HTTPException(status_code=404, detail="Company not found")

        company = row_to_company(dict(row))
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
