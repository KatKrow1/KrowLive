"""Migrate legacy company rows into country_id + state_id FKs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from supabase import Client

from app.repositories.hierarchy import HierarchyRepository
from app.services.normalization import normalize_country, normalize_state
from app.supabase_retry import supabase_write_retry

logger = logging.getLogger("krowlive.migration")


@dataclass
class MigrationReport:
    companies_processed: int = 0
    companies_updated: int = 0
    companies_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "companies_processed": self.companies_processed,
            "companies_updated": self.companies_updated,
            "companies_skipped": self.companies_skipped,
            "errors": self.errors[:50],
        }


def migrate_all_companies(db: Client, *, batch_size: int = 100) -> MigrationReport:
    """Link every company to country_id and state_id. Never deletes rows."""
    report = MigrationReport()
    repo = HierarchyRepository(db)
    offset = 0

    while True:
        rows = (
            db.table("companies")
            .select("id, name, country, state, country_id, state_id")
            .range(offset, offset + batch_size - 1)
            .execute()
            .data
            or []
        )
        if not rows:
            break

        for row in rows:
            report.companies_processed += 1
            try:
                country_code, country_name = normalize_country(str(row.get("country") or "CA"))
                _state_code, state_name = normalize_state(row.get("state"), country_code)

                country = repo.find_or_create_country(country_code, name=country_name)
                state = repo.find_or_create_state(
                    country["id"],
                    name=state_name,
                    country_code=country_code,
                )

                payload = {
                    "country_id": country["id"],
                    "state_id": state["id"],
                    "country": country_code,
                    "state": state_name,
                }

                if (
                    row.get("country_id") == payload["country_id"]
                    and row.get("state_id") == payload["state_id"]
                    and row.get("state") == payload["state"]
                ):
                    report.companies_skipped += 1
                    continue

                supabase_write_retry(
                    lambda p=payload, cid=row["id"]: db.table("companies")
                    .update(p)
                    .eq("id", cid)
                    .execute(),
                    operation=f"migrate company {row.get('name')}",
                )
                report.companies_updated += 1
            except Exception as exc:
                msg = f"{row.get('name', row.get('id'))}: {exc}"
                logger.exception(msg)
                report.errors.append(msg)

        if len(rows) < batch_size:
            break
        offset += batch_size

    return report
