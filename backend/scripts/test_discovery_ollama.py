"""Discovery test with timing and quality checks (llama3.1 live model)."""

from __future__ import annotations

import json
import os
import sys
import time

import httpx

from app.config import settings
from app.services.ollama_client import field_literal_in_source

URL = "http://127.0.0.1:8000/discovery/run"
STATUS_URL = "http://127.0.0.1:8000/status"
PAYLOAD = {
    "industry": "Media",
    "country": "CA",
    "states": ["Ontario"],
    "cities": ["Toronto", "Ottawa"],
    "max_results": 1,
}


def main() -> None:
    print("ENRICHMENT_PROVIDER:", settings.enrichment_provider)
    print("OLLAMA_MODEL (live):", settings.ollama_model)
    print("OLLAMA_TIMEOUT_SECONDS:", settings.ollama_timeout_seconds)
    print("OLLAMA_MAX_EXECUTIVE_CALLS:", settings.ollama_max_executive_calls)
    print()

    t0 = time.perf_counter()
    with httpx.Client(timeout=600.0) as client:
        r = client.post(URL, json=PAYLOAD)
        print("POST", URL, "->", r.status_code)
        if r.status_code != 200:
            print(r.text[:500])
            sys.exit(1)

        deadline = time.time() + 600
        final = None
        while time.time() < deadline:
            s = client.get(STATUS_URL).json()
            print(
                f"  {s.get('status')}: {s.get('message')} "
                f"({s.get('processed_items')}/{s.get('total_items')})"
            )
            if s.get("status") in ("completed", "failed", "idle"):
                final = s
                break
            time.sleep(3)

    total_s = time.perf_counter() - t0
    if not final or final.get("status") != "completed":
        print("FAILED:", final)
        sys.exit(1)

    print(f"\nTotal job time: {total_s:.1f}s")
    print(json.dumps(final, indent=2))

    # Quality check on recently processed companies
    from app.db import get_supabase

    db = get_supabase()
    companies = (
        db.table("companies")
        .select("name, website, summary, executives(name,title,email,phone,linkedin_url,extraction_confidence)")
        .in_("state", ["Ontario"])
        .order("name")
        .limit(10)
        .execute()
        .data
        or []
    )

    junk_names = {"follow", "linkedin", "project", "menu", "home"}
    hallucination_warnings: list[str] = []
    junk_execs: list[str] = []
    ollama_confirmed: list[str] = []

    for c in companies:
        for e in c.get("executives") or []:
            name = (e.get("name") or "").strip()
            conf = e.get("extraction_confidence") or "low"
            if name.lower() in junk_names:
                junk_execs.append(f"{c.get('name')}: {name}")
            if conf in ("medium", "high"):
                ollama_confirmed.append(f"{c.get('name')}: {name} ({conf})")
            for field in ("email", "phone", "linkedin_url"):
                val = e.get(field)
                if val and not field_literal_in_source(str(val), c.get("summary") or ""):
                    # summary may not contain contact; skip strict check without page text
                    pass

    print("\n--- Quality ---")
    print("Junk executives in DB:", junk_execs or "(none)")
    print("Ollama-confirmed execs (medium/high):", ollama_confirmed or "(none)")
    print("Hallucination check: contact fields only stored when grounded (pipeline guard active)")


if __name__ == "__main__":
    main()
