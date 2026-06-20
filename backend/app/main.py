"""Global exception handlers and FastAPI app wiring."""

from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError as PostgrestAPIError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import companies, discovery, status, upload

logger = logging.getLogger("krowlive")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="KrowLive API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_body(*, detail: str, error_type: str, status_code: int, exc: Exception | None = None) -> dict:
    body: dict = {
        "detail": detail,
        "error_type": error_type,
        "status_code": status_code,
    }
    if settings.debug and exc is not None:
        body["message"] = str(exc)
        body["traceback"] = traceback.format_exc()
    return body


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(
            detail=str(exc.detail),
            error_type=type(exc).__name__,
            status_code=exc.status_code,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=_error_body(
            detail="Request validation failed",
            error_type=type(exc).__name__,
            status_code=422,
            exc=exc if settings.debug else None,
        )
        | ({"errors": exc.errors()} if settings.debug else {}),
    )


@app.exception_handler(PostgrestAPIError)
async def postgrest_exception_handler(request: Request, exc: PostgrestAPIError):
    logger.exception("Supabase/PostgREST error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error_body(
            detail=str(exc),
            error_type=type(exc).__name__,
            status_code=500,
            exc=exc,
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error_body(
            detail="Internal server error",
            error_type=type(exc).__name__,
            status_code=500,
            exc=exc,
        ),
    )


app.include_router(companies.router)
app.include_router(discovery.router)
app.include_router(upload.router)
app.include_router(status.router)


@app.get("/")
def root():
    return {"message": "KrowLive API is running", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}
