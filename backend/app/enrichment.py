"""Lead enrichment — rule-based by default, optional custom AI provider."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

import httpx

from app.config import settings

logger = logging.getLogger("krowlive.enrichment")

EnrichmentProvider = Literal["none", "custom", "ollama"]
CUSTOM_ENRICHMENT_TIMEOUT = 30.0

TECH_SIGNAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("uses WordPress", re.compile(r"\bwordpress\b", re.I)),
    ("uses Shopify", re.compile(r"\bshopify\b", re.I)),
    ("uses Wix", re.compile(r"\bwix\b", re.I)),
    ("uses Squarespace", re.compile(r"\bsquarespace\b", re.I)),
    ("mentions React", re.compile(r"\breact(?:\.js)?\b", re.I)),
    ("mentions Vue", re.compile(r"\bvue(?:\.js)?\b", re.I)),
    ("mentions Angular", re.compile(r"\bangular\b", re.I)),
    ("mentions Node.js", re.compile(r"\bnode\.?js\b", re.I)),
    ("mentions Python", re.compile(r"\bpython\b", re.I)),
    ("mentions API", re.compile(r"\bapi\b", re.I)),
]


def _extract_tech_stack_signals(signals: dict[str, Any]) -> list[str]:
    """Rule-based observable tech signals from scraped page text and URLs."""
    combined = " ".join(signals.get("page_texts") or [])
    page_urls = signals.get("page_urls") or []
    found: list[str] = []

    for label, pattern in TECH_SIGNAL_PATTERNS:
        if pattern.search(combined) and label not in found:
            found.append(label)

    url_blob = " ".join(page_urls).lower()
    has_dev_page = any(
        token in url_blob
        for token in ("/developer", "/developers", "/api", "/docs", "developer.", "api.")
    )
    if not has_dev_page and "mentions API" not in found:
        found.append("has no visible API/developer page")

    return found


def rule_based_enrichment(signals: dict[str, Any]) -> dict[str, Any]:
    """Score and summarize using deterministic rules from scraped facts."""
    name = signals.get("name") or "This company"
    category = signals.get("category") or "business"
    page_texts: list[str] = signals.get("page_texts") or []
    combined = " ".join(page_texts)[:800].strip()

    parts: list[str] = [f"{name} operates as a {category}."]
    if combined:
        snippet = re.sub(r"\s+", " ", combined)[:280].strip()
        if snippet:
            parts.append(f"Their website states: {snippet}")
    else:
        parts.append("Limited public website content was available at scrape time.")

    score = 0
    emails = signals.get("emails") or []
    phones = signals.get("phones") or []
    executives = signals.get("executives") or []
    social_links = signals.get("social_links") or {}
    site_active = bool(signals.get("site_active"))
    google_rating = signals.get("google_rating")

    if emails:
        score += 20
    if phones or signals.get("phone"):
        score += 20
    if executives:
        score += 25
    if site_active:
        score += 20
    if google_rating is not None:
        score += 10
    if any(social_links.values()):
        score += 5

    tech_signals = _extract_tech_stack_signals(signals)
    if not site_active:
        tech_signals = [s for s in tech_signals if s != "has no visible API/developer page"]

    return {
        "summary": " ".join(parts[:3]),
        "lead_score": min(score, 100),
        "tech_stack_signals": tech_signals,
    }


def _parse_custom_response(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Enrichment response must be a JSON object")
    summary = str(data.get("summary", "")).strip()
    if not summary:
        raise ValueError("Enrichment response missing summary")
    lead_score = int(data.get("lead_score", 0))
    lead_score = max(0, min(lead_score, 100))
    return {"summary": summary, "lead_score": lead_score}


def custom_provider_enrichment(signals: dict[str, Any]) -> dict[str, Any]:
    """POST scraped signals to a custom enrichment API (chat-completion style)."""
    if not settings.enrichment_api_url or not settings.enrichment_api_key:
        raise ValueError("ENRICHMENT_API_URL and ENRICHMENT_API_KEY required for custom provider")

    with httpx.Client(timeout=CUSTOM_ENRICHMENT_TIMEOUT) as client:
        response = client.post(
            settings.enrichment_api_url,
            headers={
                "Authorization": f"Bearer {settings.enrichment_api_key}",
                "Content-Type": "application/json",
            },
            json={"signals": signals},
        )
        response.raise_for_status()
        return _parse_custom_response(response.json())


def enrich_company(signals: dict[str, Any]) -> dict[str, Any]:
    """Return summary, lead_score, and tech_stack_signals."""
    provider = settings.enrichment_provider.lower().strip()
    rules = rule_based_enrichment(signals)

    if provider == "ollama":
        try:
            from app.services.ollama_client import ollama_summary_and_tech

            page_texts = signals.get("page_texts") or []
            ollama_result = ollama_summary_and_tech(page_texts)
            if ollama_result:
                tech = ollama_result.get("tech_stack_signals") or []
                if not tech:
                    tech = rules["tech_stack_signals"]
                return {
                    "summary": ollama_result["summary"],
                    "lead_score": rules["lead_score"],
                    "tech_stack_signals": tech,
                }
        except Exception as exc:
            logger.warning("Ollama enrichment failed, using rule-based fallback: %s", exc)

    if provider == "custom":
        try:
            ai_result = custom_provider_enrichment(signals)
            rules = rule_based_enrichment(signals)
            return {
                "summary": ai_result["summary"],
                "lead_score": ai_result["lead_score"],
                "tech_stack_signals": rules["tech_stack_signals"],
            }
        except Exception as exc:
            logger.warning("Custom enrichment failed, using rule-based fallback: %s", exc)

    return rules
