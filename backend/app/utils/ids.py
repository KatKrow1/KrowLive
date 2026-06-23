"""Parse hierarchy path/query identifiers."""

from __future__ import annotations

import re

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


def parse_numeric_id(value: str | int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise ValueError(f"Not a numeric id: {value!r}")


def is_country_code(value: str) -> bool:
    return value.upper() in {"CA", "AU"}


def is_numeric_id(value: str) -> bool:
    return value.isdigit()


def is_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value))
