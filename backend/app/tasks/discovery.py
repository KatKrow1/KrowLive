"""Discovery background job — Places search, scrape, enrich, upsert."""

from __future__ import annotations

import logging
import traceback

from app.connectors.google_places import place_result_to_company_dict, search_places
from app.db import get_supabase
from app.schemas import DiscoveryRequest
from app.services.company_pipeline import process_company_record
from app.services.jobs import fail_job, finish_job, update_job

logger = logging.getLogger("krowlive.discovery")

CA_STATE_CITIES = {
    "Ontario": ["Toronto", "Ottawa"],
    "British Columbia": ["Vancouver"],
    "Quebec": ["Montreal"],
    "Alberta": ["Calgary"],
    "Manitoba": ["Winnipeg"],
    "Saskatchewan": ["Saskatoon"],
    "Nova Scotia": ["Halifax"],
    "New Brunswick": ["Moncton"],
}

AU_STATE_CITIES = {
    "NSW": ["Sydney"],
    "VIC": ["Melbourne"],
    "QLD": ["Brisbane"],
    "WA": ["Perth"],
    "SA": ["Adelaide"],
    "TAS": ["Hobart"],
    "ACT": ["Canberra"],
    "NT": ["Darwin"],
}


def _resolve_city_targets(request: DiscoveryRequest) -> list[dict[str, str]]:
    mapping = CA_STATE_CITIES if request.country == "CA" else AU_STATE_CITIES
    targets: list[dict[str, str]] = []

    if request.cities and request.states:
        for city in request.cities:
            for state in request.states:
                targets.append({"city": city, "state": state, "country": request.country})
    elif request.cities:
        for city in request.cities:
            targets.append({"city": city, "state": request.states[0] if request.states else "", "country": request.country})
    elif request.states:
        for state in request.states:
            for city in mapping.get(state, []):
                targets.append({"city": city, "state": state, "country": request.country})
    else:
        for state, cities in mapping.items():
            for city in cities[:2]:
                targets.append({"city": city, "state": state, "country": request.country})

    return targets


def run_discovery_job(request: DiscoveryRequest) -> None:
    db = get_supabase()
    processed = 0
    errors: list[str] = []

    try:
        targets = _resolve_city_targets(request)
        if not targets:
            fail_job(db, "Discovery failed", "No city/state targets resolved")
            return

        estimated_total = len(targets) * request.max_results
        update_job(
            db,
            job_type="discovery",
            status="running",
            progress=0,
            message=f"Starting discovery for {request.industry}",
            total_items=estimated_total,
            processed_items=0,
            error=None,
        )

        for i, target in enumerate(targets):
            city_label = f"{target['city']}, {target['state']} ({target['country']})"
            update_job(
                db,
                message=f"Searching {request.industry} in {city_label}",
                progress=int((i / max(len(targets), 1)) * 100),
                processed_items=processed,
                total_items=estimated_total,
            )

            try:
                places = search_places(
                    industry=request.industry,
                    city=target["city"],
                    state=target["state"],
                    country=target["country"],
                    max_results=request.max_results,
                )
            except Exception as exc:
                msg = f"{city_label}: {exc}"
                logger.exception(msg)
                errors.append(msg)
                continue

            for place in places:
                company = place_result_to_company_dict(place, request.industry)
                _, ok = process_company_record(db, company, source="google_places")
                if not ok:
                    errors.append(f"{company.get('name')}: processing failed")
                processed += 1
                update_job(
                    db,
                    processed_items=processed,
                    progress=min(int((processed / max(estimated_total, 1)) * 100), 99),
                    message=f"Processing {city_label} — {company.get('name')}",
                )

        finish_job(
            db,
            success=True,
            message=f"Discovery complete — {processed} companies processed",
            error="; ".join(errors[:5]) if errors else None,
        )
        update_job(db, processed_items=processed, progress=100)
    except Exception as exc:
        logger.exception("Discovery job crashed")
        fail_job(db, "Discovery failed", f"{exc}\n{traceback.format_exc()}")
