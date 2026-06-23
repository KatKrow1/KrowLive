"""Re-run Ollama enrichment over all existing companies and executives (idempotent)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from typing import Any

from app.config import settings
from app.connectors.website_intelligence import scrape_website_sync
from app.db import get_supabase
from app.services.company_pipeline import process_company_record
from app.services.ollama_client import field_literal_in_source, refinement_mode

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("refine_existing_companies")


def _fmt_exec(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": row.get("name"),
        "title": row.get("title"),
        "email": row.get("email"),
        "phone": row.get("phone"),
        "linkedin_url": row.get("linkedin_url"),
        "extraction_confidence": row.get("extraction_confidence"),
    }


def _company_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    execs = row.get("executives") or []
    return {
        "summary": row.get("summary"),
        "tech_stack_signals": row.get("tech_stack_signals") or [],
        "executives": [_fmt_exec(e) for e in execs],
    }


def _verify_no_hallucinations(
    executives: list[dict[str, Any]],
    page_texts: list[str],
) -> list[str]:
    """Return list of warning messages for fields not grounded in source text."""
    source = " ".join(page_texts)
    warnings: list[str] = []
    for exec_row in executives:
        label = exec_row.get("name") or "unknown"
        for field in ("email", "phone", "linkedin_url"):
            value = exec_row.get(field)
            if value and not field_literal_in_source(str(value), source):
                warnings.append(f"{label}.{field}={value!r} not in source text")
    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-run Ollama enrichment on stored companies")
    parser.add_argument("--limit", type=int, default=0, help="Max companies to process (0 = all)")
    args = parser.parse_args()

    if settings.enrichment_provider != "ollama":
        logger.error("Set ENRICHMENT_PROVIDER=ollama before running this script")
        sys.exit(1)

    db = get_supabase()
    rows = (
        db.table("companies")
        .select("*, executives(*)")
        .not_.is_("website", "null")
        .order("name")
        .execute()
        .data
        or []
    )

    if not rows:
        logger.info("No companies with websites found")
        return

    if args.limit > 0:
        rows = rows[: args.limit]

    logger.info(
        "Refining %d companies with Ollama refinement model (%s)",
        len(rows),
        settings.ollama_refinement_model,
    )
    touched = 0
    hallucination_warnings: list[str] = []
    start = time.perf_counter()

    for row in rows:
        company_id = row["id"]
        name = row.get("name") or company_id
        website = row.get("website")
        if not website:
            continue

        before = _company_snapshot(row)
        t0 = time.perf_counter()

        with refinement_mode():
            _, success = process_company_record(db, dict(row), source=row.get("source") or "google_places")
        elapsed = time.perf_counter() - t0

        if not success:
            logger.warning("Failed to refine %s (%s)", name, website)
            continue

        refreshed = (
            db.table("companies")
            .select("*, executives(*)")
            .eq("id", company_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not refreshed:
            continue
        after = _company_snapshot(refreshed[0])

        intel = scrape_website_sync(website, max_pages=4)
        hallucination_warnings.extend(
            _verify_no_hallucinations(after["executives"], intel.page_texts)
        )

        if before == after:
            logger.debug("No change for %s (%.1fs)", name, elapsed)
            continue

        touched += 1
        print("\n" + "=" * 72)
        print(f"### {name} ({website}) — {elapsed:.1f}s")
        print("\nBEFORE:")
        print(json.dumps(before, indent=2))
        print("\nAFTER:")
        print(json.dumps(after, indent=2))

    total = time.perf_counter() - start
    print("\n" + "=" * 72)
    print(f"Done: {touched}/{len(rows)} companies updated in {total:.1f}s")
    if hallucination_warnings:
        print("\nHALLUCINATION WARNINGS:")
        for w in hallucination_warnings:
            print(f"  - {w}")
    else:
        print("\nHallucination check: no ungrounded contact fields detected in stored data.")


if __name__ == "__main__":
    main()
