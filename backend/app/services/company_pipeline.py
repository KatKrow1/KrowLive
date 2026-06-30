"""Update company_pipeline with provenance, lead status, rescrape."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from postgrest.exceptions import APIError
from supabase import Client

from app.repositories.companies import CompanyRepository
from app.repositories.hierarchy import HierarchyRepository
from app.connectors.website_intelligence import WebsiteIntelResult, scrape_website_sync
from app.enrichment import enrich_company
from app.services.webhooks import notify_new_company
from app.supabase_retry import supabase_write_retry

from app.utils.url import canonical_website

logger = logging.getLogger("krowlive.pipeline")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_signals(company: dict[str, Any], intel: WebsiteIntelResult) -> dict[str, Any]:
    executives = [
        {"name": e.name, "title": e.title, "email": e.email, "phone": e.phone}
        for e in intel.executives
    ]
    phones = list(intel.phones)
    if company.get("phone") and company["phone"] not in phones:
        phones.insert(0, company["phone"])

    return {
        "name": company.get("name"),
        "category": company.get("category"),
        "website": company.get("website"),
        "phone": company.get("phone"),
        "emails": intel.emails,
        "phones": phones,
        "executives": executives,
        "site_active": bool(intel.success and intel.pages_scraped),
        "google_rating": company.get("google_rating"),
        "social_links": intel.social_links,
        "page_texts": intel.page_texts,
        "page_urls": intel.pages_scraped,
    }


def _company_source_url(intel: WebsiteIntelResult, website_key: str) -> str | None:
    if intel.pages_scraped:
        return intel.pages_scraped[0]
    return website_key if intel.success else None


def _upsert_company(db: Client, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Upsert with graceful fallback if optional columns are not migrated yet."""
    optional_columns = (
        "tech_stack_signals",
        "social_links",
        "country_id",
        "state_id",
        "last_scraped_at",
        "source_url",
    )
    attempt = dict(payload)
    for _ in range(len(optional_columns) + 1):
        try:
            result = supabase_write_retry(
                lambda: db.table("companies").upsert(attempt, on_conflict="website").execute(),
                operation=f"upsert company {attempt.get('website', '')}",
            )
            if result.data:
                return result.data[0]
            return None
        except APIError as exc:
            message = str(exc)
            dropped = False
            for col in optional_columns:
                if col in message and col in attempt:
                    attempt.pop(col)
                    dropped = True
                    logger.warning("Column %s missing — upserting without it", col)
                    break
            if not dropped:
                raise
    return None


def _insert_executives(
    db: Client,
    company_id: str,
    intel: WebsiteIntelResult,
    *,
    scraped_at: str,
) -> None:
    supabase_write_retry(
        lambda: db.table("executives").delete().eq("company_id", company_id).execute(),
        operation=f"delete executives for {company_id}",
    )

    exec_rows: list[dict[str, Any]] = [
        {
            "company_id": company_id,
            "name": exec_contact.name,
            "title": exec_contact.title,
            "email": exec_contact.email,
            "phone": exec_contact.phone,
            "linkedin_url": exec_contact.linkedin_url,
            "consent_status": exec_contact.consent_status,
            "extraction_confidence": exec_contact.extraction_confidence,
            "source_url": exec_contact.source_page,
            "scraped_at": scraped_at,
        }
        for exec_contact in intel.executives
    ]

    if not exec_rows:
        return

    optional_exec_cols = ("extraction_confidence", "source_url", "scraped_at")
    attempt = [dict(r) for r in exec_rows]
    for _ in range(len(optional_exec_cols) + 1):
        try:
            supabase_write_retry(
                lambda rows=attempt: db.table("executives").insert(rows).execute(),
                operation=f"insert executives for {company_id}",
            )
            return
        except Exception as exc:
            message = str(exc)
            dropped = False
            for col in optional_exec_cols:
                if col in message:
                    for row in attempt:
                        row.pop(col, None)
                    dropped = True
                    break
            if not dropped:
                raise


def process_company_record(
    db: Client,
    company: dict[str, Any],
    *,
    source: str = "google_places",
    fire_webhooks: bool = True,
) -> tuple[bool, bool]:
    """Scrape, enrich, and upsert one company. Returns (is_new, success). Never raises."""
    website = company.get("website")
    if not website:
        logger.warning("Skipping company with no website: %s", company.get("name"))
        return False, False

    try:
        website_key = canonical_website(website)
        company["website"] = website_key
        company["source"] = source

        existing = db.table("companies").select("id").eq("website", website_key).limit(1).execute()
        is_new = not (existing.data or [])

        intel = scrape_website_sync(website_key, max_pages=4)
        signals = _build_signals(company, intel)
        enriched = enrich_company(signals)
        scraped_at = _utc_now()

        if not company.get("phone") and intel.phones:
            company["phone"] = intel.phones[0]

        country_code = str(company.get("country", "CA"))
        state_name = company.get("state") or "Unknown"

        payload = {
            **{
                k: v
                for k, v in company.items()
                if k not in {"id", "executives", "category", "category_id"}
            },
            "summary": enriched["summary"],
            "lead_score": enriched["lead_score"],
            "tech_stack_signals": enriched.get("tech_stack_signals") or [],
            "social_links": intel.social_links or {},
            "last_scraped_at": scraped_at,
            "source_url": _company_source_url(intel, website_key),
        }

        repo = HierarchyRepository(db)
        country_row, state_row = repo.resolve_hierarchy(
            country_code=country_code,
            state_name=state_name,
        )
        payload["country"] = country_row["code"]
        payload["state"] = state_row["name"]
        payload["country_id"] = country_row["id"]
        payload["state_id"] = state_row["id"]

        row = _upsert_company(db, payload)
        if not row:
            logger.error("Upsert returned no data for %s", website_key)
            return is_new, False

        company_id = row["id"]
        _insert_executives(db, company_id, intel, scraped_at=scraped_at)

        company_repo = CompanyRepository(db)
        if is_new:
            company_repo.ensure_lead_status(company_id, status="new")
            if fire_webhooks:
                notify_new_company(db, row)
        else:
            company_repo.ensure_lead_status(company_id)

        return is_new, True
    except Exception as exc:
        logger.exception("Failed to process company %s: %s", company.get("name"), exc)
        return False, False


def rescrape_company(db: Client, company_id: str) -> dict[str, Any] | None:
    """Re-scrape and enrich a single company — no discovery job machinery."""
    from app.services.company_mapper import COMPANY_DETAIL_SELECT, row_to_company

    row = (
        db.table("companies")
        .select(COMPANY_DETAIL_SELECT)
        .eq("id", company_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not row:
        return None

    company = dict(row[0])
    website = company.get("website")
    if not website:
        return None

    intel = scrape_website_sync(website, max_pages=4)
    signals = _build_signals(company, intel)
    enriched = enrich_company(signals)
    scraped_at = _utc_now()

    update_payload: dict[str, Any] = {
        "summary": enriched["summary"],
        "lead_score": enriched["lead_score"],
        "tech_stack_signals": enriched.get("tech_stack_signals") or [],
        "social_links": intel.social_links or {},
        "last_scraped_at": scraped_at,
        "source_url": _company_source_url(intel, website),
    }
    if not company.get("phone") and intel.phones:
        update_payload["phone"] = intel.phones[0]

    optional = ("last_scraped_at", "source_url", "tech_stack_signals", "social_links")
    attempt = dict(update_payload)
    for _ in range(len(optional) + 1):
        try:
            db.table("companies").update(attempt).eq("id", company_id).execute()
            break
        except APIError as exc:
            dropped = False
            for col in optional:
                if col in str(exc) and col in attempt:
                    attempt.pop(col)
                    dropped = True
                    break
            if not dropped:
                raise

    _insert_executives(db, company_id, intel, scraped_at=scraped_at)

    refreshed = (
        db.table("companies")
        .select(COMPANY_DETAIL_SELECT)
        .eq("id", company_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not refreshed:
        return None
    mapped = row_to_company(refreshed[0])
    status = CompanyRepository(db).get_lead_status(company_id)
    return {"company": mapped, "executives": mapped.executives, "lead_status": status}
