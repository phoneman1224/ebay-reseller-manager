"""Schema setup for the minimum inventory + orders feature flag."""

from __future__ import annotations

import json
from typing import Iterable


def _execute_statements(cursor, statements: Iterable[str]) -> None:
    for stmt in statements:
        cursor.execute(stmt)


def run(cursor) -> None:
    """Create tables and views required for the modern inventory/orders flow."""

    table_statements = [
        """
        CREATE TABLE IF NOT EXISTS inventory_items (
            item_number            TEXT PRIMARY KEY,
            title                  TEXT NOT NULL,
            custom_sku             TEXT,
            current_price          NUMERIC,
            available_quantity     INTEGER,
            ebay_category1_name    TEXT,
            ebay_category1_number  TEXT,
            condition              TEXT,
            listing_site           TEXT,
            start_date             TEXT,
            end_date               TEXT,
            status                 TEXT DEFAULT 'active',
            last_sync_at           TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sales_orders (
            order_number         TEXT PRIMARY KEY,
            sales_record_number  TEXT,
            buyer_username       TEXT,
            buyer_name           TEXT,
            buyer_email          TEXT,
            ship_to_name         TEXT,
            ship_to_phone        TEXT,
            ship_to_address_1    TEXT,
            ship_to_address_2    TEXT,
            ship_to_city         TEXT,
            ship_to_state        TEXT,
            ship_to_zip          TEXT,
            ship_to_country      TEXT,
            order_total          NUMERIC,
            ordered_at           TEXT,
            paid_at              TEXT,
            shipped_on_date      TEXT,
            status               TEXT,
            meta_json            TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sales_order_items (
            id                   INTEGER PRIMARY KEY,
            order_number         TEXT NOT NULL,
            transaction_id       TEXT,
            item_number          TEXT,
            item_title_snapshot  TEXT,
            custom_sku           TEXT,
            quantity             INTEGER,
            unit_price           NUMERIC,
            tax_amount           NUMERIC,
            shipping_amount      NUMERIC,
            discount_amount      NUMERIC,
            FOREIGN KEY(order_number) REFERENCES sales_orders(order_number)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS shipments (
            id               INTEGER PRIMARY KEY,
            order_number     TEXT NOT NULL,
            shipping_service TEXT,
            tracking_number  TEXT UNIQUE,
            label_cost       NUMERIC,
            shipped_on_date  TEXT,
            FOREIGN KEY(order_number) REFERENCES sales_orders(order_number)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS edit_log (
            id          INTEGER PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_pk   TEXT NOT NULL,
            field       TEXT NOT NULL,
            old_value   TEXT,
            new_value   TEXT,
            edited_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            edited_by   TEXT
        )
        """,
    ]

    _execute_statements(cursor, table_statements)

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_order_line
        ON sales_order_items(order_number, COALESCE(transaction_id, CAST(id AS TEXT)));
        """
    )

    view_statements = [
        """
        CREATE VIEW IF NOT EXISTS listings_compat AS
        SELECT
            item_number,
            title,
            custom_sku        AS sku,
            current_price     AS price,
            available_quantity AS quantity,
            ebay_category1_name  AS category_name,
            ebay_category1_number AS category_number,
            status,
            start_date,
            end_date,
            listing_site,
            last_sync_at
        FROM inventory_items;
        """,
        """
        CREATE VIEW IF NOT EXISTS order_lines_compat AS
        SELECT
            so.order_number,
            so.sales_record_number,
            soi.id                       AS order_item_id,
            soi.item_number,
            soi.item_title_snapshot      AS item_title,
            soi.custom_sku,
            soi.quantity,
            soi.unit_price,
            soi.tax_amount,
            soi.shipping_amount,
            soi.discount_amount,
            so.buyer_username,
            so.buyer_name,
            so.order_total,
            so.paid_at,
            so.shipped_on_date,
            so.status
        FROM sales_order_items soi
        JOIN sales_orders so ON so.order_number = soi.order_number;
        """,
    ]

    _execute_statements(cursor, view_statements)


def as_dict(row) -> dict:
    """Return a plain dictionary for a sqlite3.Row."""

    if row is None:
        return {}
    try:
        return dict(row)
    except TypeError:
        return json.loads(json.dumps(row))

