"""Standalone Google Places test — media companies across CA + AU cities."""

from __future__ import annotations

import sys

from app.connectors.google_places import PlaceResult, search_places
from scripts.media_test_config import INDUSTRY, MAX_RESULTS_PER_CITY, MEDIA_CITIES


def _print_place(place: PlaceResult, index: int) -> None:
    rating = place.google_rating if place.google_rating is not None else "N/A"
    print(f"  {index}. {place.name}")
    print(f"     Address: {place.address or 'N/A'}")
    print(f"     Phone:   {place.phone or 'N/A'}")
    print(f"     Website: {place.website or 'N/A'}")
    print(f"     Rating:  {rating}" + (f" ({place.google_review_count} reviews)" if place.google_review_count else ""))


def main() -> None:
    print(f"KrowLive Phase 4 — Google Places: '{INDUSTRY}'")
    print("=" * 60)

    total = 0
    ca_total = 0
    au_total = 0
    failures: list[str] = []

    for target in MEDIA_CITIES:
        label = target["label"]
        print(f"\n## {label}")
        print("-" * 40)
        try:
            results = search_places(
                industry=INDUSTRY,
                city=target["city"],
                state=target["state"],
                country=target["country"],
                max_results=MAX_RESULTS_PER_CITY,
            )
        except Exception as exc:
            print(f"  ERROR: {exc}")
            failures.append(f"{label}: {exc}")
            continue

        if not results:
            print("  No results returned.")
            failures.append(f"{label}: no results")
            continue

        for i, place in enumerate(results, start=1):
            _print_place(place, i)

        total += len(results)
        if target["country"] == "CA":
            ca_total += len(results)
        else:
            au_total += len(results)

    print("\n" + "=" * 60)
    print(f"Phase 4 summary: {total} businesses across {len(MEDIA_CITIES)} cities")
    print(f"  Canada: {ca_total} | Australia: {au_total}")
    if failures:
        print(f"  Warnings: {len(failures)} city search(es) had issues")
        for msg in failures:
            print(f"    - {msg}")

    if ca_total == 0 or au_total == 0:
        print("Phase 4 FAILED — need results from both CA and AU.")
        sys.exit(1)

    print("Phase 4 OK — real media businesses returned for Canada and Australia.")


if __name__ == "__main__":
    main()
