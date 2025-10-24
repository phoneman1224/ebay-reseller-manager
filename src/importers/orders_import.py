from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from database import Database


@dataclass
class OrderLine:
    order_number: str
    transaction_id: str
    item_number: Optional[str]
    item_title: Optional[str]
    custom_sku: Optional[str]
    quantity: Optional[int]
    unit_price: Optional[float]
    tax_amount: Optional[float]
    shipping_amount: Optional[float]
    discount_amount: Optional[float]

    def to_payload(self) -> Dict[str, Any]:
        return {
            "order_number": self.order_number,
            "transaction_id": self.transaction_id,
            "item_number": self.item_number,
            "item_title_snapshot": self.item_title,
            "custom_sku": self.custom_sku,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "tax_amount": self.tax_amount,
            "shipping_amount": self.shipping_amount,
            "discount_amount": self.discount_amount,
        }


@dataclass
class OrderRecord:
    order_number: str
    sales_record_number: Optional[str] = None
    buyer_username: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None
    ship_to_name: Optional[str] = None
    ship_to_phone: Optional[str] = None
    ship_to_address_1: Optional[str] = None
    ship_to_address_2: Optional[str] = None
    ship_to_city: Optional[str] = None
    ship_to_state: Optional[str] = None
    ship_to_zip: Optional[str] = None
    ship_to_country: Optional[str] = None
    order_total: Optional[float] = None
    ordered_at: Optional[str] = None
    paid_at: Optional[str] = None
    shipped_on_date: Optional[str] = None
    status: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=lambda: defaultdict(float))
    items: List[OrderLine] = field(default_factory=list)
    shipments: Dict[str, Dict[str, Optional[str]]] = field(default_factory=dict)

    def update_from_row(self, row: Dict[str, str]) -> None:
        def _first(existing: Optional[str], new_value: Optional[str]) -> Optional[str]:
            return existing if existing not in (None, "") else new_value

        self.sales_record_number = _first(
            self.sales_record_number, _normalise_string(row.get("Sales Record Number"))
        )
        self.buyer_username = _first(
            self.buyer_username, _normalise_string(row.get("Buyer Username"))
        )
        self.buyer_name = _first(self.buyer_name, _normalise_string(row.get("Buyer Name")))
        self.buyer_email = _first(self.buyer_email, _normalise_string(row.get("Buyer Email")))
        self.ship_to_name = _first(self.ship_to_name, _normalise_string(row.get("Ship To Name")))
        self.ship_to_address_1 = _first(
            self.ship_to_address_1, _normalise_string(row.get("Ship To Address 1"))
        )
        self.ship_to_address_2 = _first(
            self.ship_to_address_2, _normalise_string(row.get("Ship To Address 2"))
        )
        self.ship_to_city = _first(self.ship_to_city, _normalise_string(row.get("Ship To City")))
        self.ship_to_state = _first(
            self.ship_to_state, _normalise_string(row.get("Ship To State"))
        )
        self.ship_to_zip = _first(self.ship_to_zip, _normalise_string(row.get("Ship To Zip")))
        self.ship_to_country = _first(
            self.ship_to_country, _normalise_string(row.get("Ship To Country"))
        )
        self.status = _first(self.status, _normalise_string(row.get("Status")))

        total = _parse_float(row.get("Order Total"))
        if total is not None:
            self.order_total = total

        ordered_at = _parse_datetime(row.get("Order Date"))
        if ordered_at:
            self.ordered_at = ordered_at
        paid_at = _parse_datetime(row.get("Paid On Date"))
        if paid_at:
            self.paid_at = paid_at
        shipped_on = _parse_datetime(row.get("Shipped On Date"))
        if shipped_on:
            self.shipped_on_date = shipped_on

        # Aggregate shipping/tax/discount meta values
        shipping_value = _parse_float(row.get("Shipping and handling")) or 0.0
        tax_value = _parse_float(row.get("Tax")) or 0.0
        discount_value = _parse_float(row.get("Discount")) or 0.0
        self.meta["shipping_amount"] += shipping_value
        self.meta["tax_amount"] += tax_value
        self.meta["discount_amount"] += discount_value

        tracking_number = _normalise_string(row.get("Tracking Number"))
        if tracking_number:
            self.shipments[tracking_number] = {
                "order_number": self.order_number,
                "shipping_service": _normalise_string(row.get("Shipping Service")),
                "tracking_number": tracking_number,
                "label_cost": None,
                "shipped_on_date": self.shipped_on_date,
            }

    def to_payload(self) -> Dict[str, Any]:
        return {
            "order_number": self.order_number,
            "sales_record_number": self.sales_record_number,
            "buyer_username": self.buyer_username,
            "buyer_name": self.buyer_name,
            "buyer_email": self.buyer_email,
            "ship_to_name": self.ship_to_name,
            "ship_to_phone": self.ship_to_phone,
            "ship_to_address_1": self.ship_to_address_1,
            "ship_to_address_2": self.ship_to_address_2,
            "ship_to_city": self.ship_to_city,
            "ship_to_state": self.ship_to_state,
            "ship_to_zip": self.ship_to_zip,
            "ship_to_country": self.ship_to_country,
            "order_total": self.order_total,
            "ordered_at": self.ordered_at,
            "paid_at": self.paid_at,
            "shipped_on_date": self.shipped_on_date,
            "status": self.status,
            "meta_json": json.dumps(dict(self.meta)),
        }


def _normalise_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_float(value: Optional[str]) -> Optional[float]:
    cleaned = _normalise_string(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned.replace("$", "").replace(",", ""))
    except ValueError:
        return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    cleaned = _normalise_string(value)
    if cleaned is None:
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def _parse_datetime(value: Optional[str]) -> Optional[str]:
    cleaned = _normalise_string(value)
    if cleaned is None:
        return None
    formats = [
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            if "H" in fmt:
                return dt.isoformat()
            return dt.date().isoformat()
        except ValueError:
            continue
    return cleaned


def _iter_rows(csv_path: Path) -> Iterable[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        filtered_lines = (line for line in handle if line.strip())
        reader = csv.DictReader(filtered_lines)
        for row in reader:
            if not row:
                continue
            if all(_normalise_string(value) is None for value in row.values()):
                continue
            yield row


def _next_line_id(counter: int) -> str:
    return f"line-{counter:03d}"


def import_orders_from_csv(db: Database, *, csv_path: str) -> Dict[str, Any]:
    """Import completed orders into the database."""

    csv_file = Path(csv_path)
    orders: Dict[str, OrderRecord] = {}
    line_counters: Dict[str, int] = defaultdict(int)
    summary: Dict[str, Any] = {
        "rows_read": 0,
        "orders_upserted": 0,
        "order_items_upserted": 0,
        "shipments_upserted": 0,
        "errors": [],
    }

    for line_number, row in enumerate(_iter_rows(csv_file), start=2):
        summary["rows_read"] += 1
        order_number = _normalise_string(row.get("Order Number"))
        if not order_number:
            summary["errors"].append({"line": line_number, "error": "Missing Order Number"})
            continue

        record = orders.setdefault(order_number, OrderRecord(order_number=order_number))
        try:
            record.update_from_row(row)

            line_counters[order_number] += 1
            transaction_id = _normalise_string(row.get("Transaction ID"))
            if not transaction_id:
                transaction_id = _next_line_id(line_counters[order_number])

            line = OrderLine(
                order_number=order_number,
                transaction_id=transaction_id,
                item_number=_normalise_string(row.get("Item Number")),
                item_title=_normalise_string(row.get("Item Title")),
                custom_sku=_normalise_string(row.get("Custom Label (SKU)")),
                quantity=_parse_int(row.get("Quantity")),
                unit_price=_parse_float(row.get("Sold For")),
                tax_amount=_parse_float(row.get("Tax")),
                shipping_amount=_parse_float(row.get("Shipping and handling")),
                discount_amount=_parse_float(row.get("Discount")),
            )
            record.items.append(line)
        except Exception as exc:  # pragma: no cover - defensive
            summary["errors"].append({"line": line_number, "error": str(exc)})

    for order in orders.values():
        db.upsert_sales_order_from_feed(order.to_payload())
        summary["orders_upserted"] += 1

        for item in order.items:
            db.upsert_sales_order_item_from_feed(item.to_payload())
            summary["order_items_upserted"] += 1

        for shipment in order.shipments.values():
            result = db.upsert_shipment_from_feed(shipment)
            if result is not None:
                summary["shipments_upserted"] += 1

    db.conn.commit()
    return summary
