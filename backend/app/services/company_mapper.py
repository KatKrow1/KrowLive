"""Map database rows to API Company models."""

from __future__ import annotations

from typing import Any

from app.schemas import Company, Executive, SocialLinks


def parse_social_links(raw: Any) -> SocialLinks:
    if not raw or not isinstance(raw, dict):
        return SocialLinks()
    return SocialLinks(
        linkedin=raw.get("linkedin"),
        twitter=raw.get("twitter"),
        instagram=raw.get("instagram"),
        facebook=raw.get("facebook"),
    )


def row_to_company(row: dict[str, Any], *, include_executives: bool = True) -> Company:
    data = dict(row)
    execs = data.pop("executives", []) or [] if include_executives else []
    countries = data.pop("countries", None) or {}
    states = data.pop("states", None) or {}
    social = parse_social_links(data.get("social_links"))
    signals = data.get("tech_stack_signals") or []
    if not isinstance(signals, list):
        signals = []

    country_code = data.get("country")
    if countries and countries.get("code"):
        country_code = countries["code"]

    state_name = data.get("state")
    state_slug = None
    if states:
        state_name = states.get("name") or state_name
        state_slug = states.get("slug")

    return Company(
        **{
            k: v
            for k, v in data.items()
            if k
            not in {
                "social_links",
                "tech_stack_signals",
                "countries",
                "states",
                "category",
                "category_id",
                "country",
                "state",
            }
        },
        country=country_code,
        state=state_name,
        state_slug=state_slug,
        social_links=social,
        tech_stack_signals=[str(s) for s in signals],
        executives=[
            Executive(
                id=e.get("id"),
                company_id=e.get("company_id"),
                name=e.get("name"),
                title=e.get("title"),
                email=e.get("email"),
                phone=e.get("phone"),
                linkedin_url=e.get("linkedin_url"),
                consent_status=e.get("consent_status", "unknown"),
                extraction_confidence=e.get("extraction_confidence", "low"),
            )
            for e in execs
        ]
        if include_executives
        else [],
    )


COMPANY_SELECT = "*, countries(code, name), states(name, slug)"
COMPANY_DETAIL_SELECT = f"{COMPANY_SELECT}, executives(*)"
