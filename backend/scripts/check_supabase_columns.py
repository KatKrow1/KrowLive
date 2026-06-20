"""Check companies table columns in Supabase."""

from __future__ import annotations

from app.db import get_supabase


def main() -> None:
    db = get_supabase()

    print("=== Probe social_links ===")
    try:
        r = db.table("companies").select("social_links").limit(1).execute()
        print("OK — sample:", r.data)
    except Exception as e:
        print("FAIL:", e)

    print("\n=== Probe tech_stack_signals ===")
    try:
        r = db.table("companies").select("tech_stack_signals").limit(1).execute()
        print("OK — sample:", r.data)
    except Exception as e:
        print("FAIL:", e)

    print("\n=== information_schema columns (if accessible via RPC) ===")
    # PostgREST doesn't expose information_schema; use a minimal insert/select probe
    for col in ("social_links", "tech_stack_signals"):
        try:
            r = db.table("companies").select(f"id,{col}").limit(0).execute()
            print(f"{col}: EXISTS (select succeeded)")
        except Exception as e:
            print(f"{col}: MISSING or error — {e}")


if __name__ == "__main__":
    main()
