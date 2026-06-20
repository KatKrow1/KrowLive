"""Google Places API connector — discover businesses by industry and location."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import googlemaps
from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError

from app.config import settings

DETAIL_FIELDS = [
    "name",
    "formatted_address",
    "address_component",
    "formatted_phone_number",
    "international_phone_number",
    "website",
    "rating",
    "user_ratings_total",
    "type",
    "place_id",
]

INDUSTRY_KEYWORDS: dict[str, str] = {
    "media": "media company production studio broadcasting",
    "media companies": "media company production studio broadcasting",
    "media company": "media company production studio broadcasting",
    "marketing": "marketing agency digital marketing firm",
    "marketing agency": "marketing agency digital marketing firm",
    "advertising": "advertising agency ad agency creative agency",
    "advertising agency": "advertising agency ad agency creative agency",
    "pr firm": "public relations firm PR agency communications agency",
    "pr": "public relations firm PR agency communications agency",
    "public relations": "public relations firm PR agency communications agency",
}


@dataclass
class PlaceResult:
    place_id: str
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str = "CA"
    phone: str | None = None
    website: str | None = None
    category: str | None = None
    google_rating: float | None = None
    google_review_count: int | None = None
    raw_types: list[str] = field(default_factory=list)


def _client() -> googlemaps.Client:
    if not settings.google_places_api_key:
        raise RuntimeError("GOOGLE_PLACES_API_KEY must be set in backend/.env")
    return googlemaps.Client(key=settings.google_places_api_key)


def _industry_query(industry: str) -> str:
    key = industry.strip().lower()
    return INDUSTRY_KEYWORDS.get(key, industry)


def _parse_address_components(components: list[dict[str, Any]]) -> tuple[str | None, str | None, str]:
    city = state = None
    country = "CA"

    for comp in components:
        types = comp.get("types", [])
        if "locality" in types:
            city = comp.get("long_name")
        elif "administrative_area_level_1" in types:
            state = comp.get("long_name")
        elif "country" in types:
            country = comp.get("short_name", "CA")

    return city, state, country


def _normalize_website(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _primary_category(types: list[str]) -> str | None:
    skip = {"point_of_interest", "establishment", "political", "geocode"}
    for t in types:
        if t not in skip:
            return t.replace("_", " ").title()
    return None


def geocode_location(
    client: googlemaps.Client,
    *,
    city: str,
    state: str,
    country: str = "CA",
) -> tuple[float, float]:
    country_name = "Canada" if country == "CA" else "Australia"
    query = f"{city}, {state}, {country_name}"
    results = client.geocode(query)
    if not results:
        raise ValueError(f"Could not geocode location: {query}")
    loc = results[0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def search_places(
    *,
    industry: str,
    city: str,
    state: str,
    country: str = "CA",
    max_results: int = 20,
) -> list[PlaceResult]:
    """Find businesses via text search + nearby search, enrich with place details."""
    client = _client()
    keyword = _industry_query(industry)
    country_name = "Canada" if country == "CA" else "Australia"
    lat, lng = geocode_location(client, city=city, state=state, country=country)

    seen_ids: set[str] = set()
    candidates: list[dict[str, Any]] = []

    text_query = f"{keyword} in {city}, {state}, {country_name}"
    text_response = client.places(query=text_query)
    candidates.extend(text_response.get("results", []))

    nearby_response = client.places_nearby(
        location=(lat, lng),
        keyword=keyword,
        radius=15_000,
    )
    candidates.extend(nearby_response.get("results", []))

    results: list[PlaceResult] = []
    for item in candidates:
        place_id = item.get("place_id")
        if not place_id or place_id in seen_ids:
            continue
        seen_ids.add(place_id)

        try:
            detail_resp = client.place(place_id, fields=DETAIL_FIELDS)
        except (ApiError, HTTPError, Timeout, TransportError):
            continue

        detail = detail_resp.get("result", {})
        components = detail.get("address_components", [])
        parsed_city, parsed_state, parsed_country = _parse_address_components(components)

        if parsed_country and parsed_country != country:
            continue

        types = detail.get("type") or item.get("types") or []
        if isinstance(types, str):
            types = [types]
        phone = detail.get("formatted_phone_number") or detail.get("international_phone_number")

        results.append(
            PlaceResult(
                place_id=place_id,
                name=detail.get("name") or item.get("name", "Unknown"),
                address=detail.get("formatted_address"),
                city=parsed_city or city,
                state=parsed_state or state,
                country=parsed_country or country,
                phone=phone,
                website=_normalize_website(detail.get("website")),
                category=_primary_category(types) or industry.title(),
                google_rating=detail.get("rating"),
                google_review_count=detail.get("user_ratings_total"),
                raw_types=list(types),
            )
        )

        if len(results) >= max_results:
            break

    return results


def place_result_to_company_dict(place: PlaceResult, industry: str) -> dict[str, Any]:
    """Map a PlaceResult to a companies-table-compatible dict."""
    website = place.website or f"https://maps.google.com/?place_id={place.place_id}"
    return {
        "name": place.name,
        "address": place.address,
        "city": place.city,
        "state": place.state,
        "country": place.country,
        "phone": place.phone,
        "website": website,
        "category": place.category or industry,
        "google_rating": place.google_rating,
        "google_review_count": place.google_review_count,
        "source": "google_places",
    }
