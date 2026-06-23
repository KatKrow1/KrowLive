"""Before/after executive extraction comparison for known companies."""

from __future__ import annotations

import json

from app.connectors.website_intelligence import scrape_website_sync
from app.db import get_supabase

SAMPLES = [
    ("Marketing Blendz", "https://marketingblendz.com"),
    ("Canada Create AI Marketing Agency", "https://canadacreate.com"),
    ("CBC", "https://cbc.ca"),
    ("One Market Media", "https://onemarketmedia.com"),
    ("SPG Media", "https://spgmedia.net"),
]


def _fmt_exec(e: dict) -> dict:
    return {
        "name": e.get("name"),
        "title": e.get("title"),
        "email": e.get("email"),
        "phone": e.get("phone"),
        "linkedin_url": e.get("linkedin_url"),
        "extraction_confidence": e.get("extraction_confidence", "low"),
    }


def main() -> None:
    db = get_supabase()
    print("=" * 72)
    for label, website in SAMPLES:
        print(f"\n### {label} ({website})")
        db_row = (
            db.table("companies")
            .select("*, executives(*)")
            .eq("website", website if website.startswith("http") else f"https://{website}")
            .limit(1)
            .execute()
        )
        before = []
        if db_row.data:
            before = [_fmt_exec(e) for e in db_row.data[0].get("executives") or []]
        else:
            alt = db.table("companies").select("*, executives(*)").ilike("name", f"%{label.split()[0]}%").limit(1).execute()
            if alt.data:
                before = [_fmt_exec(e) for e in alt.data[0].get("executives") or []]

        result = scrape_website_sync(website, max_pages=4)
        after = [
            {
                "name": e.name,
                "title": e.title,
                "email": e.email,
                "phone": e.phone,
                "linkedin_url": e.linkedin_url,
                "extraction_confidence": e.extraction_confidence,
            }
            for e in result.executives
        ]
        print("\nBEFORE (stored in DB):")
        print(json.dumps(before, indent=2))
        print("\nAFTER (fresh scrape):")
        print(json.dumps(after, indent=2))
        print(f"\nSocial links: {json.dumps(result.social_links)}")
        print("-" * 72)


if __name__ == "__main__":
    main()
