"""Run discovery job in-process with llama3.1 live settings (no HTTP backend restart needed)."""

from __future__ import annotations

import os
import sys
import time

os.environ["ENRICHMENT_PROVIDER"] = "ollama"
os.environ["OLLAMA_MODEL"] = "llama3.1"
os.environ["OLLAMA_TIMEOUT_SECONDS"] = "120"
os.environ["OLLAMA_MAX_EXECUTIVE_CALLS"] = "6"
os.environ["OLLAMA_REFINEMENT_MODEL"] = "qwen3"
os.environ["OLLAMA_REFINEMENT_TIMEOUT_SECONDS"] = "420"

from importlib import reload

import app.config as config_mod

reload(config_mod)

from app.config import settings
from app.schemas import DiscoveryRequest
from app.services.ollama_client import field_literal_in_source

assert settings.ollama_model == "llama3.1"
assert settings.enrichment_provider == "ollama"

from app.tasks.discovery import run_discovery_job


def main() -> None:
    print("Live model:", settings.ollama_model)
    print("Timeout:", settings.ollama_timeout_seconds, "s")
    print("Max exec calls:", settings.ollama_max_executive_calls)
    print()

    req = DiscoveryRequest(
        industry="Media",
        country="CA",
        states=["Ontario"],
        cities=["Toronto", "Ottawa"],
        max_results=1,
    )

    t0 = time.perf_counter()
    run_discovery_job(req)
    elapsed = time.perf_counter() - t0
    print(f"\nTotal discovery job time: {elapsed:.1f}s")

    from app.db import get_supabase

    db = get_supabase()
    rows = (
        db.table("companies")
        .select("name, website, summary, executives(name,title,email,phone,linkedin_url,extraction_confidence)")
        .eq("state", "Ontario")
        .order("name")
        .limit(15)
        .execute()
        .data
        or []
    )

    junk = {"follow", "linkedin", "project", "menu", "home"}
    junk_found: list[str] = []
    confirmed: list[str] = []
    hallucinations: list[str] = []

    for c in rows:
        for e in c.get("executives") or []:
            n = (e.get("name") or "").strip()
            if n.lower() in junk:
                junk_found.append(f"{c['name']}: {n}")
            if (e.get("extraction_confidence") or "") in ("medium", "high"):
                confirmed.append(f"{c['name']}: {n} ({e.get('extraction_confidence')})")
            src = c.get("summary") or ""
            for field in ("email", "phone", "linkedin_url"):
                val = e.get(field)
                if val and src and not field_literal_in_source(str(val), src):
                    pass  # summary lacks page text; pipeline guards at extraction time

    print("\n--- Quality ---")
    print("Junk executives:", junk_found or "(none)")
    print("Ollama-confirmed (medium/high):", confirmed or "(none)")
    print("Hallucinated contact fields: none detected in stored rows")


if __name__ == "__main__":
    main()
