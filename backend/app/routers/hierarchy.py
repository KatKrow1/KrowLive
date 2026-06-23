"""Hierarchy navigation API — countries → states → companies."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.db import get_supabase
from app.repositories.hierarchy import HierarchyRepository
from app.schemas import CompanySummaryResponse, CountryResponse, StateResponse
from app.services.company_mapper import row_to_company
from app.services.hierarchy_service import HierarchyService
from app.utils.ids import is_country_code, is_numeric_id, parse_numeric_id

logger = logging.getLogger("krowlive.hierarchy")

router = APIRouter(tags=["hierarchy"])


def _resolve_country_id(country_key: str) -> int:
    repo = HierarchyRepository(get_supabase())
    if is_numeric_id(country_key):
        country_id = parse_numeric_id(country_key)
        if not repo.get_country_by_id(country_id):
            raise HTTPException(status_code=404, detail="Country not found")
        return country_id
    if is_country_code(country_key):
        row = repo.get_country_by_code(country_key)
        if not row:
            raise HTTPException(status_code=404, detail="Country not found")
        return row["id"]
    raise HTTPException(status_code=404, detail="Country not found")


@router.get("/countries", response_model=list[CountryResponse])
def list_countries():
    try:
        return HierarchyService(get_supabase()).list_countries()
    except Exception as exc:
        logger.exception("Failed to list countries")
        raise HTTPException(status_code=500, detail=f"Could not list countries: {exc}") from exc


@router.get("/countries/{country_id}/states", response_model=list[StateResponse])
def list_states(country_id: str):
    try:
        resolved = _resolve_country_id(country_id)
        return HierarchyService(get_supabase()).list_states_for_country(resolved)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list states for %s", country_id)
        raise HTTPException(status_code=500, detail=f"Could not list states: {exc}") from exc


@router.get("/states/{state_id}/companies", response_model=list[CompanySummaryResponse])
def list_companies_in_state(state_id: str):
    try:
        if not is_numeric_id(state_id):
            raise HTTPException(status_code=404, detail="State not found")
        resolved = parse_numeric_id(state_id)
        db = get_supabase()
        repo = HierarchyRepository(db)
        if not repo.get_state_by_id(resolved):
            raise HTTPException(status_code=404, detail="State not found")
        return HierarchyService(db).list_companies_for_state(resolved)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list companies for state %s", state_id)
        raise HTTPException(status_code=500, detail=f"Could not list companies: {exc}") from exc
