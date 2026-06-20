"""Shared targets for Phase 4 / Phase 5 media company standalone tests."""

from __future__ import annotations

INDUSTRY = "media companies"
MAX_RESULTS_PER_CITY = 3

MEDIA_CITIES: list[dict[str, str]] = [
    # Canada
    {"city": "Toronto", "state": "Ontario", "country": "CA", "label": "Toronto, ON (CA)"},
    {"city": "Vancouver", "state": "British Columbia", "country": "CA", "label": "Vancouver, BC (CA)"},
    {"city": "Montreal", "state": "Quebec", "country": "CA", "label": "Montreal, QC (CA)"},
    {"city": "Calgary", "state": "Alberta", "country": "CA", "label": "Calgary, AB (CA)"},
    {"city": "Ottawa", "state": "Ontario", "country": "CA", "label": "Ottawa, ON (CA)"},
    # Australia
    {"city": "Sydney", "state": "NSW", "country": "AU", "label": "Sydney, NSW (AU)"},
    {"city": "Melbourne", "state": "VIC", "country": "AU", "label": "Melbourne, VIC (AU)"},
    {"city": "Brisbane", "state": "QLD", "country": "AU", "label": "Brisbane, QLD (AU)"},
    {"city": "Perth", "state": "WA", "country": "AU", "label": "Perth, WA (AU)"},
    {"city": "Adelaide", "state": "SA", "country": "AU", "label": "Adelaide, SA (AU)"},
]
