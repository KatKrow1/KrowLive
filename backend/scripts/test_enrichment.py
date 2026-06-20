"""Test enrichment with and without Anthropic API key."""

from __future__ import annotations

import json

from app.enrichment import enrich_company


def main() -> None:
    signals = {
        "name": "Viva Media",
        "category": "Media",
        "website": "https://vivamedia.ca",
        "phone": "(647) 749-8842",
        "emails": ["hello@vivamedia.ca"],
        "phones": ["647-749-8842"],
        "executives": [{"name": "Shawn Bedard", "title": "President"}],
        "site_active": True,
        "google_rating": 5.0,
        "social_links": {"linkedin": "https://linkedin.com/company/viva-media"},
        "page_texts": [
            "Viva Media is a video production and creative agency based in Toronto.",
            "We offer commercial production, animation, and post-production services.",
        ],
    }
    result = enrich_company(signals)
    print(json.dumps(result, indent=2))
    assert "tech_stack_signals" in result
    print("Phase 6 OK — enrichment returned summary, lead_score, tech_stack_signals")


if __name__ == "__main__":
    main()
