"""Importer for Active Listings CSV -> ``inventory_items`` table."""

from __future__ import annotations

import csv
import datetime as dt
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

try:  # pragma: no cover - allow running without package context
    from ..database import APP_DIR, Database
except ImportError:  # pragma: no cover
    from database import APP_DIR, Database


def _normalize_header(header: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", header.strip().lower())
    return cleaned.strip("_")


HEADER_MAP: Dict[str, str] = {
    "item_id": "item_number",
    "itemid": "item_number",
    "item_number": "item_number",
    "title": "title",
    "item_title": "title",
    "custom_label": "custom_sku",
    "custom_label_sku": "custom_sku",
    "custom_label_(sku)": "custom_sku",
    "sku": "custom_sku",
    "current_price": "current_price",
    "price": "current_price",
    "start_price": "current_price",
    "available_quantity": "available_quantity",
    "quantity": "available_quantity",
    "ebay_category_1_name": "ebay_category1_name",
    "category_name": "ebay_category1_name",
    "ebay_category1_name": "ebay_category1_name",
    "ebay_category_1_number": "ebay_category1_number",
    "category_number": "ebay_category1_number",
    "ebay_category1_number": "ebay_category1_number",
    "condition": "condition",
    "listing_site": "listing_site",
    "site": "listing_site",
    "start_date": "start_date",
    "start_time": "start_date",
    "end_date": "end_date",
    "end_time": "end_date",
    "status": "status",
}

REQUIRED_FIELDS = {"item_number", "title"}


def _parse_decimal(value: Optional[str]) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Optional[str]) -> Optional[str]:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for fmt in (
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y",
    ):
        try:
            return dt.datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue
    return text


def _resolve_inventory_csv_path() -> Path:
    env_value = os.environ.get("INVENTORY_CSV_PATH")
    if env_value:
        return Path(env_value)

    candidates: List[Path] = [
        Path(APP_DIR) / "data" / "active_listings.csv",
    ]
    # Fall back to any csv resembling the shipped reports.
    candidates += Path(APP_DIR).glob("*active-listings*.csv")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Active listings CSV not found. Set INVENTORY_CSV_PATH.")


def import_inventory_from_csv(
    db: Database, csv_path: Optional[str] = None
) -> Dict[str, object]:
    """Seed ``inventory_items`` from the Active Listings CSV."""

    path = Path(csv_path) if csv_path else _resolve_inventory_csv_path()
    if not path.exists():
        raise FileNotFoundError(path)

    summary = {"rows_read": 0, "upserts": 0, "skipped": 0, "warnings": []}
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Active listings CSV is missing headers")

        header_map = {
            raw: HEADER_MAP.get(_normalize_header(raw), _normalize_header(raw))
            for raw in reader.fieldnames
        }

        for row_index, raw_row in enumerate(reader, start=1):
            summary["rows_read"] += 1
            canonical: Dict[str, Optional[str]] = {}
            for raw_key, value in raw_row.items():
                if raw_key is None:
                    continue
                canonical_key = header_map.get(raw_key)
                if not canonical_key:
                    canonical_key = _normalize_header(raw_key)
                canonical[canonical_key] = value

            item_number = str(canonical.get("item_number") or "").strip()
            title = str(canonical.get("title") or "").strip()

            if any(field not in canonical or not (canonical[field] or "").strip() for field in REQUIRED_FIELDS):
                summary["skipped"] += 1
                summary["warnings"].append(
                    f"Row {row_index}: missing required fields for inventory item"
                )
                continue

            price_value = _parse_decimal(canonical.get("current_price"))
            quantity_value = _parse_int(canonical.get("available_quantity"))

            if canonical.get("current_price") not in (None, "") and price_value is None:
                summary["warnings"].append(
                    f"Row {row_index}: non-numeric price '{canonical.get('current_price')}' for {item_number}"
                )

            if canonical.get("available_quantity") not in (None, "") and quantity_value is None:
                summary["warnings"].append(
                    f"Row {row_index}: non-numeric quantity '{canonical.get('available_quantity')}' for {item_number}"
                )

            record = {
                "item_number": item_number,
                "title": title,
                "custom_sku": (canonical.get("custom_sku") or "").strip() or None,
                "current_price": price_value,
                "available_quantity": quantity_value,
                "ebay_category1_name": (canonical.get("ebay_category1_name") or "").strip() or None,
                "ebay_category1_number": (canonical.get("ebay_category1_number") or "").strip() or None,
                "condition": (canonical.get("condition") or "").strip() or None,
                "listing_site": (canonical.get("listing_site") or "").strip() or None,
                "start_date": _parse_datetime(canonical.get("start_date")),
                "end_date": _parse_datetime(canonical.get("end_date")),
                "status": "active",
            }

            try:
                db.upsert_inventory_item_from_feed(record, timestamp=timestamp)
                summary["upserts"] += 1
            except Exception as exc:  # pragma: no cover - defensive logging
                summary["warnings"].append(
                    f"Row {row_index}: failed to upsert inventory item {item_number} ({exc})"
                )
                summary["skipped"] += 1

    db.conn.commit()
    return summary

