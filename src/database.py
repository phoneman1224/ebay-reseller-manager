# src/database.py
from __future__ import annotations
import os
import csv
import json
import sqlite3
import datetime
from typing import Any, Dict, List, Optional


def _env_flag(name: str, default: bool = False) -> bool:
    """Return True when the given environment variable is truthy."""

    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

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

    def __init__(self, db_path: str = DEFAULT_DB_PATH, *, feature_flags: Optional[Dict[str, bool]] = None):
        """Initialize database connection and create tables if needed.
        
        Args:
            db_path: Path to SQLite database file. Uses default path if not specified.
        """
        try:
            directory = os.path.dirname(db_path)
            # ``:memory:`` (and similar URI forms) do not represent a real
            # filesystem path.  ``os.makedirs`` also raises ``FileNotFoundError``
            # when asked to create ``""`` which is what ``os.path.dirname``
            # returns for paths in the current working directory.  Skip
            # directory creation in those cases so callers can freely use
            # in-memory databases or relative file paths.
            if directory:
                os.makedirs(directory, exist_ok=True)
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self.feature_flags: Dict[str, bool] = dict(feature_flags or {})
            if "enable_min_inventory_orders" not in self.feature_flags:
                self.feature_flags["enable_min_inventory_orders"] = _env_flag(
                    "ENABLE_MIN_INVENTORY_ORDERS"
                )
            self.enable_min_inventory_orders = bool(
                self.feature_flags.get("enable_min_inventory_orders", False)
            )
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
                brand TEXT,
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

        self._ensure_inventory_columns()
        self._ensure_min_inventory_orders_schema()
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
            "brand": "TEXT",
        }.items():
            if col not in cols:
                try:
                    self.cursor.execute(f"ALTER TABLE inventory ADD COLUMN {col} {ddl}")
                except Exception:
                    pass

    def _ensure_min_inventory_orders_schema(self) -> None:
        """Create additive tables for the minimum inventory/orders feature."""

        try:
            from migrations import min_inventory_orders
        except ImportError:  # pragma: no cover - fallback for package usage
            min_inventory_orders = None

        if min_inventory_orders is None:
            return

        min_inventory_orders.run(self.cursor)

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

        # Filter out None/empty keys before calling .lower()
        lower_key_map = {k.lower(): k for k in row.keys() if k}

        for column in candidates:
            if not column:  # Skip None/empty candidates
                continue
            lookup = column.lower()
            actual_key = column if column in row else lower_key_map.get(lookup)
            if not actual_key:
                continue
            value = row.get(actual_key)
            if value not in (None, ""):
                return value
        return None

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
    def get_total_deductible_expenses(self, year: Optional[int] = None) -> float:
        clauses = ["tax_deductible=1"]
        params: List[Any] = []
        if year:
            clauses.append("substr(date, 1, 4)=?")
            params.append(str(year))

        where = " WHERE " + " AND ".join(clauses)
        self.cursor.execute(
            f"SELECT COALESCE(SUM(amount), 0) AS total FROM expenses{where}",
            params,
        )
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

    def get_total_revenue(self, year: Optional[int] = None) -> float:
        clauses = ["LOWER(status)='sold'"]
        params: List[Any] = []
        if year:
            clauses.append("substr(sold_date, 1, 4)=?")
            params.append(str(year))

        where = " WHERE " + " AND ".join(clauses)
        self.cursor.execute(
            f"SELECT COALESCE(SUM(sold_price * COALESCE(quantity,1)), 0) AS total FROM inventory{where}",
            params,
        )
        return float(self.cursor.fetchone()["total"])

    def get_total_profit(self, year: Optional[int] = None) -> float:
        clauses = ["LOWER(status)='sold'"]
        params: List[Any] = []
        if year:
            clauses.append("substr(sold_date, 1, 4)=?")
            params.append(str(year))

        where = " WHERE " + " AND ".join(clauses)
        self.cursor.execute(
            f"""
            SELECT
                COALESCE(SUM(COALESCE(sold_price,0) * COALESCE(quantity,1)), 0)
                - COALESCE(SUM(COALESCE(
                    CASE
                        WHEN cost IS NOT NULL THEN cost
                        ELSE purchase_price
                    END,0) * COALESCE(quantity,1)), 0)
                AS profit
            FROM inventory{where}
            """,
            params,
        )
        return float(self.cursor.fetchone()["profit"])

    def get_expense_breakdown(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return total expenses by category."""

        clauses: List[str] = []
        params: List[Any] = []
        if year:
            clauses.append("substr(date, 1, 4)=?")
            params.append(str(year))

        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        self.cursor.execute(
            f"""
            SELECT
                COALESCE(category, 'Uncategorized') AS category,
                COUNT(*) AS count,
                COALESCE(SUM(amount), 0) AS total
            FROM expenses
            {where}
            GROUP BY COALESCE(category, 'Uncategorized')
            ORDER BY total DESC
            """,
            params,
        )
        rows = self.cursor.fetchall()
        return [
            {
                "category": row["category"],
                "count": row["count"],
                "total": float(row["total"]),
            }
            for row in rows
        ]

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

        data = dict(data)

        # Normalise legacy aliases so callers can continue to pass purchase_cost
        # without knowing that the column is stored as ``cost`` in SQLite.  If
        # the structured cost columns are already supplied we simply drop the
        # alias; otherwise we funnel the value into ``cost`` so the update does
        # not fail with "no such column".
        if "purchase_cost" in data:
            purchase_cost = data.pop("purchase_cost")
            if "cost" not in data and "purchase_price" not in data:
                data["cost"] = purchase_cost

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

    # ---------------------------- min inventory/orders helpers ----------------------------
    def use_min_inventory_orders(self) -> bool:
        """Return True when the modern inventory/orders flow is enabled."""

        return bool(self.feature_flags.get("enable_min_inventory_orders", False))

    def get_inventory_items_v2(self) -> List[Dict[str, Any]]:
        """Return inventory rows from the new ``inventory_items`` table."""

        self.cursor.execute(
            "SELECT * FROM inventory_items ORDER BY LOWER(COALESCE(title, '')) ASC"
        )
        return self._rows_to_dicts(self.cursor.fetchall())

    def get_inventory_item_v2(self, item_number: str) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT * FROM inventory_items WHERE item_number=?",
            (item_number,),
        )
        return self._row_to_dict(self.cursor.fetchone())

    def list_inventory_categories(self) -> List[Dict[str, Optional[str]]]:
        """Return distinct category name/number pairs for dropdowns."""

        self.cursor.execute(
            """
            SELECT DISTINCT
                NULLIF(TRIM(ebay_category1_name), '') AS name,
                NULLIF(TRIM(ebay_category1_number), '') AS number
            FROM inventory_items
            WHERE
                COALESCE(TRIM(ebay_category1_name), '') <> '' OR
                COALESCE(TRIM(ebay_category1_number), '') <> ''
            ORDER BY LOWER(COALESCE(ebay_category1_name), ''),
                     LOWER(COALESCE(ebay_category1_number, ''))
            """
        )
        rows = self.cursor.fetchall()
        return [
            {
                "name": row["name"],
                "number": row["number"],
            }
            for row in rows
        ]

    def get_sales_orders_v2(self) -> List[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT * FROM sales_orders ORDER BY ordered_at DESC, order_number DESC"
        )
        return self._rows_to_dicts(self.cursor.fetchall())

    def get_sales_order_v2(self, order_number: str) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT * FROM sales_orders WHERE order_number=?",
            (order_number,),
        )
        return self._row_to_dict(self.cursor.fetchone())

    def get_sales_order_items_v2(
        self, order_number: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if order_number:
            self.cursor.execute(
                "SELECT * FROM sales_order_items WHERE order_number=? ORDER BY id ASC",
                (order_number,),
            )
        else:
            self.cursor.execute("SELECT * FROM sales_order_items ORDER BY id ASC")
        return self._rows_to_dicts(self.cursor.fetchall())

    def get_sales_order_item_v2(self, order_item_id: int) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT * FROM sales_order_items WHERE id=?",
            (order_item_id,),
        )
        return self._row_to_dict(self.cursor.fetchone())

    def get_shipments_for_order(self, order_number: str) -> List[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT * FROM shipments WHERE order_number=? ORDER BY shipped_on_date",
            (order_number,),
        )
        return self._rows_to_dicts(self.cursor.fetchall())

    def _append_edit_log(
        self,
        entity_type: str,
        entity_pk: Any,
        field: str,
        old_value: Optional[Any],
        new_value: Optional[Any],
        edited_by: Optional[str],
    ) -> None:
        self.cursor.execute(
            """
            INSERT INTO edit_log (entity_type, entity_pk, field, old_value, new_value, edited_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entity_type,
                str(entity_pk),
                field,
                None if old_value is None else str(old_value),
                None if new_value is None else str(new_value),
                edited_by,
            ),
        )

    def update_inventory_item_user_fields(
        self,
        item_number: str,
        updates: Dict[str, Optional[str]],
        *,
        edited_by: Optional[str] = None,
    ) -> bool:
        """Persist user-editable inventory fields and log the change."""

        allowed = {"custom_sku", "ebay_category1_name", "ebay_category1_number"}
        if not updates:
            return False

        current = self.get_inventory_item_v2(item_number)
        if not current:
            return False

        pending: Dict[str, Optional[str]] = {}
        changes: List[tuple] = []
        for field, value in updates.items():
            if field not in allowed:
                continue
            new_value = value.strip() if isinstance(value, str) else value
            if isinstance(new_value, str) and new_value == "":
                new_value = None
            old_value = current.get(field)
            if isinstance(old_value, str) and old_value == "":
                old_value = None
            if old_value == new_value:
                continue
            pending[field] = new_value
            changes.append((field, old_value, new_value))

        if not pending:
            return False

        set_clause = ", ".join(f"{field}=?" for field in pending)
        params = list(pending.values()) + [item_number]
        self.cursor.execute(
            f"UPDATE inventory_items SET {set_clause} WHERE item_number=?",
            params,
        )

        for field, old_value, new_value in changes:
            self._append_edit_log(
                "inventory_item",
                item_number,
                field,
                old_value,
                new_value,
                edited_by,
            )

        self.conn.commit()
        return True

    def update_sales_order_item_user_fields(
        self,
        order_item_id: int,
        updates: Dict[str, Optional[str]],
        *,
        edited_by: Optional[str] = None,
    ) -> bool:
        """Persist user-editable order item fields and log the change."""

        if not updates:
            return False

        current = self.get_sales_order_item_v2(order_item_id)
        if not current:
            return False

        pending: Dict[str, Optional[str]] = {}
        changes: List[tuple] = []
        for field in ("custom_sku",):
            if field not in updates:
                continue
            value = updates[field]
            new_value = value.strip() if isinstance(value, str) else value
            if isinstance(new_value, str) and new_value == "":
                new_value = None
            old_value = current.get(field)
            if isinstance(old_value, str) and old_value == "":
                old_value = None
            if old_value == new_value:
                continue
            pending[field] = new_value
            changes.append((field, old_value, new_value))

        if not pending:
            return False

        set_clause = ", ".join(f"{field}=?" for field in pending)
        params = list(pending.values()) + [order_item_id]
        self.cursor.execute(
            f"UPDATE sales_order_items SET {set_clause} WHERE id=?",
            params,
        )

        for field, old_value, new_value in changes:
            self._append_edit_log(
                "sales_order_item",
                order_item_id,
                field,
                old_value,
                new_value,
                edited_by,
            )

        self.conn.commit()
        return True

    def upsert_inventory_item_from_feed(
        self,
        record: Dict[str, Any],
        *,
        timestamp: Optional[str] = None,
    ) -> bool:
        """Insert or update an inventory item from the active listings feed."""

        item_number = record.get("item_number")
        if not item_number:
            raise ValueError("item_number is required")

        timestamp = timestamp or datetime.datetime.utcnow().isoformat()
        existing = self.get_inventory_item_v2(item_number)

        def _normalize(field: str) -> Optional[Any]:
            value = record.get(field)
            if isinstance(value, str):
                value = value.strip()
                if value == "":
                    value = None
            return value

        payload = {
            "item_number": item_number,
            "title": record.get("title"),
            "custom_sku": _normalize("custom_sku"),
            "current_price": record.get("current_price"),
            "available_quantity": record.get("available_quantity"),
            "ebay_category1_name": _normalize("ebay_category1_name"),
            "ebay_category1_number": _normalize("ebay_category1_number"),
            "condition": _normalize("condition"),
            "listing_site": _normalize("listing_site"),
            "start_date": _normalize("start_date"),
            "end_date": _normalize("end_date"),
            "status": record.get("status", "active"),
            "last_sync_at": timestamp,
        }

        if existing:
            for field in ("custom_sku", "ebay_category1_name", "ebay_category1_number"):
                current_value = existing.get(field)
                if isinstance(current_value, str) and current_value.strip() == "":
                    current_value = None
                if current_value not in (None, ""):
                    payload[field] = current_value
            self.cursor.execute(
                """
                UPDATE inventory_items
                SET
                    title=:title,
                    current_price=:current_price,
                    available_quantity=:available_quantity,
                    ebay_category1_name=:ebay_category1_name,
                    ebay_category1_number=:ebay_category1_number,
                    condition=:condition,
                    listing_site=:listing_site,
                    start_date=:start_date,
                    end_date=:end_date,
                    status='active',
                    last_sync_at=:last_sync_at,
                    custom_sku=:custom_sku
                WHERE item_number=:item_number
                """,
                payload,
            )
            return False

        self.cursor.execute(
            """
            INSERT INTO inventory_items (
                item_number,
                title,
                custom_sku,
                current_price,
                available_quantity,
                ebay_category1_name,
                ebay_category1_number,
                condition,
                listing_site,
                start_date,
                end_date,
                status,
                last_sync_at
            ) VALUES (
                :item_number,
                :title,
                :custom_sku,
                :current_price,
                :available_quantity,
                :ebay_category1_name,
                :ebay_category1_number,
                :condition,
                :listing_site,
                :start_date,
                :end_date,
                :status,
                :last_sync_at
            )
            """,
            payload,
        )
        return True

    def upsert_sales_order_from_feed(self, record: Dict[str, Any]) -> bool:
        """Insert or update a sales order from the completed-orders feed."""

        order_number = record.get("order_number")
        if not order_number:
            raise ValueError("order_number is required")

        existing = self.get_sales_order_v2(order_number)
        self.cursor.execute(
            """
            INSERT INTO sales_orders (
                order_number,
                sales_record_number,
                buyer_username,
                buyer_name,
                buyer_email,
                ship_to_name,
                ship_to_phone,
                ship_to_address_1,
                ship_to_address_2,
                ship_to_city,
                ship_to_state,
                ship_to_zip,
                ship_to_country,
                order_total,
                ordered_at,
                paid_at,
                shipped_on_date,
                status,
                meta_json
            ) VALUES (
                :order_number,
                :sales_record_number,
                :buyer_username,
                :buyer_name,
                :buyer_email,
                :ship_to_name,
                :ship_to_phone,
                :ship_to_address_1,
                :ship_to_address_2,
                :ship_to_city,
                :ship_to_state,
                :ship_to_zip,
                :ship_to_country,
                :order_total,
                :ordered_at,
                :paid_at,
                :shipped_on_date,
                :status,
                :meta_json
            )
            ON CONFLICT(order_number) DO UPDATE SET
                sales_record_number=excluded.sales_record_number,
                buyer_username=excluded.buyer_username,
                buyer_name=excluded.buyer_name,
                buyer_email=excluded.buyer_email,
                ship_to_name=excluded.ship_to_name,
                ship_to_phone=excluded.ship_to_phone,
                ship_to_address_1=excluded.ship_to_address_1,
                ship_to_address_2=excluded.ship_to_address_2,
                ship_to_city=excluded.ship_to_city,
                ship_to_state=excluded.ship_to_state,
                ship_to_zip=excluded.ship_to_zip,
                ship_to_country=excluded.ship_to_country,
                order_total=excluded.order_total,
                ordered_at=excluded.ordered_at,
                paid_at=excluded.paid_at,
                shipped_on_date=excluded.shipped_on_date,
                status=excluded.status,
                meta_json=excluded.meta_json
            """,
            record,
        )
        return existing is None

    def upsert_sales_order_item_from_feed(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Insert/update a sales order item while preserving user fields."""

        order_number = record.get("order_number")
        if not order_number:
            raise ValueError("order_number is required")

        transaction_id = record.get("transaction_id")
        lookup_params = (order_number, transaction_id, transaction_id)
        self.cursor.execute(
            """
            SELECT id, custom_sku FROM sales_order_items
            WHERE order_number=?
              AND ((transaction_id IS NULL AND ? IS NULL) OR transaction_id=?)
            ORDER BY id ASC
            LIMIT 1
            """,
            lookup_params,
        )
        existing = self.cursor.fetchone()

        payload = dict(record)
        if existing and existing["custom_sku"] not in (None, ""):
            payload["custom_sku"] = existing["custom_sku"]

        if existing:
            payload["id"] = existing["id"]
            self.cursor.execute(
                """
                UPDATE sales_order_items
                SET
                    item_number=:item_number,
                    item_title_snapshot=:item_title_snapshot,
                    custom_sku=:custom_sku,
                    quantity=:quantity,
                    unit_price=:unit_price,
                    tax_amount=:tax_amount,
                    shipping_amount=:shipping_amount,
                    discount_amount=:discount_amount
                WHERE id=:id
                """,
                payload,
            )
            return {"id": existing["id"], "inserted": False}

        self.cursor.execute(
            """
            INSERT INTO sales_order_items (
                order_number,
                transaction_id,
                item_number,
                item_title_snapshot,
                custom_sku,
                quantity,
                unit_price,
                tax_amount,
                shipping_amount,
                discount_amount
            ) VALUES (
                :order_number,
                :transaction_id,
                :item_number,
                :item_title_snapshot,
                :custom_sku,
                :quantity,
                :unit_price,
                :tax_amount,
                :shipping_amount,
                :discount_amount
            )
            """,
            payload,
        )
        return {"id": self.cursor.lastrowid, "inserted": True}

    def upsert_shipment_from_feed(self, record: Dict[str, Any]) -> Optional[bool]:
        """Insert or update a shipment. Returns True if inserted, False if updated."""

        tracking_number = record.get("tracking_number")
        if not tracking_number:
            return None

        self.cursor.execute(
            "SELECT id FROM shipments WHERE tracking_number=?",
            (tracking_number,),
        )
        existing = self.cursor.fetchone()

        self.cursor.execute(
            """
            INSERT INTO shipments (
                order_number,
                shipping_service,
                tracking_number,
                label_cost,
                shipped_on_date
            ) VALUES (
                :order_number,
                :shipping_service,
                :tracking_number,
                :label_cost,
                :shipped_on_date
            )
            ON CONFLICT(tracking_number) DO UPDATE SET
                order_number=excluded.order_number,
                shipping_service=excluded.shipping_service,
                label_cost=excluded.label_cost,
                shipped_on_date=excluded.shipped_on_date
            """,
            record,
        )
        return existing is None

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
