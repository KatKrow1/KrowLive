"""Shared pipeline: scrape website -> enrich -> upsert company + executives."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from postgrest.exceptions import APIError
from supabase import Client

from app.connectors.website_intelligence import WebsiteIntelResult, scrape_website_sync
from app.enrichment import enrich_company
from app.supabase_retry import supabase_write_retry

logger = logging.getLogger("krowlive.pipeline")


def canonical_website(url: str) -> str:
    parsed = urlparse(url.strip().split("?")[0].split("#")[0])
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.replace("www.", "").lower()
    path = parsed.path.rstrip("/")
    return f"{scheme}://{netloc}{path}"


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


def _upsert_company(db: Client, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Upsert with graceful fallback if optional columns are not migrated yet."""
    optional_columns = ("tech_stack_signals", "social_links")
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


def process_company_record(
    db: Client,
    company: dict[str, Any],
    *,
    source: str = "google_places",
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

        if not company.get("phone") and intel.phones:
            company["phone"] = intel.phones[0]

        payload = {
            **{k: v for k, v in company.items() if k not in {"id", "executives"}},
            "summary": enriched["summary"],
            "lead_score": enriched["lead_score"],
            "tech_stack_signals": enriched.get("tech_stack_signals") or [],
            "social_links": intel.social_links or {},
        }

        row = _upsert_company(db, payload)
        if not row:
            logger.error("Upsert returned no data for %s", website_key)
            return is_new, False

        company_id = row["id"]
        supabase_write_retry(
            lambda: db.table("executives").delete().eq("company_id", company_id).execute(),
            operation=f"delete executives for {website_key}",
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
            }
            for exec_contact in intel.executives
        ]

        if exec_rows:
            try:
                supabase_write_retry(
                    lambda rows=exec_rows: db.table("executives").insert(rows).execute(),
                    operation=f"insert executives for {website_key}",
                )
            except Exception as exc:
                if "extraction_confidence" in str(exc):
                    for row in exec_rows:
                        row.pop("extraction_confidence", None)
                    supabase_write_retry(
                        lambda rows=exec_rows: db.table("executives").insert(rows).execute(),
                        operation=f"insert executives for {website_key}",
                    )
                else:
                    raise

        return is_new, True
    except Exception as exc:
        logger.exception("Failed to process company %s: %s", company.get("name"), exc)
        return False, False
