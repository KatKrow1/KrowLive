"""Company queries, export, and lead status helpers."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

from supabase import Client

from app.services.company_mapper import row_to_company
from app.utils.url import canonical_website


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CompanyRepository:
    def __init__(self, db: Client) -> None:
        self.db = db

    def ensure_lead_status(self, company_id: str, *, status: str = "new") -> None:
        try:
            self.db.table("lead_status").upsert(
                {"company_id": company_id, "status": status, "updated_at": _now_iso()},
                on_conflict="company_id",
            ).execute()
        except Exception:
            pass

    def get_lead_status(self, company_id: str) -> str:
        row = (
            self.db.table("lead_status")
            .select("status")
            .eq("company_id", company_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        return row[0]["status"] if row else "new"

    def set_lead_status(self, company_id: str, status: str) -> dict[str, Any] | None:
        result = (
            self.db.table("lead_status")
            .upsert(
                {"company_id": company_id, "status": status, "updated_at": _now_iso()},
                on_conflict="company_id",
            )
            .execute()
        )
        return (result.data or [None])[0]

    def bulk_set_lead_status(self, company_ids: list[str], status: str) -> int:
        rows = [
            {"company_id": cid, "status": status, "updated_at": _now_iso()} for cid in company_ids
        ]
        if not rows:
            return 0
        self.db.table("lead_status").upsert(rows, on_conflict="company_id").execute()
        return len(rows)

    def list_companies_filtered(
        self,
        *,
        country: str | None = None,
        state: str | None = None,
        state_id: int | None = None,
        industry: str | None = None,
        min_score: int | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.db.table("companies").select(
            "id, name, website, city, state, country, phone, lead_score, summary, "
            "source, last_scraped_at, source_url, created_at, "
            "lead_status(status), executives(name, title, email, phone, linkedin_url)"
        )
        if country:
            query = query.eq("country", country.upper())
        if state:
            query = query.eq("state", state)
        if state_id is not None:
            query = query.eq("state_id", state_id)
        if min_score is not None:
            query = query.gte("lead_score", min_score)
        rows = query.order("name").execute().data or []

        if status:
            rows = [
                r
                for r in rows
                if (r.get("lead_status") or {}).get("status", "new") == status
            ]
        if industry:
            needle = industry.lower()
            rows = [
                r
                for r in rows
                if needle in (r.get("summary") or "").lower()
                or needle in (r.get("name") or "").lower()
            ]
        return rows

    def export_csv(
        self,
        *,
        country: str | None = None,
        state: str | None = None,
        state_id: int | None = None,
        industry: str | None = None,
        min_score: int | None = None,
        status: str | None = None,
    ) -> str:
        rows = self.list_companies_filtered(
            country=country,
            state=state,
            state_id=state_id,
            industry=industry,
            min_score=min_score,
            status=status,
        )
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "company_id",
                "name",
                "website",
                "city",
                "state",
                "country",
                "phone",
                "lead_score",
                "lead_status",
                "last_scraped_at",
                "summary",
                "executive_names",
                "executive_titles",
                "executive_emails",
                "executive_phones",
                "executive_linkedin",
            ]
        )
        for row in rows:
            ls = row.get("lead_status") or {}
            execs = row.get("executives") or []
            writer.writerow(
                [
                    row.get("id"),
                    row.get("name"),
                    row.get("website"),
                    row.get("city"),
                    row.get("state"),
                    row.get("country"),
                    row.get("phone"),
                    row.get("lead_score"),
                    ls.get("status", "new"),
                    row.get("last_scraped_at"),
                    (row.get("summary") or "")[:500],
                    "; ".join(e.get("name") or "" for e in execs),
                    "; ".join(e.get("title") or "" for e in execs),
                    "; ".join(e.get("email") or "" for e in execs if e.get("email")),
                    "; ".join(e.get("phone") or "" for e in execs if e.get("phone")),
                    "; ".join(e.get("linkedin_url") or "" for e in execs if e.get("linkedin_url")),
                ]
            )
        return buf.getvalue()

    def snapshot_websites(self) -> set[str]:
        rows = self.db.table("companies").select("website").execute().data or []
        return {canonical_website(r["website"]) for r in rows if r.get("website")}

    def companies_by_websites(self, websites: set[str]) -> list[dict[str, Any]]:
        if not websites:
            return []
        rows = self.db.table("companies").select("id, name, website").execute().data or []
        return [r for r in rows if canonical_website(r.get("website", "")) in websites]
