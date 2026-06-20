"""Discovery integration test — Sydney + Melbourne (AU), waits for job completion."""

from __future__ import annotations

import json
import sys
import time

import httpx

URL = "http://127.0.0.1:8000/discovery/run"
STATUS_URL = "http://127.0.0.1:8000/status"
COMPANIES_URL = "http://127.0.0.1:8000/companies"
PAYLOAD = {
    "industry": "Media",
    "country": "AU",
    "states": ["NSW", "VIC"],
    "cities": ["Sydney", "Melbourne"],
    "max_results": 2,
}


def main() -> None:
    print("POST", URL)
    print("Payload:", json.dumps(PAYLOAD, indent=2))
    with httpx.Client(timeout=300.0) as client:
        r = client.post(URL, json=PAYLOAD)
        print("Start status:", r.status_code, r.text[:400])
        if r.status_code != 200:
            sys.exit(1)

        deadline = time.time() + 300
        final_status = None
        while time.time() < deadline:
            s = client.get(STATUS_URL).json()
            print(
                f"Job: {s.get('status')} — {s.get('message')} "
                f"({s.get('processed_items')}/{s.get('total_items')}) progress={s.get('progress')}%"
            )
            if s.get("status") in ("completed", "failed", "idle"):
                final_status = s
                break
            time.sleep(3)

        if not final_status:
            print("Timed out waiting for job")
            sys.exit(1)

        print("\n=== JOB RESULT ===")
        print(json.dumps(final_status, indent=2))

        if final_status.get("status") == "failed":
            sys.exit(1)

        companies = client.get(
            COMPANIES_URL,
            params={"country": "AU", "page": 1, "page_size": 10},
        ).json()
        items = companies.get("items") or companies.get("data") or []
        print("\n=== RECENT AU COMPANIES (up to 5) ===")
        for row in items[:5]:
            print(
                json.dumps(
                    {
                        "name": row.get("name"),
                        "city": row.get("city"),
                        "state": row.get("state"),
                        "country": row.get("country"),
                        "website": row.get("website"),
                        "phone": row.get("phone"),
                        "lead_score": row.get("lead_score"),
                        "executives": [
                            {
                                "name": e.get("name"),
                                "title": e.get("title"),
                                "extraction_confidence": e.get("extraction_confidence"),
                            }
                            for e in (row.get("executives") or [])[:3]
                        ],
                    },
                    indent=2,
                )
            )
            print("-" * 40)


if __name__ == "__main__":
    main()
