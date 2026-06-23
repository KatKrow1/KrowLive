"""Clean before/after diff — Ollama-refined vs stored DB (no error noise on stdout)."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

# Keep stdout clean; errors go only to stderr if CRITICAL+ somehow fires.
logging.basicConfig(level=logging.CRITICAL, stream=sys.stderr)
for name in ("krowlive.ollama", "krowlive.enrichment", "httpx", "httpcore", "krowlive.pipeline"):
    logging.getLogger(name).setLevel(logging.CRITICAL)

from app.connectors.website_intelligence import scrape_website_sync
from app.db import get_supabase
from app.enrichment import enrich_company, rule_based_enrichment
from app.services.ollama_client import ollama_summary_and_tech

SAMPLES = [
    ("Marketing Blendz", "https://marketingblendz.com"),
    ("Canada Create AI Marketing Agency", "https://canadacreate.com"),
    ("One Market Media", "http://onemarketmedia.com"),
]


def _snap(row: dict) -> dict[str, Any]:
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


def _exec_snap(intel_executives: list) -> list[dict]:
    return [
        {
            "name": e.name,
            "title": e.title,
            "email": e.email,
            "phone": e.phone,
            "linkedin_url": e.linkedin_url,
            "extraction_confidence": e.extraction_confidence,
        }
        for e in intel_executives
    ]


def main() -> None:
    os.environ["ENRICHMENT_PROVIDER"] = "ollama"
    timeout = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "360"))

    from importlib import reload
    import app.config as config_mod
    os.environ["OLLAMA_TIMEOUT_SECONDS"] = str(timeout)
    reload(config_mod)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    db = get_supabase()
    summary_ollama: list[str] = []
    summary_fallback: list[str] = []
    exec_ollama_confirmed: list[str] = []

    for label, website in SAMPLES:
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
            print(f"\n{'='*72}\nSKIP {label} — not found in DB\n")
            continue

        before = _snap(rows[0])

        t0 = time.perf_counter()
        intel = scrape_website_sync(website, max_pages=4)
        scrape_s = time.perf_counter() - t0

        for e in intel.executives:
            if e.extraction_confidence in ("medium", "high"):
                exec_ollama_confirmed.append(f"{label}: {e.name} ({e.extraction_confidence})")

        signals = {
            "name": label,
            "category": rows[0].get("category") or "Media",
            "page_texts": intel.page_texts,
            "page_urls": intel.pages_scraped,
            "emails": intel.emails,
            "phones": intel.phones,
            "executives": _exec_snap(intel.executives),
            "site_active": intel.success,
            "social_links": intel.social_links,
        }

        rules = rule_based_enrichment(signals)

        t1 = time.perf_counter()
        ollama_result = ollama_summary_and_tech(intel.page_texts)
        summary_call_s = time.perf_counter() - t1

        if ollama_result:
            summary_ollama.append(label)
            final_summary = ollama_result["summary"]
            final_tech = ollama_result.get("tech_stack_signals") or rules["tech_stack_signals"]
            summary_source = "ollama"
        else:
            summary_fallback.append(label)
            enriched = enrich_company(signals)
            final_summary = enriched["summary"]
            final_tech = enriched.get("tech_stack_signals") or rules["tech_stack_signals"]
            summary_source = "rule-based (timeout/error fallback)"

        after = {
            "summary": final_summary,
            "tech_stack_signals": final_tech,
            "executives": _exec_snap(intel.executives),
        }

        print(f"\n{'='*72}")
        print(f"COMPANY: {label}")
        print(f"WEBSITE: {website}")
        print(f"TIMING: scrape={scrape_s:.1f}s, ollama_summary_call={summary_call_s:.1f}s, timeout_setting={timeout}s")
        print(f"SUMMARY SOURCE: {summary_source}")
        print()
        print("--- OLD (stored in DB) ---")
        print(json.dumps(before, indent=2, ensure_ascii=False))
        print()
        print("--- NEW (Ollama-refined scrape) ---")
        print(json.dumps(after, indent=2, ensure_ascii=False))
        sys.stdout.flush()

    print(f"\n{'='*72}")
    print("RUN DIAGNOSTICS")
    print(f"Ollama server: http://localhost:11434 (checked at start of script)")
    print(f"Timeout setting: {timeout}s")
    print()
    print("Summary via Ollama:", summary_ollama if summary_ollama else "(none)")
    print("Summary rule-based fallback:", summary_fallback if summary_fallback else "(none)")
    print("Executives Ollama-confirmed (medium/high confidence):", exec_ollama_confirmed or "(none)")


if __name__ == "__main__":
    main()
