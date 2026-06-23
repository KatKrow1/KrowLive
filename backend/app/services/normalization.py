"""Canonical names and codes for countries and states."""

from __future__ import annotations

import re

COUNTRY_ALIASES: dict[str, tuple[str, str]] = {
    "ca": ("CA", "Canada"),
    "can": ("CA", "Canada"),
    "canada": ("CA", "Canada"),
    "au": ("AU", "Australia"),
    "aus": ("AU", "Australia"),
    "australia": ("AU", "Australia"),
    "us": ("US", "United States"),
    "usa": ("US", "United States"),
    "united states": ("US", "United States"),
    "united states of america": ("US", "United States"),
}

CA_STATE_ALIASES: dict[str, tuple[str, str]] = {
    "on": ("ON", "Ontario"),
    "ontario": ("ON", "Ontario"),
    "bc": ("BC", "British Columbia"),
    "british columbia": ("BC", "British Columbia"),
    "ab": ("AB", "Alberta"),
    "alberta": ("AB", "Alberta"),
    "qc": ("QC", "Quebec"),
    "quebec": ("QC", "Quebec"),
    "mb": ("MB", "Manitoba"),
    "manitoba": ("MB", "Manitoba"),
    "sk": ("SK", "Saskatchewan"),
    "saskatchewan": ("SK", "Saskatchewan"),
    "ns": ("NS", "Nova Scotia"),
    "nova scotia": ("NS", "Nova Scotia"),
    "nb": ("NB", "New Brunswick"),
    "new brunswick": ("NB", "New Brunswick"),
    "nl": ("NL", "Newfoundland and Labrador"),
    "pei": ("PE", "Prince Edward Island"),
}

AU_STATE_ALIASES: dict[str, tuple[str, str]] = {
    "nsw": ("NSW", "New South Wales"),
    "new south wales": ("NSW", "New South Wales"),
    "vic": ("VIC", "Victoria"),
    "victoria": ("VIC", "Victoria"),
    "qld": ("QLD", "Queensland"),
    "queensland": ("QLD", "Queensland"),
    "wa": ("WA", "Western Australia"),
    "western australia": ("WA", "Western Australia"),
    "sa": ("SA", "South Australia"),
    "south australia": ("SA", "South Australia"),
    "tas": ("TAS", "Tasmania"),
    "tasmania": ("TAS", "Tasmania"),
    "act": ("ACT", "Australian Capital Territory"),
    "australian capital territory": ("ACT", "Australian Capital Territory"),
    "nt": ("NT", "Northern Territory"),
    "northern territory": ("NT", "Northern Territory"),
}


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def normalize_country(raw: str | None) -> tuple[str, str]:
    from app.utils.slug import slugify

    key = _clean(raw).lower()
    if key in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[key]
    if len(key) == 2:
        return key.upper(), key.upper()
    if key:
        return slugify(key).upper()[:2] or "CA", _clean(raw).title()
    return "CA", "Canada"


def normalize_state(raw: str | None, country_code: str) -> tuple[str | None, str]:
    key = _clean(raw).lower() or "unknown"
    aliases = AU_STATE_ALIASES if country_code == "AU" else CA_STATE_ALIASES
    if key in aliases:
        code, name = aliases[key]
        return code, name
    name = _clean(raw).title() if raw else "Unknown"
    return None, name
