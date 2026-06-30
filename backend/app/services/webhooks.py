"""Fire outbound webhooks without blocking the discovery pipeline."""

from __future__ import annotations

import logging
import threading
from typing import Any

import httpx
from supabase import Client

logger = logging.getLogger("krowlive.webhooks")

WEBHOOK_TIMEOUT = 5.0


def _post_webhook(url: str, payload: dict[str, Any]) -> None:
    try:
        with httpx.Client(timeout=WEBHOOK_TIMEOUT) as client:
            client.post(url, json=payload)
    except Exception as exc:
        logger.warning("Webhook delivery failed for %s: %s", url, exc)


def notify_new_company(db: Client, company_row: dict[str, Any]) -> None:
    """Fire active webhooks in a background thread — never raises."""
    try:
        hooks = (
            db.table("webhooks")
            .select("id, url")
            .eq("active", True)
            .execute()
            .data
            or []
        )
        if not hooks:
            return
        payload = {
            "event": "company.created",
            "company": {
                k: company_row.get(k)
                for k in (
                    "id",
                    "name",
                    "website",
                    "city",
                    "state",
                    "country",
                    "phone",
                    "lead_score",
                    "summary",
                    "source",
                )
            },
        }
        for hook in hooks:
            url = hook.get("url")
            if url:
                threading.Thread(
                    target=_post_webhook,
                    args=(url, payload),
                    daemon=True,
                ).start()
    except Exception as exc:
        logger.warning("Webhook notification setup failed: %s", exc)
