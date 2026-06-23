"""Standalone website intelligence test — media company sites from Phase 4 + one failure."""

from __future__ import annotations

import json
import sys

from app.connectors.google_places import search_places
from app.connectors.website_intelligence import scrape_website_sync
from scripts.media_test_config import INDUSTRY, MAX_RESULTS_PER_CITY, MEDIA_CITIES

BROKEN_SITE = ("Broken site (should skip gracefully)", "https://krowlive-invalid-domain-xyz123.example")
WEBSITE_SCRAPE_COUNT = 3
WEBSITE_CANDIDATE_POOL = 12


def _collect_media_sites() -> list[tuple[str, str]]:
    """Run Phase 4 searches and return real media company website candidates."""
    sites: list[tuple[str, str]] = []
    seen_websites: set[str] = set()

    print(f"Collecting media company websites from Google Places ('{INDUSTRY}')...")
    for target in MEDIA_CITIES:
        if len(sites) >= WEBSITE_CANDIDATE_POOL:
            break
        try:
            results = search_places(
                industry=INDUSTRY,
                city=target["city"],
                state=target["state"],
                country=target["country"],
                max_results=MAX_RESULTS_PER_CITY,
            )
        except Exception:
            continue

        for place in results:
            if not place.website or place.website in seen_websites:
                continue
            seen_websites.add(place.website)
            label = f"{place.name} ({target['label']})"
            sites.append((label, place.website))

    return sites


def main() -> None:
    print("KrowLive Phase 5 — website intelligence standalone test")
    print("=" * 60)

    media_candidates = _collect_media_sites()
    if not media_candidates:
        print("ERROR: No media company websites found from Phase 4 searches.")
        sys.exit(1)

    print(f"Found {len(media_candidates)} candidate site(s) from Phase 4. Scraping until {WEBSITE_SCRAPE_COUNT} succeed...")
    print()

    ok_count = 0
    skip_count = 0
    scraped_media: list[tuple[str, str]] = []

    for label, url in media_candidates:
        if ok_count >= WEBSITE_SCRAPE_COUNT:
            break
        print(f"\n[{label}]")
        print(f"URL: {url}")
        result = scrape_website_sync(url, max_pages=4)

        payload = {
            "success": result.success,
            "error": result.error,
            "pages_scraped": result.pages_scraped,
            "emails": result.emails,
            "phones": result.phones,
            "executives": [
                {
                    "name": e.name,
                    "title": e.title,
                    "email": e.email,
                    "phone": e.phone,
                    "consent_status": e.consent_status,
                    "source_page": e.source_page,
                }
                for e in result.executives
            ],
        }
        print(json.dumps(payload, indent=2))

        if result.success:
            ok_count += 1
            scraped_media.append((label, url))
            print(
                f"OK: {len(result.emails)} emails, {len(result.phones)} phones, "
                f"{len(result.executives)} leadership mentions"
            )
        else:
            skip_count += 1
            print(f"SKIPPED: {result.error}")

    label, url = BROKEN_SITE
    print(f"\n[{label}]")
    print(f"URL: {url}")
    result = scrape_website_sync(url, max_pages=4)
    payload = {
        "success": result.success,
        "error": result.error,
        "pages_scraped": result.pages_scraped,
        "emails": result.emails,
        "phones": result.phones,
        "executives": [],
    }
    print(json.dumps(payload, indent=2))
    if result.success:
        ok_count += 1
    else:
        skip_count += 1
        print(f"SKIPPED: {result.error}")

    print("\n" + "=" * 60)
    print(f"Phase 5 summary: {ok_count} scraped, {skip_count} skipped (no crash)")
    if ok_count < 2:
        sys.exit(1)


if __name__ == "__main__":
    main()
