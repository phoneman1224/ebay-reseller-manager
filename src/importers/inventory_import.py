from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from database import Database


@dataclass
class InventoryRow:
    item_number: str
    title: str
    custom_sku: Optional[str]
    current_price: Optional[float]
    available_quantity: Optional[int]
    ebay_category1_name: Optional[str]
    ebay_category1_number: Optional[str]
    condition: Optional[str]
    listing_site: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]

    def to_payload(self) -> Dict[str, Any]:
        return {
            "item_number": self.item_number,
            "title": self.title,
            "custom_sku": self.custom_sku,
            "current_price": self.current_price,
            "available_quantity": self.available_quantity,
            "ebay_category1_name": self.ebay_category1_name,
            "ebay_category1_number": self.ebay_category1_number,
            "condition": self.condition,
            "listing_site": self.listing_site,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": "active",
        }


def _normalise_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_float(value: Optional[str]) -> Optional[float]:
    value = _normalise_string(value)
    if not value:
        return None
    try:
        return float(value.replace("$", "").replace(",", ""))
    except ValueError:
        return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    value = _normalise_string(value)
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _parse_datetime(value: Optional[str]) -> Optional[str]:
    raw = _normalise_string(value)
    if not raw:
        return None
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(raw, fmt)
            if "H" in fmt:
                return dt.isoformat()
            return dt.date().isoformat()
        except ValueError:
            continue
    return raw


def _iter_rows(csv_path: Path) -> Iterable[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        filtered_lines = (line for line in handle if line.strip())
        reader = csv.DictReader(filtered_lines)
        for row in reader:
            if not row:
                continue
            if all(_normalise_string(v) is None for v in row.values()):
                continue
            yield row


def _build_inventory_row(row: Dict[str, str]) -> InventoryRow:
    item_number = _normalise_string(row.get("Item Number"))
    title = _normalise_string(row.get("Title")) or ""
    if not item_number or not title:
        raise ValueError("Row missing required inventory identifiers")

    return InventoryRow(
        item_number=item_number,
        title=title,
        custom_sku=_normalise_string(row.get("Custom label (SKU)")),
        current_price=_parse_float(row.get("Current price")),
        available_quantity=_parse_int(row.get("Available quantity")),
        ebay_category1_name=_normalise_string(row.get("eBay category 1 name")),
        ebay_category1_number=_normalise_string(row.get("eBay category 1 number")),
        condition=_normalise_string(row.get("Condition")),
        listing_site=_normalise_string(row.get("Listing site")),
        start_date=_parse_datetime(row.get("Start date")),
        end_date=_parse_datetime(row.get("End date")),
    )


def import_inventory_from_csv(db: Database, *, csv_path: str) -> Dict[str, Any]:
    """Import active listings data into the database.

    Parameters
    ----------
    db:
        Initialised :class:`Database` instance.
    csv_path:
        Path to the CSV file exported from eBay.

    Returns
    -------
    Dict[str, Any]
        Summary of the import process. Keys include ``rows_read``, ``upserts``
        and ``errors``.
    """

    csv_file = Path(csv_path)
    summary: Dict[str, Any] = {"rows_read": 0, "upserts": 0, "errors": []}

    for line_number, row in enumerate(_iter_rows(csv_file), start=2):
        summary["rows_read"] += 1
        try:
            payload = _build_inventory_row(row).to_payload()
            db.upsert_inventory_item_from_feed(payload)
            summary["upserts"] += 1
        except Exception as exc:  # pragma: no cover - defensive, surfaced in summary
            summary["errors"].append({"line": line_number, "error": str(exc)})

    db.conn.commit()
    return summary
