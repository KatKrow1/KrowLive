"""Before/after: DB state vs fresh scrape with Ollama provider (fail-safe to heuristics)."""

from __future__ import annotations

import json
import os
import time

from app.connectors.website_intelligence import scrape_website_sync
from app.db import get_supabase
from app.enrichment import enrich_company, rule_based_enrichment

SAMPLES = [
    ("Canada Create AI Marketing Agency", "https://canadacreate.com"),
    ("Aspen Films", "https://aspenfilms.ca/toronto-video"),
    ("Marketing Blendz", "https://marketingblendz.com"),
]


def _fmt_execs(execs: list) -> list[dict]:
    out = []
    for e in execs:
        if hasattr(e, "name"):
            out.append(
                {
                    "name": e.name,
                    "title": e.title,
                    "email": e.email,
                    "phone": e.phone,
                    "linkedin_url": e.linkedin_url,
                    "extraction_confidence": e.extraction_confidence,
                }
            )
        else:
            out.append(
                {
                    "name": e.get("name"),
                    "title": e.get("title"),
                    "email": e.get("email"),
                    "phone": e.get("phone"),
                    "linkedin_url": e.get("linkedin_url"),
                    "extraction_confidence": e.get("extraction_confidence"),
                }
            )
    return out


def main() -> None:
    os.environ["ENRICHMENT_PROVIDER"] = "ollama"
    os.environ["OLLAMA_TIMEOUT_SECONDS"] = "60"

    db = get_supabase()
    for label, website in SAMPLES:
        db_row = (
            db.table("companies")
            .select("summary, tech_stack_signals, executives(*)")
            .eq("website", website)
            .limit(1)
            .execute()
            .data
            or []
        )
        before = {
            "summary": db_row[0].get("summary") if db_row else None,
            "tech_stack_signals": (db_row[0].get("tech_stack_signals") or []) if db_row else [],
            "executives": _fmt_execs((db_row[0].get("executives") or []) if db_row else []),
        }

        t0 = time.perf_counter()
        intel = scrape_website_sync(website, max_pages=4)
        scrape_s = time.perf_counter() - t0

        signals = {
            "name": label,
            "category": "Media",
            "page_texts": intel.page_texts,
            "page_urls": intel.pages_scraped,
            "emails": intel.emails,
            "phones": intel.phones,
            "executives": _fmt_execs(intel.executives),
            "site_active": intel.success,
            "social_links": intel.social_links,
        }

        t1 = time.perf_counter()
        rules = rule_based_enrichment(signals)
        rule_ms = (time.perf_counter() - t1) * 1000

        t2 = time.perf_counter()
        enriched = enrich_company(signals)
        ollama_s = time.perf_counter() - t2

        after = {
            "summary": enriched["summary"],
            "tech_stack_signals": enriched.get("tech_stack_signals") or [],
            "executives": _fmt_execs(intel.executives),
        }

        print("\n" + "=" * 72)
        print(f"### {label} ({website})")
        print("BEFORE:", json.dumps(before, indent=2))
        print("AFTER:", json.dumps(after, indent=2))
        print(f"Timing — scrape: {scrape_s:.1f}s, rule enrich: {rule_ms:.0f}ms, ollama enrich: {ollama_s:.1f}s")
        print(f"(rule summary preview: {rules['summary'][:120]}...)")


if __name__ == "__main__":
    main()
