"""Pydantic models for KrowLive API.

ID conventions (match production Supabase):
- countries.id, states.id, country_id, state_id → integer
- companies.id, executives.id, company_id → UUID string
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CountryCode = Literal["CA", "AU"]
CompanySource = Literal["google_places", "csv_upload"]
ConsentStatus = Literal["unknown", "opted_in", "opted_out"]
LeadStatusValue = Literal["new", "contacted", "replied", "not_interested"]
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
    source_url: str | None = None
    scraped_at: datetime | None = None


class CompanyResponse(BaseModel):
    id: str | None = None
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: CountryCode
    country_id: int | None = None
    state_id: int | None = None
    state_slug: str | None = None
    phone: str | None = None
    website: str
    google_rating: float | None = None
    google_review_count: int | None = None
    lead_score: int | None = None
    summary: str | None = None
    tech_stack_signals: list[str] = Field(default_factory=list)
    source: CompanySource = "google_places"
    social_links: SocialLinks = Field(default_factory=SocialLinks)
    executives: list[Executive] = Field(default_factory=list)
    last_scraped_at: datetime | None = None
    source_url: str | None = None
    lead_status: LeadStatusValue = "new"
    created_at: datetime | None = None
    updated_at: datetime | None = None


Company = CompanyResponse


class CountryResponse(BaseModel):
    id: int
    code: CountryCode
    name: str


class StateResponse(BaseModel):
    id: int
    name: str
    slug: str


class CompanySummaryResponse(BaseModel):
    id: str
    name: str
    lead_score: int | None = None
    lead_status: LeadStatusValue = "new"
    last_scraped_at: datetime | None = None
    website: str | None = None


CountryNode = CountryResponse
StateNode = StateResponse
CompanySummary = CompanySummaryResponse


class CompanyDetailResponse(BaseModel):
    company: CompanyResponse
    executives: list[Executive]


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


class EnrichmentResult(BaseModel):
    summary: str
    lead_score: int
    tech_stack_signals: list[str] = Field(default_factory=list)


class LeadStatusUpdate(BaseModel):
    status: LeadStatusValue


class BulkLeadStatusUpdate(BaseModel):
    company_ids: list[str] = Field(..., min_length=1)
    status: LeadStatusValue


class WebhookCreate(BaseModel):
    url: str


class WebhookResponse(BaseModel):
    id: str
    url: str
    active: bool
    created_at: datetime | None = None


class SavedSearchCreate(BaseModel):
    name: str
    industry: str
    country: CountryCode
    states: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    max_results: int = Field(default=5, ge=1, le=20)


class SavedSearchResponse(BaseModel):
    id: str
    name: str
    industry: str
    country: CountryCode
    states: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    max_results: int = 5
    created_at: datetime | None = None
    last_run_at: datetime | None = None
    last_result_count: int = 0


class SavedSearchRunResponse(BaseModel):
    saved_search_id: str
    new_companies: list[CompanySummaryResponse] = Field(default_factory=list)
    new_count: int = 0
    total_processed: int = 0
