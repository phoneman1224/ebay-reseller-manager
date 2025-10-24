from pathlib import Path
import sqlite3
from typing import Optional

VALID_STATUSES = ("stocked", "listed", "sold", "archived")

class ItemService:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def set_status(self, item_id: int, status: str) -> bool:
        if status not in VALID_STATUSES:
            raise ValueError(f'Invalid status: {status}')
        con = self._conn()
        cur = con.cursor()
        cur.execute("UPDATE items SET status=? WHERE id=?", (status, item_id))
        con.commit()
        ok = cur.rowcount > 0
        con.close()
        return ok

    def set_category(self, item_id: int, ebay_category_id: int) -> bool:
        con = self._conn()
        cur = con.cursor()
        cur.execute("UPDATE items SET ebay_category_id=? WHERE id=?", (ebay_category_id, item_id))
        con.commit()
        ok = cur.rowcount > 0
        con.close()
        return ok

    def get(self, item_id: int):
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT id, sku, title, price, qty_on_hand, ebay_category_id, status FROM items WHERE id=?", (item_id,))
        row = cur.fetchone()
        con.close()
        return row
