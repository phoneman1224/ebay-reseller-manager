# src/database.py
from __future__ import annotations

import os
import csv
import json
import sqlite3
import datetime
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DB_PATH = os.path.join("data", "reseller.db")


class Database:
    """
    SQLite wrapper for the reseller app.
    Handles inventory, expenses, imports, normalization, and dashboard stats.
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
        """Create or ensure all required tables exist."""
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
                quantity INTEGER,
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

        # Default mappings
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

        # Lightweight migrations for older DBs: add missing columns
        self._ensure_inventory_columns()

        self.conn.commit()

    def _ensure_inventory_columns(self):
        """Add columns that may be missing in older databases."""
        self.cursor.execute("PRAGMA table_info(inventory)")
        cols = {row["name"] for row in self.cursor.fetchall()}
        to_add = []
        if "quantity" not in cols:
            to_add.append(("quantity", "INTEGER DEFAULT 1"))
        if "purchase_price" not in cols:
            to_add.append(("purchase_price", "REAL"))
        if "cost" not in cols:
            to_add.append(("cost", "REAL"))
        for name, ddl in to_add:
            try:
                self.cursor.execute(f"ALTER TABLE inventory ADD COLUMN {name} {ddl}")
            except Exception:
                pass  # ignore if race or already added elsewhere

    # ---------------------------- helpers ----------------------------

    def _safe_int(self, v, default: int = 1) -> int:
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

    def _parse_float(self, v) -> Optional[float]:
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).replace("$", "").replace(",", "").strip()
        try:
            return float(s) if s else None
        except Exception:
            return None

    def _parse_date_iso(self, s: Any) -> Optional[str]:
        if not s:
            return None
        s = str(s).strip()
        if len(s) >= 10 and s[4:5] == "-":
            try:
                datetime.date.fromisoformat(s[:10])
                return s[:10]
            except Exception:
                pass
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.datetime.strptime(s, fmt).date().isoformat()
            except Exception:
                continue
        return s

    def _first_existing_column(self, row: Dict[str, Any], candidates_str: str) -> Any:
        for name in candidates_str.split("|"):
            if name in row and row[name] not in (None, ""):
                return row[name]
        return None

    # ---------------------------- data access ----------------------------

    def get_inventory_items(self, **kwargs) -> List[sqlite3.Row]:
        """Get inventory list with optional filters."""
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
            clauses.append("(LOWER(title) LIKE ? OR LOWER(sku) LIKE ?)")
            q = f"%{search.lower()}%"
            params.extend([q, q])

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = "SELECT * FROM inventory" + where + " ORDER BY id DESC"
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def get_sold_items(self, **kwargs) -> List[sqlite3.Row]:
        """Get sold inventory items."""
        kwargs["sold_only"] = True
        return self.get_inventory_items(**kwargs)

    def get_sales(self, *args, **kwargs) -> List[sqlite3.Row]:
        """
        Return sold items with optional filters:
          - search='keyword' (matches title or SKU)
          - date_from='YYYY-MM-DD' (inclusive)
          - date_to='YYYY-MM-DD'   (inclusive)
          - limit=int
        Unknown kwargs are ignored.
        """
        search = kwargs.get("search")
        date_from = kwargs.get("date_from")
        date_to = kwargs.get("date_to")
        limit = kwargs.get("limit")

        clauses = ["LOWER(status)='sold'"]
        params: List[Any] = []

        if search:
            clauses.append("(LOWER(title) LIKE ? OR LOWER(sku) LIKE ?)")
            q = f"%{search.lower()}%"
            params.extend([q, q])

        if date_from:
            clauses.append("(sold_date >= ?)")
            params.append(str(date_from))

        if date_to:
            clauses.append("(sold_date <= ?)")
            params.append(str(date_to))

        where = " WHERE " + " AND ".join(clauses)
        sql = "SELECT * FROM inventory" + where + " ORDER BY sold_date DESC, id DESC"
        if isinstance(limit, int) and limit > 0:
            sql += " LIMIT ?"
            params.append(limit)

        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def get_expenses(self, *args, **kwargs) -> List[sqlite3.Row]:
        """Return all expense records."""
        self.cursor.execute("SELECT * FROM expenses ORDER BY date DESC, id DESC")
        return self.cursor.fetchall()

    # ---------------------------- inventory edit helpers ----------------------------

    def get_inventory_item(self, item_id: int) -> Optional[sqlite3.Row]:
        """Fetch a single inventory row by id."""
        try:
            self.cursor.execute("SELECT * FROM inventory WHERE id = ?", (int(item_id),))
            return self.cursor.fetchone()
        except Exception:
            return None

    def update_inventory_item(self, item_id: int, data: Dict[str, Any]) -> bool:
        """
        Update an inventory row. Ignores unknown keys and safely parses numerics/dates.
        Returns True on success, False otherwise (e.g., duplicate SKU).
        """
        allowed = {
            "title", "sku", "condition", "listed_price", "listed_date", "status",
            "sold_price", "sold_date", "quantity", "order_number", "upc",
            "image_url", "description", "category_id", "purchase_price", "cost"
        }

        clean: Dict[str, Any] = {}
        for k, v in (data or {}).items():
            if k not in allowed:
                continue
            if k in {"listed_price", "sold_price", "purchase_price", "cost"}:
                clean[k] = self._parse_float(v)
            elif k in {"listed_date", "sold_date"}:
                clean[k] = self._parse_date_iso(v)
            elif k == "quantity":
                clean[k] = self._safe_int(v, default=1)
            else:
                clean[k] = (None if v == "" else v)

        if not clean:
            return True  # nothing to update

        try:
            sets = ", ".join(f"{k}=:{k}" for k in clean.keys())
            clean["id"] = int(item_id)
            self.cursor.execute(f"UPDATE inventory SET {sets} WHERE id=:id", clean)
            self.conn.commit()
            return True
        except sqlite3.IntegrityError as ie:
            # likely duplicate SKU; log and report False
            try:
                self.cursor.execute(
                    "INSERT INTO error_logs (created_at, context, message) VALUES (?, ?, ?)",
                    (datetime.datetime.now().isoformat(timespec="seconds"),
                     "update_inventory_item",
                     f"IntegrityError: {str(ie)}"),
                )
                self.conn.commit()
            except Exception:
                pass
            return False
        except Exception as e:
            try:
                self.cursor.execute(
                    "INSERT INTO error_logs (created_at, context, message) VALUES (?, ?, ?)",
                    (datetime.datetime.now().isoformat(timespec="seconds"),
                     "update_inventory_item",
                     str(e)),
                )
                self.conn.commit()
            except Exception:
                pass
            return False

    # ---------------------------- dashboard metrics ----------------------------

    def get_total_deductible_expenses(self, *args) -> float:
        self.cursor.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE tax_deductible=1")
        row = self.cursor.fetchone()
        return float(row["total"] or 0.0)

    def get_inventory_value(self, *args) -> float:
        self.cursor.execute(
            "SELECT COALESCE(SUM(listed_price), 0) AS total FROM inventory WHERE LOWER(status)='listed'"
        )
        row = self.cursor.fetchone()
        return float(row["total"] or 0.0)

    def get_total_revenue(self, *args) -> float:
        self.cursor.execute(
            "SELECT COALESCE(SUM(sold_price * COALESCE(quantity,1)), 0) AS total "
            "FROM inventory WHERE LOWER(status)='sold'"
        )
        row = self.cursor.fetchone()
        return float(row["total"] or 0.0)

    def get_total_profit(self, *args) -> float:
        """
        Total profit from sold items.
        Profit = SUM(sold_price * quantity) - SUM(purchase_price * quantity) over SOLD items.
        """
        self.cursor.execute(
            """
            SELECT
              COALESCE(SUM(COALESCE(sold_price,0) * COALESCE(quantity,1)), 0)
              - COALESCE(SUM(COALESCE(purchase_price,0) * COALESCE(quantity,1)), 0)
              AS profit
            FROM inventory
            WHERE LOWER(status) = 'sold'
            """
        )
        row = self.cursor.fetchone()
        return float(row["profit"] or 0.0)

    # ---------------------------- housekeeping ----------------------------

    def clear_error_logs(self):
        self.cursor.execute("DELETE FROM error_logs")
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
