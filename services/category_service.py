from pathlib import Path
import sqlite3
from typing import List, Tuple, Optional

class CategoryService:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def list_categories(self, search: Optional[str] = None) -> List[Tuple[int, int, str]]:
        con = self._conn()
        cur = con.cursor()
        if search:
            cur.execute("SELECT id, category_id, category_name FROM categories WHERE category_name LIKE ? ORDER BY category_name ASC", (f'%{search}%',))
        else:
            cur.execute("SELECT id, category_id, category_name FROM categories ORDER BY category_name ASC")
        rows = cur.fetchall()
        con.close()
        return rows

    def upsert_category(self, category_id: int, category_name: str, parent_id: Optional[int] = None, leaf: int = 1) -> int:
        con = self._conn()
        cur = con.cursor()
        cur.execute("
            INSERT INTO categories (category_id, category_name, parent_id, leaf)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category_id) DO UPDATE SET category_name=excluded.category_name, parent_id=excluded.parent_id, leaf=excluded.leaf
        ", (category_id, category_name, parent_id, leaf))
        con.commit()
        cur.execute("SELECT id FROM categories WHERE category_id=?", (category_id,))
        row = cur.fetchone()
        con.close()
        return row[0] if row else 0

    def delete_category(self, category_id: int) -> None:
        con = self._conn()
        cur = con.cursor()
        cur.execute("DELETE FROM categories WHERE category_id=?", (category_id,))
        con.commit()
        con.close()
