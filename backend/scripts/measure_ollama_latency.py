"""Measure single qwen3 extraction call latency on this machine."""

from __future__ import annotations

import time

import httpx

from app.services.ollama_client import EXECUTIVE_EXTRACT_PROMPT, SUMMARY_EXTRACT_PROMPT

SAMPLE_CONTAINER = (
    "Sam Vincent Co-Founder & Art Director Sam leads creative direction at Canada Create. "
    "Contact: sam@canadacreate.com LinkedIn: https://www.linkedin.com/in/samvincent"
)
SAMPLE_PAGE = (
    "Canada Create is a digital marketing agency in Toronto offering web design, SEO, "
    "and WordPress development for local businesses."
)


def _timed_call(label: str, prompt: str) -> float | None:
    print(f"\n--- {label} ---")
    t0 = time.perf_counter()
    try:
        r = httpx.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3",
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "think": False,
                "options": {"num_predict": 64, "temperature": 0},
            },
            timeout=300.0,
        )
        elapsed = time.perf_counter() - t0
        body = r.json()
        print(f"elapsed: {elapsed:.1f}s")
        print(f"eval_count: {body.get('eval_count')}")
        print(f"response: {(body.get('response') or '')[:200]}")
        return elapsed
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        print(f"FAILED after {elapsed:.1f}s: {exc}")
        return None


def main() -> None:
    exec_prompt = EXECUTIVE_EXTRACT_PROMPT.format(text=SAMPLE_CONTAINER)
    sum_prompt = SUMMARY_EXTRACT_PROMPT.format(text=SAMPLE_PAGE)

    exec_s = _timed_call("Executive extraction", exec_prompt)
    sum_s = _timed_call("Summary + tech extraction", sum_prompt)

    print("\n=== SUMMARY ===")
    for label, val in [("executive", exec_s), ("summary", sum_s)]:
        if val is None:
            print(f"{label}: FAILED")
        else:
            print(f"{label}: {val:.1f}s")


if __name__ == "__main__":
    main()
