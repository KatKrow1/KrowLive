"""URL normalization helpers."""

from __future__ import annotations

from urllib.parse import urlparse


def canonical_website(url: str) -> str:
    parsed = urlparse(url.strip().split("?")[0].split("#")[0])
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.replace("www.", "").lower()
    path = parsed.path.rstrip("/")
    return f"{scheme}://{netloc}{path}"
