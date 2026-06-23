"""Direct test of POST /discovery/run — captures full response."""

from __future__ import annotations

import json
import sys
import traceback

import httpx

URL = "http://127.0.0.1:8000/discovery/run"
PAYLOAD = {
    "industry": "Media",
    "country": "CA",
    "states": ["Ontario"],
    "cities": ["Toronto"],
    "max_results": 1,
}


def main() -> None:
    print("POST", URL)
    print("Payload:", json.dumps(PAYLOAD))
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(URL, json=PAYLOAD)
        print("Status:", r.status_code)
        print("Headers:", dict(r.headers))
        print("Body (raw):", repr(r.text))
        if r.text:
            try:
                print("Body (json):", json.dumps(r.json(), indent=2))
            except Exception:
                pass
    except Exception as exc:
        print("REQUEST FAILED:", exc)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
