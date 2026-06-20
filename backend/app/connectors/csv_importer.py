"""CSV import with flexible column mapping.

Admin-only: re-uploading the same CSV upserts on the unique `website` column,
re-scrapes each site, and re-runs enrichment — no duplicate rows.
"""

from __future__ import annotations

import io
from typing import Any

import pandas as pd
from supabase import Client

from app.connectors.google_places import _normalize_website
from app.schemas import CsvUploadResult
from app.services.company_pipeline import canonical_website, process_company_record

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("name", "company", "company name", "company_name", "business", "business name", "organization"),
    "website": ("website", "url", "web", "site", "domain", "company website", "company_url"),
    "email": ("email", "e-mail", "contact email", "contact_email", "email address"),
    "phone": ("phone", "telephone", "tel", "mobile", "phone number", "contact phone"),
    "city": ("city", "town", "municipality"),
    "state": ("state", "province", "region", "state/province", "state_province"),
    "country": ("country", "country code", "country_code"),
    "category": ("category", "industry", "sector", "type", "business type"),
    "address": ("address", "street", "street address", "full address"),
}


def _normalize_header(header: str) -> str:
    return header.strip().lower().replace("_", " ")


def _map_columns(df: pd.DataFrame) -> dict[str, str | None]:
    mapping: dict[str, str | None] = {field: None for field in COLUMN_ALIASES}
    normalized = {_normalize_header(col): col for col in df.columns}

    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[field] = normalized[alias]
                break
    return mapping


def _parse_country(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "CA"
    text = str(value).strip().upper()
    if text in {"CA", "CAN", "CANADA"}:
        return "CA"
    if text in {"AU", "AUS", "AUSTRALIA"}:
        return "AU"
    return "CA"


def _cell(row: pd.Series, column: str | None) -> Any:
    if not column:
        return None
    value = row.get(column)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def import_csv(db: Client, file_bytes: bytes) -> CsvUploadResult:
    result = CsvUploadResult()
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:
        result.errors.append(f"Failed to parse CSV: {exc}")
        return result

    if df.empty:
        result.errors.append("CSV file is empty")
        return result

    mapping = _map_columns(df)
    if not mapping["name"]:
        result.errors.append("Could not find a company name column (expected: name, company, etc.)")
        return result

    for idx, row in df.iterrows():
        result.rows_processed += 1
        try:
            name = _cell(row, mapping["name"])
            if not name:
                result.errors.append(f"Row {idx + 2}: missing company name")
                continue

            website = _cell(row, mapping["website"])
            if website:
                website = _normalize_website(website) or canonical_website(website)
            else:
                result.errors.append(f"Row {idx + 2}: missing website (required for upsert key)")
                continue

            company = {
                "name": name,
                "website": website,
                "address": _cell(row, mapping["address"]),
                "city": _cell(row, mapping["city"]),
                "state": _cell(row, mapping["state"]),
                "country": _parse_country(_cell(row, mapping["country"])),
                "phone": _cell(row, mapping["phone"]),
                "category": _cell(row, mapping["category"]) or "Imported",
            }

            is_new, ok = process_company_record(db, company, source="csv_upload")
            if ok:
                if is_new:
                    result.rows_new += 1
                else:
                    result.rows_updated += 1
            else:
                result.errors.append(f"Row {idx + 2}: failed to process {name}")
        except Exception as exc:
            result.errors.append(f"Row {idx + 2}: {exc}")

    return result
