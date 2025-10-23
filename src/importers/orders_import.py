"""Importer for Completed Orders CSV -> sales orders/tables."""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
from collections import defaultdict
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
    "order_number": "order_number",
    "order_id": "order_number",
    "sales_record_number": "sales_record_number",
    "salesrecordnumber": "sales_record_number",
    "buyer_username": "buyer_username",
    "buyer_user_id": "buyer_username",
    "buyerid": "buyer_username",
    "buyer_name": "buyer_name",
    "buyer_fullname": "buyer_name",
    "buyer_email": "buyer_email",
    "email": "buyer_email",
    "ship_to_name": "ship_to_name",
    "shipping_name": "ship_to_name",
    "ship_to_phone": "ship_to_phone",
    "buyer_phone": "ship_to_phone",
    "ship_to_address_1": "ship_to_address_1",
    "ship_to_address_2": "ship_to_address_2",
    "ship_to_city": "ship_to_city",
    "ship_to_state": "ship_to_state",
    "ship_to_zip": "ship_to_zip",
    "ship_to_postal_code": "ship_to_zip",
    "ship_to_country": "ship_to_country",
    "order_total": "order_total",
    "order_amount": "order_total",
    "total_amount": "order_total",
    "order_date": "ordered_at",
    "sale_date": "ordered_at",
    "sold_date": "ordered_at",
    "sold_on": "ordered_at",
    "paid_on_date": "paid_at",
    "paid_date": "paid_at",
    "paid_on": "paid_at",
    "shipped_on_date": "shipped_on_date",
    "ship_date": "shipped_on_date",
    "status": "status",
    "order_status": "status",
    "transaction_id": "transaction_id",
    "item_id": "item_number",
    "item_number": "item_number",
    "listing_id": "item_number",
    "item_title": "item_title",
    "title": "item_title",
    "custom_label": "custom_sku",
    "custom_label_sku": "custom_sku",
    "custom_label_(sku)": "custom_sku",
    "sku": "custom_sku",
    "quantity": "quantity",
    "qty": "quantity",
    "sold_for": "unit_price",
    "sale_price": "unit_price",
    "total_price": "unit_price",
    "item_total": "unit_price",
    "price": "unit_price",
    "item_price": "unit_price",
    "tax": "tax_amount",
    "tax_amount": "tax_amount",
    "seller_collected_tax": "seller_collected_tax",
    "ebay_collected_tax": "ebay_collected_tax",
    "shipping_and_handling": "shipping_amount",
    "shipping": "shipping_amount",
    "shipping_amount": "shipping_amount",
    "shipping_price": "shipping_amount",
    "discount": "discount_amount",
    "discount_amount": "discount_amount",
    "promotion_discount": "discount_amount",
    "shipping_service": "shipping_service",
    "service": "shipping_service",
    "carrier": "shipping_service",
    "tracking_number": "tracking_number",
    "tracking_id": "tracking_number",
    "tracking": "tracking_number",
    "label_cost": "label_cost",
    "postage": "label_cost",
}

META_FIELDS = [
    "seller_collected_tax",
    "ebay_collected_tax",
    "shipping_amount",
    "discount_amount",
]


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


def _strip(value: Optional[str]) -> Optional[str]:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _resolve_orders_csv_path() -> Path:
    env_value = os.environ.get("ORDERS_CSV_PATH")
    if env_value:
        return Path(env_value)

    candidates: List[Path] = [
        Path(APP_DIR) / "data" / "completed_orders.csv",
    ]
    candidates += list(Path(APP_DIR).glob("*all-orders-report*.csv"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Completed orders CSV not found. Set ORDERS_CSV_PATH.")


def _prepare_reader(handle) -> csv.DictReader:
    """Return a DictReader, skipping any blank header rows."""

    while True:
        pos = handle.tell()
        line = handle.readline()
        if not line:
            raise ValueError("Orders CSV appears to be empty")
        if line.strip():
            handle.seek(pos)
            break

    reader = csv.DictReader(handle)
    if reader.fieldnames is None:
        raise ValueError("Orders CSV missing headers")
    return reader


def import_orders_from_csv(db: Database, csv_path: Optional[str] = None) -> Dict[str, object]:
    """Seed sales orders, order items and shipments from Completed Orders CSV."""

    path = Path(csv_path) if csv_path else _resolve_orders_csv_path()
    if not path.exists():
        raise FileNotFoundError(path)

    summary = {
        "rows_read": 0,
        "orders_upserted": 0,
        "order_items_upserted": 0,
        "shipments_upserted": 0,
        "skipped": 0,
        "warnings": [],
    }

    orders_payload: Dict[str, Dict[str, Optional[object]]] = {}
    orders_meta: Dict[str, Dict[str, str]] = defaultdict(dict)
    order_items_payload: Dict[str, Dict[str, Dict[str, object]]] = defaultdict(dict)
    shipments_payload: Dict[str, Dict[str, object]] = {}
    line_index = defaultdict(int)

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = _prepare_reader(handle)
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

            order_number = _strip(canonical.get("order_number"))
            if not order_number:
                summary["skipped"] += 1
                summary["warnings"].append(
                    f"Row {row_index}: missing order number"
                )
                continue

            order_payload = orders_payload.setdefault(
                order_number,
                {
                    "order_number": order_number,
                    "sales_record_number": None,
                    "buyer_username": None,
                    "buyer_name": None,
                    "buyer_email": None,
                    "ship_to_name": None,
                    "ship_to_phone": None,
                    "ship_to_address_1": None,
                    "ship_to_address_2": None,
                    "ship_to_city": None,
                    "ship_to_state": None,
                    "ship_to_zip": None,
                    "ship_to_country": None,
                    "order_total": None,
                    "ordered_at": None,
                    "paid_at": None,
                    "shipped_on_date": None,
                    "status": None,
                    "meta_json": None,
                },
            )

            for field in (
                "sales_record_number",
                "buyer_username",
                "buyer_name",
                "buyer_email",
                "ship_to_name",
                "ship_to_phone",
                "ship_to_address_1",
                "ship_to_address_2",
                "ship_to_city",
                "ship_to_state",
                "ship_to_zip",
                "ship_to_country",
                "status",
            ):
                value = _strip(canonical.get(field))
                if value is not None:
                    order_payload[field] = value

            total_value = _parse_decimal(canonical.get("order_total"))
            if total_value is not None:
                order_payload["order_total"] = total_value

            ordered_at_value = _parse_datetime(canonical.get("ordered_at"))
            if ordered_at_value is not None:
                order_payload["ordered_at"] = ordered_at_value

            paid_at_value = _parse_datetime(canonical.get("paid_at"))
            if paid_at_value is not None:
                order_payload["paid_at"] = paid_at_value

            shipped_at_value = _parse_datetime(canonical.get("shipped_on_date"))
            if shipped_at_value is not None:
                order_payload["shipped_on_date"] = shipped_at_value

            for meta_field in META_FIELDS:
                value = canonical.get(meta_field)
                if value not in (None, ""):
                    orders_meta[order_number][meta_field] = str(value)

            # Order items
            line_index[order_number] += 1
            transaction_id = _strip(canonical.get("transaction_id"))
            if not transaction_id:
                transaction_id = f"line-{line_index[order_number]:03d}"

            quantity_value = _parse_int(canonical.get("quantity")) or 1
            unit_price_value = _parse_decimal(canonical.get("unit_price"))
            tax_value = _parse_decimal(canonical.get("tax_amount"))
            if tax_value is None:
                tax_parts = [
                    _parse_decimal(canonical.get("seller_collected_tax")),
                    _parse_decimal(canonical.get("ebay_collected_tax")),
                ]
                tax_sum = sum(v for v in tax_parts if v is not None)
                tax_value = tax_sum if any(v is not None for v in tax_parts) else None
            shipping_value = _parse_decimal(canonical.get("shipping_amount"))
            discount_value = _parse_decimal(canonical.get("discount_amount"))

            item_title = _strip(canonical.get("item_title"))
            if not item_title:
                item_title = ""

            item_record = {
                "order_number": order_number,
                "transaction_id": transaction_id,
                "item_number": _strip(canonical.get("item_number")),
                "item_title_snapshot": item_title,
                "custom_sku": _strip(canonical.get("custom_sku")),
                "quantity": quantity_value,
                "unit_price": unit_price_value,
                "tax_amount": tax_value,
                "shipping_amount": shipping_value,
                "discount_amount": discount_value,
            }

            order_items_payload[order_number][transaction_id] = item_record

            tracking_number = _strip(canonical.get("tracking_number"))
            if tracking_number:
                shipments_payload[tracking_number] = {
                    "order_number": order_number,
                    "shipping_service": _strip(canonical.get("shipping_service")),
                    "tracking_number": tracking_number,
                    "label_cost": _parse_decimal(canonical.get("label_cost")),
                    "shipped_on_date": _parse_datetime(canonical.get("shipped_on_date")),
                }

    for order_number, payload in orders_payload.items():
        meta = orders_meta.get(order_number, {})
        payload["meta_json"] = json.dumps(meta, sort_keys=True) if meta else None
        db.upsert_sales_order_from_feed(payload)
    summary["orders_upserted"] = len(orders_payload)

    for items in order_items_payload.values():
        for record in items.values():
            db.upsert_sales_order_item_from_feed(record)
            summary["order_items_upserted"] += 1

    for shipment in shipments_payload.values():
        result = db.upsert_shipment_from_feed(shipment)
        if result is not None:
            summary["shipments_upserted"] += 1

    db.conn.commit()
    return summary

