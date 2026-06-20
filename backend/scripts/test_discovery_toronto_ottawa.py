"""Discovery integration test — Toronto + Ottawa, waits for job completion."""

from __future__ import annotations

import json
import sys
import time

import httpx

URL = "http://127.0.0.1:8000/discovery/run"
STATUS_URL = "http://127.0.0.1:8000/status"
PAYLOAD = {
    "industry": "Media",
    "country": "CA",
    "states": ["Ontario"],
    "cities": ["Toronto", "Ottawa"],
    "max_results": 1,
}


def main() -> None:
    print("POST", URL)
    print("Payload:", json.dumps(PAYLOAD))
    with httpx.Client(timeout=120.0) as client:
        r = client.post(URL, json=PAYLOAD)
        print("Start status:", r.status_code, r.text[:300])
        if r.status_code != 200:
            sys.exit(1)

        deadline = time.time() + 180
        while time.time() < deadline:
            s = client.get(STATUS_URL).json()
            print(f"Job: {s.get('status')} — {s.get('message')} ({s.get('processed_items')}/{s.get('total_items')})")
            if s.get("status") in ("completed", "failed", "idle"):
                if s.get("status") == "failed":
                    print("FAILED:", s.get("error"))
                    sys.exit(1)
                if s.get("status") == "completed":
                    print("SUCCESS:", json.dumps(s, indent=2))
                    return
            time.sleep(3)

    print("Timed out waiting for job")
    sys.exit(1)


if __name__ == "__main__":
    main()
