"""Hierarchy navigation — countries → states → companies."""

from __future__ import annotations

from typing import Any

from supabase import Client

from app.repositories.hierarchy import HierarchyRepository


class HierarchyService:
    def __init__(self, db: Client) -> None:
        self.db = db
        self.repo = HierarchyRepository(db)

    def list_countries(self) -> list[dict[str, Any]]:
        return [
            {"id": c["id"], "code": c["code"], "name": c["name"]}
            for c in self.repo.list_countries()
        ]

    def list_states_for_country(self, country_id: int | str) -> list[dict[str, Any]]:
        return self.repo.list_states(country_id)

    def list_companies_for_state(self, state_id: int | str) -> list[dict[str, Any]]:
        return self.repo.list_companies(state_id)

    def dashboard_stats(self, country_code: str | None = None) -> dict[str, Any]:
        countries = self.repo.list_countries()
        by_code: dict[str, dict] = {c["code"]: c for c in countries}

        def count_for(code: str) -> int:
            country = by_code.get(code)
            if not country:
                return 0
            resp = (
                self.db.table("companies")
                .select("id", count="exact")
                .eq("country_id", country["id"])
                .execute()
            )
            return resp.count or 0

        canada_count = count_for("CA")
        australia_count = count_for("AU")
        total = canada_count + australia_count

        query = self.db.table("companies").select("lead_score")
        if country_code:
            country = by_code.get(country_code)
            if country:
                query = query.eq("country_id", country["id"])
        rows = query.execute().data or []

        scores = [int(r["lead_score"]) for r in rows if r.get("lead_score") is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0

        chart: list[dict[str, Any]] = []
        if country_code:
            country = by_code.get(country_code)
            if country:
                state_rows = self.list_states_for_country(country["id"])
                state_ids = [s["id"] for s in state_rows]
                if state_ids:
                    company_rows = (
                        self.db.table("companies")
                        .select("state_id")
                        .eq("country_id", country["id"])
                        .in_("state_id", state_ids)
                        .execute()
                        .data
                        or []
                    )
                    counts: dict[Any, int] = {}
                    for row in company_rows:
                        sid = row.get("state_id")
                        if sid is not None:
                            counts[sid] = counts.get(sid, 0) + 1
                    chart = [
                        {"state": s["name"], "count": counts.get(s["id"], 0)}
                        for s in state_rows
                    ]

        return {
            "total_companies": total,
            "avg_lead_score": avg_score,
            "canada_count": canada_count,
            "australia_count": australia_count,
            "chart_by_state": chart,
        }
