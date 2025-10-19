# src/database.py
from __future__ import annotations
import os
import csv
import json
import sqlite3
import datetime
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = os.path.join("data", "reseller.db")


class Database:
    """
    Unified SQLite data layer for the reseller app.
    Handles inventory, expenses, imports, normalization, and dashboard analytics.
    """

    # -------------------- column maps --------------------
    INVENTORY_MAP = {
        "title": "title",
        "sku": "sku",
        "condition": "condition",
        "listed_price": "listed_price",
        "listed_date": "listed_date",
        "status": "status",
    }

    SOLD_MAP = {
        "title": "title",
        "sku": "sku",
        "sold_price": "sold_price",
        "sold_date": "sold_date",
        "quantity": "quantity",
        "order_number": "order_number",
    }

    # -----------------------------------------------------
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()

    # ---------------------------- schema ----------------------------
    def create_tables(self):
        """Create all necessary tables."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                sku TEXT UNIQUE,
                condition TEXT,
                listed_price REAL,
                listed_date TEXT,
                status TEXT,
                sold_price REAL,
                sold_date TEXT,
                quantity INTEGER DEFAULT 1,
                order_number TEXT,
                upc TEXT,
                image_url TEXT,
                description TEXT,
                category_id TEXT,
                purchase_price REAL,
                cost REAL
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                amount REAL,
                category TEXT,
                note TEXT,
                tax_deductible INTEGER DEFAULT 0
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS expense_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id) ON DELETE CASCADE
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                context TEXT,
                message TEXT NOT NULL
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS import_settings (
                id INTEGER PRIMARY KEY CHECK (id=1),
                settings_json TEXT NOT NULL
            )
            """
        )
        self.cursor.execute(
            """
            INSERT OR IGNORE INTO import_settings (id, settings_json)
            VALUES (1, '{"encoding":"utf-8","delimiter":",","default_category_id":"47140","decimal":"."}')
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS import_mappings (
                report_type TEXT PRIMARY KEY,
                mapping_json TEXT NOT NULL
            )
            """
        )

        self.cursor.execute(
            """
            INSERT OR IGNORE INTO import_mappings (report_type, mapping_json)
            VALUES ('active_listings', '{"title":"Title","sku":"Custom label (SKU)","condition":"Condition","listed_price":"Current price|Start price","listed_date":"Start date"}')
            """
        )
        self.cursor.execute(
            """
            INSERT OR IGNORE INTO import_mappings (report_type, mapping_json)
            VALUES ('orders', '{"title":"Item Title","sku":"Custom Label","sold_price":"Total Price|Sale Price","sold_date":"Sale Date","quantity":"Quantity","order_number":"Order Number"}')
            """
        )

        self._ensure_inventory_columns()
        self.conn.commit()

    def _ensure_inventory_columns(self):
        """Ensure required columns exist (for legacy DBs)."""
        self.cursor.execute("PRAGMA table_info(inventory)")
        cols = {r["name"] for r in self.cursor.fetchall()}
        missing = {
            "quantity": "INTEGER DEFAULT 1",
            "purchase_price": "REAL",
            "cost": "REAL",
        }
        for col, ddl in missing.items():
            if col not in cols:
                try:
                    self.cursor.execute(f"ALTER TABLE inventory ADD COLUMN {col} {ddl}")
                except Exception:
                    pass

    # ---------------------------- helpers ----------------------------
    def _safe_int(self, v, default=1):
        try:
            if v in (None, ""):
                return default
            if isinstance(v, (int, float)):
                return int(v)
            s = str(v).strip()
            if s.replace(".", "", 1).isdigit():
                return int(float(s))
            return int(s)
        except Exception:
            return default

    def _parse_float(self, v):
        if v in (None, ""):
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).replace("$", "").replace(",", "").strip()
        try:
            return float(s)
        except Exception:
            return None

    def _parse_date_iso(self, s):
        if not s:
            return None
        s = str(s).strip()
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.datetime.strptime(s, fmt).date().isoformat()
            except Exception:
                continue
        return s

    def _first_existing_column(self, row: Dict[str, Any], candidates: str):
        for name in candidates.split("|"):
            if name in row and row[name]:
                return row[name]
        return None

    # ---------------------------- settings ----------------------------
    def get_import_settings(self) -> Dict[str, Any]:
        self.cursor.execute("SELECT settings_json FROM import_settings WHERE id=1")
        row = self.cursor.fetchone()
        return json.loads(row["settings_json"]) if row else {}

    def update_import_settings(self, settings: Dict[str, Any]):
        self.cursor.execute(
            "INSERT INTO import_settings (id, settings_json) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET settings_json=excluded.settings_json",
            (json.dumps(settings),),
        )
        self.conn.commit()

    def get_setting(self, key: str, default=None):
        s = self.get_import_settings()
        return s.get(key, default)

    def set_setting(self, key: str, value: Any):
        s = self.get_import_settings()
        s[key] = value
        self.update_import_settings(s)

    def get_mapping(self, report_type: str):
        self.cursor.execute("SELECT mapping_json FROM import_mappings WHERE report_type=?", (report_type,))
        row = self.cursor.fetchone()
        return json.loads(row["mapping_json"]) if row else {}

    # ---------------------------- data access ----------------------------
    def get_inventory_items(self, **kwargs):
        status = kwargs.get("status")
        listed_only = kwargs.get("listed_only")
        sold_only = kwargs.get("sold_only")
        search = kwargs.get("search")

        clauses, params = [], []
        if status:
            clauses.append("LOWER(status)=LOWER(?)")
            params.append(status)
        if listed_only:
            clauses.append("LOWER(status)='listed'")
        if sold_only:
            clauses.append("LOWER(status)='sold'")
        if search:
            q = f"%{search.lower()}%"
            clauses.append("(LOWER(title) LIKE ? OR LOWER(sku) LIKE ?)")
            params += [q, q]

        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"SELECT * FROM inventory{where} ORDER BY id DESC"
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def get_inventory_item(self, item_id: int):
        self.cursor.execute("SELECT * FROM inventory WHERE id=?", (item_id,))
        return self.cursor.fetchone()

    def get_expenses(self):
        self.cursor.execute("SELECT * FROM expenses ORDER BY date DESC, id DESC")
        return self.cursor.fetchall()

    # ---------------------------- analytics / dashboard ----------------------------
    def get_total_deductible_expenses(self, *args):
        self.cursor.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE tax_deductible=1")
        return float(self.cursor.fetchone()["total"])

    def get_inventory_value(self, *args):
        self.cursor.execute("SELECT COALESCE(SUM(listed_price), 0) AS total FROM inventory WHERE LOWER(status)='listed'")
        return float(self.cursor.fetchone()["total"])

    def get_total_revenue(self, *args):
        self.cursor.execute(
            "SELECT COALESCE(SUM(sold_price * COALESCE(quantity,1)), 0) AS total FROM inventory WHERE LOWER(status)='sold'"
        )
        return float(self.cursor.fetchone()["total"])

    def get_total_profit(self, *args):
        self.cursor.execute(
            """
            SELECT
                COALESCE(SUM(COALESCE(sold_price,0) * COALESCE(quantity,1)), 0)
                - COALESCE(SUM(COALESCE(purchase_price,0) * COALESCE(quantity,1)), 0)
                AS profit
            FROM inventory
            WHERE LOWER(status)='sold'
            """
        )
        return float(self.cursor.fetchone()["profit"])

    def get_expense_breakdown(self):
        self.cursor.execute(
            "SELECT category, COALESCE(SUM(amount), 0) AS total FROM expenses GROUP BY category ORDER BY total DESC"
        )
        rows = self.cursor.fetchall()
        return {r["category"]: float(r["total"]) for r in rows if r["category"]}

    def get_sales(self, *args, **kwargs):
        """Returns all sold inventory items (optionally filtered by date/search)."""
        search = kwargs.get("search")
        date_from = kwargs.get("date_from")
        date_to = kwargs.get("date_to")
        clauses = ["LOWER(status)='sold'"]
        params = []
        if search:
            q = f"%{search.lower()}%"
            clauses.append("(LOWER(title) LIKE ? OR LOWER(sku) LIKE ?)")
            params += [q, q]
        if date_from:
            clauses.append("sold_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("sold_date <= ?")
            params.append(date_to)
        where = " WHERE " + " AND ".join(clauses)
        sql = f"SELECT * FROM inventory{where} ORDER BY sold_date DESC, id DESC"
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    # ---------------------------- housekeeping ----------------------------
    def clear_error_logs(self):
        self.cursor.execute("DELETE FROM error_logs")
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
