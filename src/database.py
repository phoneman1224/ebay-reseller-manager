# src/database.py
from __future__ import annotations
import os
import csv
import json
import sqlite3
import datetime
from typing import Any, Dict, List, Optional

# Get absolute path for database relative to application directory
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(APP_DIR, "data", "reseller.db")


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

    # Column fallbacks used when normalising CSV imports.  Each value is an
    # ordered list of column names that should be attempted if the user has
    # not customised the mapping for a particular field.
    ACTIVE_IMPORT_DEFAULTS = {
        "title": ["Title"],
        "sku": ["Custom label (SKU)", "Custom Label"],
        "condition": ["Condition"],
        "listed_price": ["Current price", "Start price", "Price"],
        "listed_date": ["Start date", "Start Date"],
    }

    ORDERS_IMPORT_DEFAULTS = {
        "title": ["Item Title", "Title"],
        "sku": ["Custom Label", "Custom label (SKU)", "SKU"],
        "sold_price": ["Sold For", "Total Price", "Sale Price", "Sold Price"],
        "sold_date": ["Sale Date", "Paid on Date", "Paid On Date"],
        "quantity": ["Quantity", "Qty"],
        "order_number": ["Order Number", "Sales Record Number"],
    }

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize database connection and create tables if needed.
        
        Args:
            db_path: Path to SQLite database file. Uses default path if not specified.
        """
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self.create_tables()
        except Exception as e:
            self.log_error("Database initialization failed", str(e))
            raise

    def _row_to_dict(self, row: Any) -> Optional[Dict[str, Any]]:
        """Convert a sqlite3.Row (or similar mapping) to a plain dict.

        The application historically relied on a ``purchase_cost`` key being
        present on inventory records even though the underlying schema stores
        the value as ``cost`` or ``purchase_price``.  Returning a plain dict is
        convenient for the PyQt views, but we also need to preserve those legacy
        aliases so existing widgets do not raise ``KeyError`` when formatting
        values.  This helper normalises the data before handing it back to the
        caller.
        """
        if row is None:
            return None
        if isinstance(row, dict):
            data = dict(row)
        else:
            try:
                data = dict(row)
            except TypeError:
                keys_fn = getattr(row, "keys", lambda: [])
                data = {key: row[key] for key in keys_fn()}

        # Normalise cost aliases for backwards compatibility.
        if "purchase_cost" not in data:
            for alias in ("cost", "purchase_price"):
                if data.get(alias) not in (None, ""):
                    try:
                        data["purchase_cost"] = float(data[alias])
                    except (TypeError, ValueError):
                        data["purchase_cost"] = data[alias]
                    break
        # Ensure the inverse aliases exist when only purchase_cost is present.
        if "purchase_cost" in data:
            for alias in ("cost", "purchase_price"):
                if alias not in data or data[alias] in (None, ""):
                    data[alias] = data["purchase_cost"]

        return data

    def _rows_to_dicts(self, rows: List[Any]) -> List[Dict[str, Any]]:
        """Convert an iterable of rows into dictionaries."""
        return [r for r in (self._row_to_dict(row) for row in rows) if r is not None]

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

    def _resolve_mapped_value(
        self,
        row: Dict[str, Any],
        mapping: Optional[Dict[str, str]],
        field: str,
        fallbacks: List[str],
    ) -> Optional[str]:
        """Return the value for ``field`` using the user-defined mapping.

        The mapping stored in the database allows multiple fallbacks separated
        by the ``|`` character.  We also try a curated list of sensible
        defaults so that freshly exported eBay reports work even before the
        user customises the mapping.  Column matching is case-insensitive.
        """

        candidates: List[str] = []
        if mapping and mapping.get(field):
            candidates.extend(part.strip() for part in mapping[field].split("|") if part.strip())
        candidates.extend([c for c in fallbacks if c])

        if not candidates:
            return None

        lower_key_map = {k.lower(): k for k in row.keys()}

        for column in candidates:
            lookup = column.lower()
            actual_key = column if column in row else lower_key_map.get(lookup)
            if not actual_key:
                continue
            value = row.get(actual_key)
            if value not in (None, ""):
                return value
        return None

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

    def update_mapping(self, report_type: str, mapping: Dict[str, Any]):
        """Persist a mapping for a given report type."""
        mapping_json = json.dumps(mapping)
        self.cursor.execute(
            """
            INSERT INTO import_mappings (report_type, mapping_json)
            VALUES (?, ?)
            ON CONFLICT(report_type) DO UPDATE SET mapping_json=excluded.mapping_json
            """,
            (report_type, mapping_json),
        )
        self.conn.commit()

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
        return self._rows_to_dicts(self.cursor.fetchall())

    def get_inventory_item(self, item_id: int):
        self.cursor.execute("SELECT * FROM inventory WHERE id=?", (item_id,))
        return self._row_to_dict(self.cursor.fetchone())

    def get_expenses(self):
        self.cursor.execute("SELECT * FROM expenses ORDER BY date DESC, id DESC")
        return self._rows_to_dicts(self.cursor.fetchall())

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
        """Return the total value of inventory that has not been sold."""
        self.cursor.execute(
            "SELECT status, listed_price, cost, purchase_price FROM inventory "
            "WHERE status IS NULL OR LOWER(status)!='sold'"
        )
        rows = self.cursor.fetchall()
        total = 0.0
        for row in rows:
            status = (row["status"] or "").lower()
            if status == "listed" and row["listed_price"] is not None:
                total += float(row["listed_price"])
                continue

            cost_val = row["cost"]
            if cost_val is None:
                cost_val = row["purchase_price"]
            if cost_val is not None:
                total += float(cost_val)

        return float(total)

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
                - COALESCE(SUM(COALESCE(
                    CASE 
                        WHEN cost IS NOT NULL THEN cost
                        ELSE purchase_price 
                    END,0) * COALESCE(quantity,1)), 0)
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
        return self._rows_to_dicts(self.cursor.fetchall())

    # ---------------------------- CRUD operations ----------------------------
    def add_inventory_item(self, data: Dict[str, Any]) -> int:
        """Add a new inventory item. Returns the new item's ID."""
        try:
            data = dict(data or {})
            # Normalise legacy field names so callers can continue passing
            # purchase_cost without worrying about the underlying schema.
            if 'purchase_cost' in data:
                purchase_cost = data.pop('purchase_cost')
                if data.get('cost') is None and data.get('purchase_price') is None:
                    data['cost'] = purchase_cost

            columns = []
            values = []
            for key, val in data.items():
                # Treat empty strings as missing values so we don't insert
                # empty-string SKUs which violate the UNIQUE constraint.
                if isinstance(val, str) and val.strip() == "":
                    continue
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
        except Exception as e:
            self.log_error("add_inventory_item", str(e))
            raise

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
        self.cursor.execute("SELECT id, cost, purchase_price FROM inventory WHERE sku=?", (sku,))
        row = self.cursor.fetchone()
        
        if row:
            # Update existing but preserve cost/price fields if they exist
            item_id = row["id"]
            existing = dict(row)
            # Don't override existing cost/price values unless explicitly provided
            if 'purchase_cost' in data and not data.get('purchase_price') and not data.get('cost'):
                data['cost'] = data.pop('purchase_cost')
            if not data.get('cost') and not data.get('purchase_price'):
                if existing.get('cost'):
                    data['cost'] = existing['cost']
                elif existing.get('purchase_price'):
                    data['purchase_price'] = existing['purchase_price']
            self.update_inventory_item(item_id, data)
            return item_id
        else:
            # Insert new - normalize purchase_cost to cost
            if 'purchase_cost' in data:
                data['cost'] = data.pop('purchase_cost')
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

    def mark_item_as_sold(self, item_id: int, sold_price: float = None, sold_date: str = None,
                          order_number: str = None, quantity: int = None, **kwargs):
        """Mark an inventory item as sold."""
        # Accept legacy keyword names used throughout the code base/tests.
        if sold_price is None and "sale_price" in kwargs:
            sold_price = kwargs.pop("sale_price")
        if sold_date is None and "sale_date" in kwargs:
            sold_date = kwargs.pop("sale_date")
        if quantity is None and "qty" in kwargs:
            quantity = kwargs.pop("qty")

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
        return self._rows_to_dicts(self.cursor.fetchall())

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
            headers_lower = {h.lower() for h in headers}

            def has_any(options: List[str]) -> bool:
                return any(opt.lower() in headers_lower for opt in options if opt)

            if has_any(["Item number", "Item Number"]) and has_any(self.ACTIVE_IMPORT_DEFAULTS["sku"]):
                report_type = "active_listings"
            elif (
                has_any(self.ORDERS_IMPORT_DEFAULTS["order_number"])
                and has_any(self.ORDERS_IMPORT_DEFAULTS["title"])
                and has_any(self.ORDERS_IMPORT_DEFAULTS["sold_price"])
            ):
                report_type = "orders"
            else:
                warnings.append("Could not auto-detect report type")
                return {"report_type": None, "normalized_rows": [], "warnings": warnings}
        
        # Normalize based on report type
        mapping = None
        if report_type:
            try:
                mapping = self.get_mapping(report_type)
            except Exception:
                mapping = None

        if report_type == "active_listings":
            for idx, row in enumerate(rows, 1):
                try:
                    normalized = self._normalize_active_listing(row, mapping)
                    if normalized:
                        normalized_rows.append(normalized)
                except Exception as e:
                    warnings.append(f"Row {idx}: {str(e)}")

        elif report_type == "orders":
            for idx, row in enumerate(rows, 1):
                try:
                    normalized = self._normalize_order(row, mapping)
                    if normalized:
                        normalized_rows.append(normalized)
                except Exception as e:
                    warnings.append(f"Row {idx}: {str(e)}")
        
        return {
            "report_type": report_type,
            "normalized_rows": normalized_rows,
            "warnings": warnings
        }

    def _normalize_active_listing(
        self,
        row: Dict[str, str],
        mapping: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Normalize an Active Listings CSV row."""

        title = (self._resolve_mapped_value(
            row, mapping, "title", self.ACTIVE_IMPORT_DEFAULTS["title"]
        ) or "").strip()
        if not title:
            return None

        price_raw = self._resolve_mapped_value(
            row, mapping, "listed_price", self.ACTIVE_IMPORT_DEFAULTS["listed_price"]
        )
        price_str = price_raw or ""
        listed_price = self._parse_float(price_str)

        # Parse date
        date_raw = self._resolve_mapped_value(
            row, mapping, "listed_date", self.ACTIVE_IMPORT_DEFAULTS["listed_date"]
        )
        date_str = date_raw or ""
        listed_date = self._parse_date_iso(date_str)

        return {
            "title": title,
            "sku": (self._resolve_mapped_value(
                row, mapping, "sku", self.ACTIVE_IMPORT_DEFAULTS["sku"]
            ) or "").strip(),
            "condition": (self._resolve_mapped_value(
                row, mapping, "condition", self.ACTIVE_IMPORT_DEFAULTS["condition"]
            ) or "").strip(),
            "listed_price": listed_price,
            "listed_date": listed_date,
            "status": "Listed",
            "item_number": row.get("Item number", "").strip(),
            "upc": row.get("P:UPC", "").strip(),
            "quantity": self._safe_int(row.get("Available quantity"), 1),
            "category_id": row.get("eBay category 1 number", "").strip(),
        }

    def _normalize_order(
        self,
        row: Dict[str, str],
        mapping: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Normalize an Orders Report CSV row."""

        title = (self._resolve_mapped_value(
            row, mapping, "title", self.ORDERS_IMPORT_DEFAULTS["title"]
        ) or "").strip()
        if not title:
            return None

        sold_price_raw = self._resolve_mapped_value(
            row, mapping, "sold_price", self.ORDERS_IMPORT_DEFAULTS["sold_price"]
        )
        sold_price = self._parse_float(sold_price_raw or "")

        if sold_price is None:
            return None

        # Parse date
        date_raw = self._resolve_mapped_value(
            row, mapping, "sold_date", self.ORDERS_IMPORT_DEFAULTS["sold_date"]
        )
        date_str = date_raw or ""
        sold_date = self._parse_date_iso(date_str)

        return {
            "title": title,
            "sku": (self._resolve_mapped_value(
                row, mapping, "sku", self.ORDERS_IMPORT_DEFAULTS["sku"]
            ) or "").strip(),
            "sold_price": sold_price,
            "sold_date": sold_date,
            "status": "Sold",
            "quantity": self._safe_int(
                self._resolve_mapped_value(
                    row, mapping, "quantity", self.ORDERS_IMPORT_DEFAULTS["quantity"]
                ),
                1,
            ),
            "order_number": (self._resolve_mapped_value(
                row, mapping, "order_number", self.ORDERS_IMPORT_DEFAULTS["order_number"]
            ) or "").strip(),
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
                sku = row.get("sku") or ""
                sku = sku.strip()

                # Normalize empty sku to None so our upsert logic treats it as missing
                if sku == "":
                    sku = None

                if sku:
                    # Use upsert helper - it will update existing or insert new
                    # and normalize purchase cost fields as needed
                    # Prepare data: ensure we don't pass empty strings
                    clean_row = {k: (v if not (isinstance(v, str) and v.strip() == "") else None) for k, v in row.items()}
                    item_id = self.upsert_inventory_item(sku, clean_row)
                    # Decide whether this was an insert or update by checking row existence (cheap)
                    # If item existed before, upsert_inventory_item returns existing id after update
                    # We can't easily know inserted vs updated here without extra query; count as updated
                    stats["updated"] += 1
                
                else:
                    # No SKU - try to match by title (orders) or insert as new (active listings)
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
                        clean_row = {k: (v if not (isinstance(v, str) and v.strip() == "") else None) for k, v in row.items()}
                        self.add_inventory_item(clean_row)
                        stats["inserted"] += 1
            
            except Exception as e:
                stats["errors"] += 1
                print(f"Import error: {e}")
        
        self.conn.commit()
        return stats

    # ---------------------------- housekeeping ----------------------------
    def log_error(self, context: str, message: str):
        """Log an error to the database.
        
        Args:
            context: Error context/location
            message: Error message details
        """
        try:
            self.cursor.execute(
                """
                INSERT INTO error_logs (created_at, context, message)
                VALUES (datetime('now'), ?, ?)
                """,
                (context, message)
            )
            self.conn.commit()
        except Exception:
            # If we can't log the error, print it at least
            print(f"Error logging failed - Context: {context}, Message: {message}")
            
    def clear_error_logs(self):
        """Clear all error logs from the database."""
        self.cursor.execute("DELETE FROM error_logs")
        self.conn.commit()

    def close(self):
        """Close the database connection."""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
        except Exception as e:
            print(f"Error closing database: {e}")
