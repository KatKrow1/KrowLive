"""Webhook integration endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.db import get_supabase
from app.schemas import WebhookCreate, WebhookResponse

logger = logging.getLogger("krowlive.integrations")

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/webhooks", response_model=list[WebhookResponse])
def list_webhooks():
    rows = get_supabase().table("webhooks").select("*").order("created_at").execute().data or []
    return [
        WebhookResponse(
            id=r["id"],
            url=r["url"],
            active=r.get("active", True),
            created_at=r.get("created_at"),
        )
        for r in rows
    ]


@router.post("/webhook", response_model=WebhookResponse)
def create_webhook(body: WebhookCreate):
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="Webhook URL must start with http:// or https://")
    result = (
        get_supabase()
        .table("webhooks")
        .insert({"url": url, "active": True})
        .execute()
    )
    row = (result.data or [None])[0]
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create webhook")
    return WebhookResponse(
        id=row["id"],
        url=row["url"],
        active=row.get("active", True),
        created_at=row.get("created_at"),
    )


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: str):
    get_supabase().table("webhooks").delete().eq("id", webhook_id).execute()
    return {"deleted": webhook_id}


@router.patch("/webhooks/{webhook_id}/toggle")
def toggle_webhook(webhook_id: str, active: bool = True):
    db = get_supabase()
    db.table("webhooks").update({"active": active}).eq("id", webhook_id).execute()
    return {"id": webhook_id, "active": active}
