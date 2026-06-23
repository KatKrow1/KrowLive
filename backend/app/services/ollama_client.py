"""Ollama HTTP client for structured extraction and enrichment."""

from __future__ import annotations

import json
import logging
import re
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

import httpx

from app.config import settings

logger = logging.getLogger("krowlive.ollama")

_refinement_mode: ContextVar[bool] = ContextVar("ollama_refinement_mode", default=False)

_TECH_SIGNAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
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

EXECUTIVE_EXTRACT_PROMPT = """Below is raw text/HTML from a company team page. Extract ONLY information EXPLICITLY present in this text. Do not guess, infer, or invent anything. Return ONLY valid JSON: {{"name": string or null, "title": string or null, "email": string or null, "phone": string or null, "linkedin_url": string or null, "is_real_person": true or false}}. If a field isn't explicitly present, use null. If this isn't a real person (nav text, company name, generic content), set is_real_person to false and all fields null.

TEXT: {text}"""

SUMMARY_EXTRACT_PROMPT = """Below is scraped text from a company website. Write a factual 2-3 sentence summary using ONLY information explicitly stated in the text. Do not speculate about needs, pain points, or opportunities. Also list explicit technology/platform mentions found in the text (e.g. WordPress, Shopify, React). Return ONLY valid JSON: {{"summary": string, "tech_mentions": [string]}}. If no tech is mentioned, use an empty list.

TEXT: {text}"""


def _base_url() -> str:
    return settings.ollama_base_url.rstrip("/")


def _active_model() -> str:
    if _refinement_mode.get():
        return settings.ollama_refinement_model
    return settings.ollama_model


def _active_timeout() -> float:
    if _refinement_mode.get():
        return settings.ollama_refinement_timeout_seconds
    return settings.ollama_timeout_seconds


@contextmanager
def refinement_mode() -> Iterator[None]:
    """Use OLLAMA_REFINEMENT_MODEL (qwen3) — for offline refine scripts only."""
    token = _refinement_mode.set(True)
    try:
        yield
    finally:
        _refinement_mode.reset(token)


def _generate_json(
    prompt: str,
    *,
    timeout: float | None = None,
    model: str | None = None,
) -> dict[str, Any] | None:
    if timeout is None:
        timeout = _active_timeout()
    if model is None:
        model = _active_model()
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{_base_url()}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "think": False,
                    "options": {"num_predict": 64, "temperature": 0},
                },
            )
            response.raise_for_status()
            body = response.json()
            raw = (body.get("response") or "").strip()
            if not raw:
                return None
            return _parse_json_object(raw)
    except Exception as exc:
        logger.warning("Ollama request failed: %s", exc)
        return None


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _normalize_phone_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def field_literal_in_source(field_value: str | None, source: str) -> bool:
    """Return True only if field_value literally appears in source text."""
    if not field_value or not source:
        return False
    source_lower = source.lower()
    value = field_value.strip()
    if not value:
        return False
    if value.lower() in source_lower:
        return True
    if "@" in value:
        return value.lower() in source_lower
    if value.startswith("http"):
        normalized = value.split("?", 1)[0].rstrip("/").lower()
        return normalized in source_lower.replace("www.", "")
    digits = _normalize_phone_digits(value)
    if len(digits) >= 10:
        return digits in _normalize_phone_digits(source)
    return False


def _guard_contact_field(
    field_name: str,
    value: str | None,
    source: str,
    *,
    person_label: str,
) -> str | None:
    if not value:
        return None
    if field_literal_in_source(value, source):
        return value.strip()
    logger.warning(
        "Ollama hallucinated %s for %s — discarding: %r",
        field_name,
        person_label,
        value,
    )
    return None


def refine_executive_from_container(
    heuristic_name: str,
    heuristic_title: str | None,
    heuristic_email: str | None,
    heuristic_phone: str | None,
    heuristic_linkedin: str | None,
    heuristic_confidence: str,
    container_text: str,
    *,
    source_page: str | None = None,
) -> dict[str, Any] | None:
    """
    Refine one executive candidate via Ollama.
    Returns dict with executive fields, or None if discarded (not a real person).
    On failure, returns None to signal caller should keep heuristic unchanged.
    """
    text = container_text[:4000].strip()
    if not text:
        return None

    parsed = _generate_json(EXECUTIVE_EXTRACT_PROMPT.format(text=text))
    if not parsed:
        return None  # fail-safe: caller keeps heuristic

    if not parsed.get("is_real_person"):
        return {"discarded": True}

    label = str(parsed.get("name") or heuristic_name)
    ollama_name = parsed.get("name") if isinstance(parsed.get("name"), str) else None
    ollama_title = parsed.get("title") if isinstance(parsed.get("title"), str) else None
    ollama_email = _guard_contact_field("email", parsed.get("email"), text, person_label=label)
    ollama_phone = _guard_contact_field("phone", parsed.get("phone"), text, person_label=label)
    ollama_linkedin = _guard_contact_field(
        "linkedin_url", parsed.get("linkedin_url"), text, person_label=label
    )

    name = (ollama_name or heuristic_name).strip()
    title = (ollama_title or heuristic_title or "").strip() or heuristic_title
    email = ollama_email or heuristic_email
    phone = ollama_phone or heuristic_phone
    linkedin = ollama_linkedin or heuristic_linkedin

    if ollama_email and heuristic_email and ollama_email != heuristic_email:
        email = ollama_email
    if ollama_phone and heuristic_phone and ollama_phone != heuristic_phone:
        phone = ollama_phone
    if ollama_linkedin and heuristic_linkedin and ollama_linkedin != heuristic_linkedin:
        linkedin = ollama_linkedin

    has_contact = bool(email or phone or linkedin)
    if has_contact:
        confidence = "high"
    else:
        confidence = "medium"

    return {
        "discarded": False,
        "name": name,
        "title": title,
        "email": email,
        "phone": phone,
        "linkedin_url": linkedin,
        "extraction_confidence": confidence,
        "source_page": source_page,
    }


def ollama_summary_and_tech(page_texts: list[str]) -> dict[str, Any] | None:
    """Return {summary, tech_stack_signals} or None on failure."""
    combined = " ".join(page_texts)[:6000].strip()
    if not combined:
        return None

    parsed = _generate_json(SUMMARY_EXTRACT_PROMPT.format(text=combined))
    if not parsed:
        return None

    summary = str(parsed.get("summary") or "").strip()
    if not summary:
        return None

    if not _summary_grounded_in_source(summary, combined):
        logger.warning("Ollama summary failed grounding check — using fallback")
        return None

    raw_mentions = parsed.get("tech_mentions") or []
    if not isinstance(raw_mentions, list):
        raw_mentions = []

    verified_signals: list[str] = []
    source_lower = combined.lower()
    for mention in raw_mentions:
        if not isinstance(mention, str):
            continue
        mention = mention.strip()
        if not mention:
            continue
        if mention.lower() not in source_lower:
            logger.warning("Ollama hallucinated tech mention — discarding: %r", mention)
            continue
        matched_label = None
        for label, pattern in _TECH_SIGNAL_PATTERNS:
            if pattern.search(mention) or pattern.search(combined):
                matched_label = label
                break
        if matched_label and matched_label not in verified_signals:
            verified_signals.append(matched_label)
        elif mention.lower() in source_lower and mention not in verified_signals:
            verified_signals.append(f"mentions {mention}")

    return {"summary": summary, "tech_stack_signals": verified_signals}


def _summary_grounded_in_source(summary: str, source: str) -> bool:
    """Require most content words in each sentence to appear in source."""
    source_words = set(re.findall(r"[a-z0-9]+", source.lower()))
    sentences = re.split(r"[.!?]+", summary)
    for sentence in sentences:
        words = [w for w in re.findall(r"[a-z0-9]+", sentence.lower()) if len(w) > 3]
        if not words:
            continue
        hits = sum(1 for w in words if w in source_words)
        if hits / len(words) < 0.35:
            return False
    return True


def ollama_available() -> bool:
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(_base_url())
            return response.status_code == 200
    except Exception:
        return False
