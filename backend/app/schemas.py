"""Pydantic models for KrowLive API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

CountryCode = Literal["CA", "AU"]
CompanySource = Literal["google_places", "csv_upload"]
ConsentStatus = Literal["unknown", "opted_in", "opted_out"]
ExtractionConfidence = Literal["high", "medium", "low"]
JobStatus = Literal["idle", "running", "completed", "failed"]


class SocialLinks(BaseModel):
    linkedin: str | None = None
    twitter: str | None = None
    instagram: str | None = None
    facebook: str | None = None


class Executive(BaseModel):
    id: str | None = None
    company_id: str | None = None
    name: str
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    consent_status: ConsentStatus = "unknown"
    extraction_confidence: ExtractionConfidence = "low"


class Company(BaseModel):
    id: str | None = None
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: CountryCode
    phone: str | None = None
    website: str
    category: str | None = None
    google_rating: float | None = None
    google_review_count: int | None = None
    lead_score: int | None = None
    summary: str | None = None
    tech_stack_signals: list[str] = Field(default_factory=list)
    source: CompanySource = "google_places"
    social_links: SocialLinks = Field(default_factory=SocialLinks)
    executives: list[Executive] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DiscoveryRequest(BaseModel):
    industry: str
    country: CountryCode
    states: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    max_results: int = Field(default=5, ge=1, le=20)


class CsvUploadResult(BaseModel):
    rows_processed: int = 0
    rows_new: int = 0
    rows_updated: int = 0
    errors: list[str] = Field(default_factory=list)


class JobStatusResponse(BaseModel):
    id: str | None = None
    job_type: str = "discovery"
    status: JobStatus = "idle"
    progress: int = 0
    message: str | None = None
    total_items: int = 0
    processed_items: int = 0
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CompanyListResponse(BaseModel):
    items: list[Company]
    total: int
    page: int
    page_size: int


class EnrichmentResult(BaseModel):
    summary: str
    lead_score: int
    tech_stack_signals: list[str] = Field(default_factory=list)
