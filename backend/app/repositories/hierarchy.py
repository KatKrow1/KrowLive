"""Persistence layer for countries, states, and companies."""

from __future__ import annotations

import logging
from typing import Any

from supabase import Client

from app.services.normalization import normalize_country, normalize_state
from app.utils.slug import slugify

logger = logging.getLogger("krowlive.hierarchy")

Id = int | str


class HierarchyRepository:
    def __init__(self, db: Client) -> None:
        self.db = db

    def list_countries(self) -> list[dict[str, Any]]:
        return self.db.table("countries").select("id, code, name").order("name").execute().data or []

    def list_states(self, country_id: Id) -> list[dict[str, Any]]:
        rows = (
            self.db.table("states")
            .select("id, name, slug")
            .eq("country_id", country_id)
            .order("name")
            .execute()
            .data
            or []
        )
        if not rows:
            return []

        companies = (
            self.db.table("companies")
            .select("state_id")
            .eq("country_id", country_id)
            .execute()
            .data
            or []
        )
        counts: dict[Any, int] = {}
        for row in companies:
            sid = row.get("state_id")
            if sid is not None:
                counts[sid] = counts.get(sid, 0) + 1

        result = [s for s in rows if counts.get(s["id"], 0) > 0]
        result.sort(key=lambda s: -counts.get(s["id"], 0))
        return result

    def list_companies(self, state_id: Id) -> list[dict[str, Any]]:
        select = "id, name, website, lead_score, last_scraped_at, lead_status(status)"
        try:
            rows = (
                self.db.table("companies")
                .select(select)
                .eq("state_id", state_id)
                .order("name")
                .execute()
                .data
                or []
            )
        except Exception:
            rows = (
                self.db.table("companies")
                .select("id, name, website, lead_score")
                .eq("state_id", state_id)
                .order("name")
                .execute()
                .data
                or []
            )
        result = []
        for r in rows:
            ls = r.get("lead_status") or {}
            result.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "website": r.get("website"),
                    "lead_score": r.get("lead_score"),
                    "last_scraped_at": r.get("last_scraped_at"),
                    "lead_status": ls.get("status", "new") if isinstance(ls, dict) else "new",
                }
            )
        return result

    def get_company(self, company_id: Id) -> dict[str, Any] | None:
        from app.services.company_mapper import COMPANY_DETAIL_SELECT

        result = (
            self.db.table("companies")
            .select(COMPANY_DETAIL_SELECT)
            .eq("id", company_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def get_country_by_id(self, country_id: Id) -> dict[str, Any] | None:
        result = self.db.table("countries").select("*").eq("id", country_id).limit(1).execute()
        return (result.data or [None])[0]

    def get_country_by_code(self, code: str) -> dict[str, Any] | None:
        result = self.db.table("countries").select("*").eq("code", code.upper()).limit(1).execute()
        return (result.data or [None])[0]

    def get_state_by_id(self, state_id: Id) -> dict[str, Any] | None:
        result = self.db.table("states").select("*").eq("id", state_id).limit(1).execute()
        return (result.data or [None])[0]

    def get_state_by_slug(self, country_id: Id, slug: str) -> dict[str, Any] | None:
        result = (
            self.db.table("states")
            .select("*")
            .eq("country_id", country_id)
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        return (result.data or [None])[0]

    def find_or_create_country(self, code: str, *, name: str | None = None) -> dict[str, Any]:
        code, default_name = normalize_country(code)
        name = name or default_name
        existing = self.get_country_by_code(code)
        if existing:
            return existing
        result = self.db.table("countries").insert({"code": code, "name": name}).execute()
        if result.data:
            return result.data[0]
        return self.get_country_by_code(code) or {"code": code, "name": name}

    def find_or_create_state(
        self,
        country_id: Id,
        *,
        name: str,
        country_code: str,
        state_code: str | None = None,
    ) -> dict[str, Any]:
        _sc, name = normalize_state(name, country_code)
        state_code = state_code or _sc
        slug = slugify(name)
        existing = self.get_state_by_slug(country_id, slug)
        if existing:
            return existing
        payload: dict[str, Any] = {"country_id": country_id, "name": name, "slug": slug}
        if state_code:
            payload["code"] = state_code
        result = self.db.table("states").insert(payload).execute()
        if result.data:
            return result.data[0]
        return self.get_state_by_slug(country_id, slug) or payload

    def resolve_hierarchy(
        self,
        *,
        country_code: str,
        state_name: str,
        state_code: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        country = self.find_or_create_country(country_code)
        state = self.find_or_create_state(
            country["id"],
            name=state_name,
            country_code=country["code"],
            state_code=state_code,
        )
        return country, state
