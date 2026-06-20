"""Run AU discovery end-to-end and print job + company + executive scrape results."""

from __future__ import annotations

import json

from app.connectors.website_intelligence import scrape_website_sync
from app.db import get_supabase
from app.schemas import DiscoveryRequest
from app.tasks.discovery import _resolve_city_targets, run_discovery_job

PAYLOAD = {
    "industry": "Media",
    "country": "AU",
    "states": ["NSW", "VIC"],
    "cities": ["Sydney", "Melbourne"],
    "max_results": 2,
}


def main() -> None:
    req = DiscoveryRequest(**PAYLOAD)
    print("Payload:", json.dumps(PAYLOAD, indent=2))
    print("Resolved targets:", json.dumps(_resolve_city_targets(req), indent=2))

    run_discovery_job(req)

    db = get_supabase()
    job = (
        db.table("jobs")
        .select("*")
        .eq("job_type", "discovery")
        .order("id", desc=True)
        .limit(1)
        .execute()
        .data[0]
    )
    print("\n=== JOB RESULT ===")
    print(
        json.dumps(
            {k: job.get(k) for k in ("status", "progress", "message", "total_items", "processed_items", "error")},
            indent=2,
        )
    )

    rows = (
        db.table("companies")
        .select("name, city, state, website, phone, lead_score")
        .eq("country", "AU")
        .order("id", desc=True)
        .limit(5)
        .execute()
        .data
        or []
    )
    print("\n=== SAMPLE AU COMPANIES ===")
    for row in rows:
        print(
            f"- {row['name']} | {row.get('city')}, {row.get('state')} | "
            f"{row.get('website')} | score={row.get('lead_score')}"
        )

    for url in ["https://1minutemedia.com.au", "http://marver.com.au"]:
        print(f"\n=== EXEC SCRAPE: {url} ===")
        result = scrape_website_sync(url, max_pages=4)
        print("success:", result.success, "pages:", result.pages_scraped)
        for exec_contact in result.executives[:5]:
            print(
                {
                    "name": exec_contact.name,
                    "title": exec_contact.title,
                    "confidence": exec_contact.extraction_confidence,
                    "linkedin": exec_contact.linkedin_url,
                }
            )


if __name__ == "__main__":
    main()
