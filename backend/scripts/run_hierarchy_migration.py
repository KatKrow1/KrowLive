"""Apply hierarchy migration via Supabase REST (DDL sections need SQL Editor)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.db import get_supabase
from app.services.hierarchy_migration import migrate_all_companies

MIGRATION = Path(__file__).resolve().parents[1] / "app" / "sql" / "migration_hierarchy.sql"


def main() -> None:
    db = get_supabase()
    try:
        db.table("countries").select("id").limit(1).execute()
    except Exception:
        print(
            "Hierarchy tables not found. Run migration_hierarchy.sql in Supabase SQL Editor first.\n"
            f"File: {MIGRATION}",
            file=sys.stderr,
        )
        sys.exit(1)

    report = migrate_all_companies(db)
    print(json.dumps(report.to_dict(), indent=2))
    sys.exit(1 if report.errors else 0)


if __name__ == "__main__":
    main()
