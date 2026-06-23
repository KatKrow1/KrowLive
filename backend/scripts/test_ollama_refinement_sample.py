"""Show before/after for 3 companies using Ollama scrape + enrich (updates DB)."""

from __future__ import annotations

import json
import os
import time

from app.connectors.website_intelligence import scrape_website_sync
from app.db import get_supabase
from app.enrichment import enrich_company, rule_based_enrichment
from app.services.company_pipeline import process_company_record
from app.services.ollama_client import field_literal_in_source

SAMPLES = [
    "https://canadacreate.com",
    "https://aspenfilms.ca/toronto-video",
    "https://marketingblendz.com",
]


def _snap(row: dict) -> dict:
    return {
        "summary": row.get("summary"),
        "tech_stack_signals": row.get("tech_stack_signals") or [],
        "executives": [
            {
                "name": e.get("name"),
                "title": e.get("title"),
                "email": e.get("email"),
                "phone": e.get("phone"),
                "linkedin_url": e.get("linkedin_url"),
                "extraction_confidence": e.get("extraction_confidence"),
            }
            for e in (row.get("executives") or [])
        ],
    }


def main() -> None:
    os.environ["ENRICHMENT_PROVIDER"] = "ollama"
    os.environ["OLLAMA_TIMEOUT_SECONDS"] = "200"

    db = get_supabase()
    for website in SAMPLES:
        rows = (
            db.table("companies")
            .select("*, executives(*)")
            .eq("website", website)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            print(f"SKIP {website}")
            continue
        company = rows[0]
        before = _snap(company)

        t0 = time.perf_counter()
        _, ok = process_company_record(
            db, dict(company), source=company.get("source") or "google_places"
        )
        elapsed = time.perf_counter() - t0

        refreshed = (
            db.table("companies")
            .select("*, executives(*)")
            .eq("id", company["id"])
            .limit(1)
            .execute()
            .data[0]
        )
        after = _snap(refreshed)

        intel = scrape_website_sync(website, max_pages=4)
        warnings: list[str] = []
        source_text = " ".join(intel.page_texts)
        for e in after["executives"]:
            for field in ("email", "phone", "linkedin_url"):
                val = e.get(field)
                if val and not field_literal_in_source(str(val), source_text):
                    warnings.append(f"{e.get('name')}.{field}={val!r}")

        signals = {
            "name": company.get("name"),
            "category": company.get("category"),
            "page_texts": intel.page_texts,
            "page_urls": intel.pages_scraped,
            "emails": intel.emails,
            "phones": intel.phones,
            "executives": after["executives"],
            "site_active": intel.success,
            "social_links": intel.social_links,
        }
        t1 = time.perf_counter()
        rule_based_enrichment(signals)
        rule_ms = (time.perf_counter() - t1) * 1000
        t2 = time.perf_counter()
        enrich_company(signals)
        ollama_s = time.perf_counter() - t2

        print("\n" + "=" * 72)
        print(f"### {company.get('name')} ({website}) — pipeline {elapsed:.0f}s")
        print("\nBEFORE:")
        print(json.dumps(before, indent=2))
        print("\nAFTER:")
        print(json.dumps(after, indent=2))
        print(f"\nTiming — rule-based: {rule_ms:.0f}ms, ollama enrich call: {ollama_s:.0f}s")
        print("Hallucination check:", warnings if warnings else "OK (no ungrounded contact fields)")
        print("DB update ok:", ok)


if __name__ == "__main__":
    main()
