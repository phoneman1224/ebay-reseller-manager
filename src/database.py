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
    """SQLite data layer for the eBay Reseller Manager app."""

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
                cost REAL,
                item_number TEXT,
                location TEXT,
                notes TEXT
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

        # Settings / import mappings
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
        """Ensure legacy DBs have all columns."""
        self.cursor.execute("PRAGMA table_info(inventory)")
        cols = {r["name"] for r in self.cursor.fetchall()}
        for col, ddl in {
            "quantity": "INTEGER DEFAULT 1",
            "purchase_price": "REAL",
            "cost": "REAL",
            "item_number": "TEXT",
            "location": "TEXT",
            "notes": "TEXT",
        }.items():
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
            return int(float(v))
        except Exception:
            return default

    def _parse_float(self, v):
        if v in (None, ""):
            return None
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
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

    # ---------------------------- settings ----------------------------
    def get_import_settings(self):
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
        self.cursor.execute(f"SELECT * FROM inventory{where} ORDER BY id DESC", params)
        return self.cursor.fetchall()

    def get_inventory_item(self, item_id: int):
        self.cursor.execute("SELECT * FROM inventory WHERE id=?", (item_id,))
        return self.cursor.fetchone()

    def get_expenses(self):
        self.cursor.execute("SELECT * FROM expenses ORDER BY date DESC, id DESC")
        return self.cursor.fetchall()

    def get_sold_items(self, *args, **kwargs):
        """Return sold inventory items."""
        kwargs = dict(kwargs or {})
        kwargs["sold_only"] = True
        return self.get_inventory_items(**kwargs)

    # ---------------------------- dashboard metrics ----------------------------
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

    def get_expense_breakdown(self, *args) -> Dict[str, float]:
        """Return total expenses by category."""
        self.cursor.execute(
            "SELECT category, COALESCE(SUM(amount), 0) AS total FROM expenses GROUP BY category ORDER BY total DESC"
        )
        rows = self.cursor.fetchall()
        return {r["category"]: float(r["total"]) for r in rows if r["category"]}

    def get_sales(self, *args, **kwargs):
        """Return sold items (optionally filtered)."""
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

    # ---------------------------- CRUD operations ----------------------------
    def add_inventory_item(self, data: Dict[str, Any]) -> int:
        """Add a new inventory item. Returns the new item's ID."""
        columns = []
        values = []
        for key, val in data.items():
            if val is not None:
                columns.append(key)
                values.append(val)
        
        if not columns:
            raise ValueError("No data provided for inventory item")
        
        placeholders = ",".join("?" * len(columns))
        cols_str = ",".join(columns)
        sql = f"INSERT INTO inventory ({cols_str}) VALUES ({placeholders})"
        
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.lastrowid

    def update_inventory_item(self, item_id: int, data: Dict[str, Any]):
        """Update an existing inventory item."""
        if not data:
            return
        
        set_clause = ",".join(f"{k}=?" for k in data.keys())
        values = list(data.values()) + [item_id]
        
        sql = f"UPDATE inventory SET {set_clause} WHERE id=?"
        self.cursor.execute(sql, values)
        self.conn.commit()

    def upsert_inventory_item(self, sku: str, data: Dict[str, Any]) -> int:
        """Insert or update inventory item by SKU. Returns item ID."""
        if not sku:
            return self.add_inventory_item(data)
        
        # Check if item exists
        self.cursor.execute("SELECT id FROM inventory WHERE sku=?", (sku,))
        row = self.cursor.fetchone()
        
        if row:
            # Update existing
            item_id = row["id"]
            self.update_inventory_item(item_id, data)
            return item_id
        else:
            # Insert new
            data["sku"] = sku
            return self.add_inventory_item(data)

    def delete_inventory_item(self, item_id: int):
        """Delete an inventory item."""
        self.cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
        self.conn.commit()

    def add_expense(self, data: Dict[str, Any]) -> int:
        """Add a new expense. Returns the new expense ID."""
        columns = []
        values = []
        for key, val in data.items():
            if val is not None:
                columns.append(key)
                values.append(val)
        
        if not columns:
            raise ValueError("No data provided for expense")
        
        placeholders = ",".join("?" * len(columns))
        cols_str = ",".join(columns)
        sql = f"INSERT INTO expenses ({cols_str}) VALUES ({placeholders})"
        
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.lastrowid

    def update_expense(self, expense_id: int, data: Dict[str, Any]):
        """Update an existing expense."""
        if not data:
            return
        
        set_clause = ",".join(f"{k}=?" for k in data.keys())
        values = list(data.values()) + [expense_id]
        
        sql = f"UPDATE expenses SET {set_clause} WHERE id=?"
        self.cursor.execute(sql, values)
        self.conn.commit()

    def delete_expense(self, expense_id: int):
        """Delete an expense."""
        self.cursor.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        self.conn.commit()

    def mark_item_as_sold(self, item_id: int, sold_price: float, sold_date: str, 
                          order_number: str = None, quantity: int = None):
        """Mark an inventory item as sold."""
        data = {
            "status": "Sold",
            "sold_price": sold_price,
            "sold_date": sold_date,
        }
        if order_number:
            data["order_number"] = order_number
        if quantity:
            data["quantity"] = quantity
        
        self.update_inventory_item(item_id, data)

    def mark_item_as_listed(self, item_id: int, listed_price: float, 
                           listed_date: str = None, item_number: str = None):
        """Mark an inventory item as listed."""
        data = {
            "status": "Listed",
            "listed_price": listed_price,
        }
        if listed_date:
            data["listed_date"] = listed_date
        if item_number:
            data["item_number"] = item_number
        
        self.update_inventory_item(item_id, data)

    def get_items_for_drafts(self, status: str = "In Stock") -> List:
        """Get items suitable for creating draft listings (typically In Stock items)."""
        self.cursor.execute(
            "SELECT * FROM inventory WHERE LOWER(status)=LOWER(?) ORDER BY title",
            (status,)
        )
        return self.cursor.fetchall()

    def get_condition_id_mapping(self) -> Dict[str, str]:
        """Return eBay condition text to Condition ID mapping."""
        return {
            "New": "1000",
            "New with tags": "1000",
            "New without tags": "1500",
            "New with defects": "1500",
            "Used": "3000",
            "Like New": "2750",
            "Very Good": "4000",
            "Good": "5000",
            "Acceptable": "6000",
            "For parts or not working": "7000",
        }

    # ---------------------------- CSV Import ----------------------------
    def normalize_csv_file(self, filepath: str, report_type: Optional[str] = None, 
                          dry_run: bool = False) -> Dict[str, Any]:
        """
        Normalize an eBay CSV file (Active Listings or Orders Report).
        Auto-detects report type if not specified.
        Returns dict with report_type, normalized_rows, warnings
        """
        import csv as csv_module
        
        warnings = []
        normalized_rows = []
        
        # Detect encoding
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                content = f.read(1024)
        except Exception:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read(1024)
        
        encoding = 'utf-8-sig'
        
        # Read CSV
        with open(filepath, 'r', encoding=encoding, newline='') as f:
            # Skip BOM if present
            reader = csv_module.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return {"report_type": None, "normalized_rows": [], "warnings": ["No data rows found"]}
        
        # Auto-detect report type by examining headers
        headers = list(rows[0].keys())
        
        if report_type is None:
            if "Item number" in headers and "Custom label (SKU)" in headers:
                report_type = "active_listings"
            elif "Order Number" in headers and "Item Title" in headers and "Sold For" in headers:
                report_type = "orders"
            else:
                warnings.append("Could not auto-detect report type")
                return {"report_type": None, "normalized_rows": [], "warnings": warnings}
        
        # Normalize based on report type
        if report_type == "active_listings":
            for idx, row in enumerate(rows, 1):
                try:
                    normalized = self._normalize_active_listing(row)
                    if normalized:
                        normalized_rows.append(normalized)
                except Exception as e:
                    warnings.append(f"Row {idx}: {str(e)}")
        
        elif report_type == "orders":
            for idx, row in enumerate(rows, 1):
                try:
                    # Skip header rows or empty rows
                    if not row.get("Item Title") or not row.get("Sold For"):
                        continue
                    normalized = self._normalize_order(row)
                    if normalized:
                        normalized_rows.append(normalized)
                except Exception as e:
                    warnings.append(f"Row {idx}: {str(e)}")
        
        return {
            "report_type": report_type,
            "normalized_rows": normalized_rows,
            "warnings": warnings
        }

    def _normalize_active_listing(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Normalize an Active Listings CSV row"""
        title = row.get("Title", "").strip()
        if not title:
            return None
        
        # Parse price - try Current price first, then Start price
        price_str = row.get("Current price", "") or row.get("Start price", "")
        listed_price = self._parse_float(price_str)
        
        # Parse date
        date_str = row.get("Start date", "")
        listed_date = self._parse_date_iso(date_str)
        
        return {
            "title": title,
            "sku": row.get("Custom label (SKU)", "").strip(),
            "condition": row.get("Condition", "").strip(),
            "listed_price": listed_price,
            "listed_date": listed_date,
            "status": "Listed",
            "item_number": row.get("Item number", "").strip(),
            "upc": row.get("P:UPC", "").strip(),
            "quantity": self._safe_int(row.get("Available quantity"), 1),
            "category_id": row.get("eBay category 1 number", "").strip(),
        }

    def _normalize_order(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Normalize an Orders Report CSV row"""
        title = row.get("Item Title", "").strip()
        if not title:
            return None
        
        # Parse sold price
        sold_price = self._parse_float(row.get("Sold For", ""))
        
        # Parse date
        date_str = row.get("Sale Date", "")
        sold_date = self._parse_date_iso(date_str)
        
        return {
            "title": title,
            "sku": row.get("Custom Label", "").strip(),
            "sold_price": sold_price,
            "sold_date": sold_date,
            "status": "Sold",
            "quantity": self._safe_int(row.get("Quantity"), 1),
            "order_number": row.get("Order Number", "").strip(),
            "item_number": row.get("Item Number", "").strip(),
        }

    def import_normalized(self, report_type: str, rows: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Import normalized rows into database.
        Uses UPSERT logic (update if SKU exists, insert if new).
        Returns statistics about the import.
        """
        stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}
        
        for row in rows:
            try:
                sku = row.get("sku", "").strip()
                
                if sku:
                    # Check if item exists
                    self.cursor.execute("SELECT id FROM inventory WHERE sku=?", (sku,))
                    existing = self.cursor.fetchone()
                    
                    if existing:
                        # Update existing item
                        item_id = existing["id"]
                        
                        # For active listings, update listing info
                        if report_type == "active_listings":
                            update_data = {
                                "title": row.get("title"),
                                "condition": row.get("condition"),
                                "listed_price": row.get("listed_price"),
                                "listed_date": row.get("listed_date"),
                                "status": "Listed",
                                "item_number": row.get("item_number"),
                            }
                            # Only update non-None values
                            update_data = {k: v for k, v in update_data.items() if v is not None}
                            self.update_inventory_item(item_id, update_data)
                            stats["updated"] += 1
                        
                        # For orders, mark as sold
                        elif report_type == "orders":
                            self.mark_item_as_sold(
                                item_id,
                                row.get("sold_price"),
                                row.get("sold_date"),
                                row.get("order_number"),
                                row.get("quantity")
                            )
                            stats["updated"] += 1
                    
                    else:
                        # Insert new item
                        self.add_inventory_item(row)
                        stats["inserted"] += 1
                
                else:
                    # No SKU - try to match by title or insert as new
                    if report_type == "orders":
                        # For orders without SKU, try to find by title
                        title = row.get("title", "")
                        if title:
                            self.cursor.execute(
                                "SELECT id FROM inventory WHERE LOWER(title)=LOWER(?) AND LOWER(status)!='sold' LIMIT 1",
                                (title,)
                            )
                            match = self.cursor.fetchone()
                            if match:
                                self.mark_item_as_sold(
                                    match["id"],
                                    row.get("sold_price"),
                                    row.get("sold_date"),
                                    row.get("order_number"),
                                    row.get("quantity")
                                )
                                stats["updated"] += 1
                            else:
                                # Insert as new sold item
                                self.add_inventory_item(row)
                                stats["inserted"] += 1
                        else:
                            stats["skipped"] += 1
                    else:
                        # For active listings without SKU, always insert
                        self.add_inventory_item(row)
                        stats["inserted"] += 1
            
            except Exception as e:
                stats["errors"] += 1
                print(f"Import error: {e}")
        
        self.conn.commit()
        return stats

    # ---------------------------- housekeeping ----------------------------
    def clear_error_logs(self):
        self.cursor.execute("DELETE FROM error_logs")
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
