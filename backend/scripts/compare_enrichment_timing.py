"""Compare rule-based vs Ollama enrichment timing on one scrape."""

from __future__ import annotations

import os
import time

from app.connectors.website_intelligence import scrape_website_sync
from app.enrichment import enrich_company

WEBSITE = "https://marketingblendz.com"


def main() -> None:
    print("Scraping", WEBSITE)
    t0 = time.perf_counter()
    intel = scrape_website_sync(WEBSITE, max_pages=4)
    scrape_s = time.perf_counter() - t0
    print(f"Scrape: {scrape_s:.1f}s, executives={len(intel.executives)}, pages={len(intel.pages_scraped)}")

    signals = {
        "name": "Marketing Blendz",
        "category": "Media",
        "page_texts": intel.page_texts,
        "page_urls": intel.pages_scraped,
        "emails": intel.emails,
        "phones": intel.phones,
        "executives": [{"name": e.name, "title": e.title} for e in intel.executives],
        "site_active": intel.success,
        "social_links": intel.social_links,
    }

    os.environ["ENRICHMENT_PROVIDER"] = "none"
    from importlib import reload
    import app.config as config_mod
    reload(config_mod)
    import app.enrichment as enrichment_mod
    reload(enrichment_mod)

    t1 = time.perf_counter()
    rules = enrichment_mod.enrich_company(signals)
    rules_s = time.perf_counter() - t1

    os.environ["ENRICHMENT_PROVIDER"] = "ollama"
    reload(config_mod)
    reload(enrichment_mod)

    t2 = time.perf_counter()
    ollama = enrichment_mod.enrich_company(signals)
    ollama_s = time.perf_counter() - t2

    print(f"\nRule-based enrich: {rules_s:.3f}s")
    print("Summary:", rules["summary"][:200])
    print(f"\nOllama enrich: {ollama_s:.1f}s")
    print("Summary:", (ollama.get("summary") or rules["summary"])[:200])
    print("Tech:", ollama.get("tech_stack_signals"))


if __name__ == "__main__":
    main()
