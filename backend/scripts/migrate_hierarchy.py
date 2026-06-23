"""Run full hierarchy data migration."""

from __future__ import annotations

import json
import sys

from app.db import get_supabase
from app.services.hierarchy_migration import migrate_all_companies


def main() -> None:
    db = get_supabase()

    try:
        db.table("countries").select("id").limit(1).execute()
    except Exception:
        print(
            "ERROR: Hierarchy tables missing. Run backend/app/sql/migration_hierarchy.sql "
            "in Supabase SQL Editor first.",
            file=sys.stderr,
        )
        sys.exit(1)

    countries = db.table("countries").select("id,code,name").execute().data or []

    print("Countries found:", len(countries))
    print(countries)

    if len(countries) == 0:
        print(
            "ERROR: countries table is empty and cannot be seeded via REST (RLS).",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Starting hierarchy migration...")

    report = migrate_all_companies(db)

    print(json.dumps(report.to_dict(), indent=2))

    if report.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()