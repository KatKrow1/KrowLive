"""Quick Supabase connectivity test — run from backend/ after schema.sql is applied."""

from app.db import get_supabase


def main() -> None:
    db = get_supabase()

    row = {
        "name": "KrowLive Test Co",
        "website": "https://krowlive-test.example.com",
        "country": "CA",
        "city": "Toronto",
        "state": "Ontario",
        "category": "IT",
        "source": "csv_upload",
        "lead_score": 42,
        "summary": "Phase 3 connectivity test row.",
    }

    inserted = db.table("companies").upsert(row, on_conflict="website").execute()
    company = inserted.data[0]
    print("INSERT OK:", company["id"], company["name"])

    fetched = (
        db.table("companies")
        .select("*")
        .eq("website", row["website"])
        .single()
        .execute()
    )
    print("READ OK:", fetched.data["name"], f"score={fetched.data['lead_score']}")

    exec_row = {
        "company_id": company["id"],
        "name": "Jane Test",
        "title": "CEO",
        "email": "jane@krowlive-test.example.com",
        "consent_status": "unknown",
    }
    exec_inserted = db.table("executives").insert(exec_row).execute()
    print("EXECUTIVE OK:", exec_inserted.data[0]["name"], exec_inserted.data[0]["consent_status"])

    db.table("executives").delete().eq("company_id", company["id"]).execute()
    db.table("companies").delete().eq("id", company["id"]).execute()
    print("CLEANUP OK — test row removed")


if __name__ == "__main__":
    main()
