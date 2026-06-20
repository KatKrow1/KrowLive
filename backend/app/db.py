from functools import lru_cache

import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.config import settings

# Force HTTP/1.1 — HTTP/2 connections to Supabase can drop intermittently on some networks.
_HTTPX_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _build_httpx_client() -> httpx.Client:
    return httpx.Client(http2=False, timeout=_HTTPX_TIMEOUT)


@lru_cache
def get_supabase() -> Client:
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in backend/.env")
    options = SyncClientOptions(httpx_client=_build_httpx_client())
    return create_client(settings.supabase_url, settings.supabase_key, options=options)
