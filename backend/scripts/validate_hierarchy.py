"""Validate hierarchy integrity after migration."""

from __future__ import annotations

import json
import sys
from collections import Counter

from app.db import get_supabase


def main() -> None:
    db = get_supabase()

    companies = db.table("companies").select("id, country_id, state_id").execute().data or []
    missing_country_fk = sum(1 for c in companies if not c.get("country_id"))
    missing_state_fk = sum(1 for c in companies if not c.get("state_id"))

    company_ids = {c["id"] for c in companies}
    executives = db.table("executives").select("id, company_id").execute().data or []
    orphan_executives = sum(
        1 for e in executives if e.get("company_id") not in company_ids
    )

    countries = db.table("countries").select("id, code").execute().data or []
    duplicate_countries = sum(1 for _, n in Counter(c["code"] for c in countries).items() if n > 1)

    states = db.table("states").select("id, country_id, slug").execute().data or []
    duplicate_states = sum(
        1 for _, n in Counter((s["country_id"], s["slug"]) for s in states).items() if n > 1
    )

    ok = (
        missing_country_fk == 0
        and missing_state_fk == 0
        and orphan_executives == 0
        and duplicate_countries == 0
        and duplicate_states == 0
    )

    report = {
        "status": "ok" if ok else "issues_found",
        "missing_country_fk": missing_country_fk,
        "missing_state_fk": missing_state_fk,
        "orphan_executives": orphan_executives,
        "duplicate_countries": duplicate_countries,
        "duplicate_states": duplicate_states,
    }

    print(json.dumps(report, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
