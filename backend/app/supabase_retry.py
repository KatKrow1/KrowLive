"""Retry helpers for transient Supabase / httpx connection failures."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

import httpx

logger = logging.getLogger("krowlive.db")

# HTTP/2 disconnects to Supabase often surface as RemoteProtocolError.
TRANSIENT_HTTP_ERRORS: tuple[type[BaseException], ...] = (
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.NetworkError,
)

T = TypeVar("T")


def supabase_write_retry(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    operation: str = "supabase write",
) -> T:
    """Run a Supabase write; retry transient httpx errors with exponential backoff."""
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except TRANSIENT_HTTP_ERRORS as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                operation,
                attempt,
                attempts,
                exc,
                delay,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc
