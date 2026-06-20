"""Lead enrichment — Claude API with rule-based fallback."""

from __future__ import annotations

import json
import re
from typing import Any

import anthropic

from app.config import settings

CLAUDE_MODEL = "claude-sonnet-4-6"
MAX_PAGE_TEXT_CHARS = 6000

ENRICHMENT_SYSTEM = (
    "You are a factual business data summarizer for KrowLive. "
    "You only describe observable facts from provided website content. "
    "Never infer business needs, pain points, or buying intent."
)

ENRICHMENT_USER_TEMPLATE = """Analyze the following company data scraped from their own website.

Do not speculate about the company's business needs, pain points, or challenges.
Only summarize observable facts from the provided website content.

Return ONLY valid JSON with exactly these keys:
- "summary": 2-3 objective sentences describing what the company actually does, based ONLY on their website content (services listed, About page text, homepage copy). No speculation.
- "lead_score": integer 0-100 based on data completeness only:
  * has email (+20), has phone (+20), has named decision-maker/executive (+25),
    site is active/scraped (+20), has Google rating (+10), has social links (+5).
  Do NOT score based on guessed buying intent.
- "tech_stack_signals": array of strings listing ONLY concrete, observable facts from the scraped content (e.g. "uses WordPress", "has no visible API/developer page", "job postings mention React"). Do NOT guess what the company needs or wants. If no concrete signals are found, return an empty array [].

Company name: {name}
Category: {category}
Website: {website}
Phone: {phone}
Emails found: {emails}
Executives found: {executives}
Site active (pages scraped): {site_active}
Google rating: {google_rating}
Social links: {social_links}
Pages scraped: {page_urls}

Website content excerpts:
{page_text}
"""

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


def _executive_names(executives: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for exec_row in executives:
        name = (exec_row.get("name") or "").strip()
        title = exec_row.get("title") or ""
        if name:
            names.append(f"{name} ({title})" if title else name)
    return names


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
    """Score and summarize using deterministic rules when Claude is unavailable."""
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
    # Only keep "no visible API/developer page" when site was actually scraped
    if not site_active:
        tech_signals = [s for s in tech_signals if s != "has no visible API/developer page"]

    return {
        "summary": " ".join(parts[:3]),
        "lead_score": min(score, 100),
        "tech_stack_signals": tech_signals,
    }


def _parse_claude_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    summary = str(data.get("summary", "")).strip()
    lead_score = int(data.get("lead_score", 0))
    lead_score = max(0, min(lead_score, 100))
    raw_signals = data.get("tech_stack_signals", [])
    tech_stack_signals = [str(s).strip() for s in raw_signals if str(s).strip()] if isinstance(raw_signals, list) else []
    if not summary:
        raise ValueError("Empty summary from Claude")
    return {"summary": summary, "lead_score": lead_score, "tech_stack_signals": tech_stack_signals}


def claude_enrichment(signals: dict[str, Any]) -> dict[str, Any]:
    page_text = "\n---\n".join(signals.get("page_texts") or [])[:MAX_PAGE_TEXT_CHARS]
    if not page_text:
        page_text = "(No website text captured)"

    prompt = ENRICHMENT_USER_TEMPLATE.format(
        name=signals.get("name", ""),
        category=signals.get("category", ""),
        website=signals.get("website", ""),
        phone=signals.get("phone") or "none",
        emails=", ".join(signals.get("emails") or []) or "none",
        executives=", ".join(_executive_names(signals.get("executives") or [])) or "none",
        site_active=signals.get("site_active", False),
        google_rating=signals.get("google_rating") if signals.get("google_rating") is not None else "none",
        social_links=json.dumps(signals.get("social_links") or {}),
        page_urls=", ".join(signals.get("page_urls") or []) or "none",
        page_text=page_text,
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=768,
        system=ENRICHMENT_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    block = response.content[0]
    if block.type != "text":
        raise ValueError("Unexpected Claude response type")
    return _parse_claude_json(block.text)


def enrich_company(signals: dict[str, Any]) -> dict[str, Any]:
    """Return summary, lead_score, and tech_stack_signals; falls back to rules if needed."""
    if settings.anthropic_api_key:
        try:
            return claude_enrichment(signals)
        except Exception:
            pass
    return rule_based_enrichment(signals)
