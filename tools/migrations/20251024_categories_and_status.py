#!/usr/bin/env python3
# Auto-migration to ensure categories & item status columns exist
# Safe to run multiple times.
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / 'data' / 'reseller.db'

def table_exists(cur, name):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,))
    return cur.fetchone() is not None

def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table});")
    return any(row[1] == column for row in cur.fetchall())

if not DB_PATH.exists():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(DB_PATH)
cur = con.cursor()
cur.execute("
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL,
    category_name TEXT NOT NULL,
    parent_id INTEGER,
    leaf INTEGER DEFAULT 1
);
")
cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_categories_category_id ON categories(category_id);")
cur.execute("CREATE INDEX IF NOT EXISTS ix_categories_name ON categories(category_name);")
if table_exists(cur, 'items'):
    if not column_exists(cur, 'items', 'status'):
        cur.execute("ALTER TABLE items ADD COLUMN status TEXT DEFAULT 'stocked';")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_items_status ON items(status);")
    if not column_exists(cur, 'items', 'ebay_category_id'):
        cur.execute("ALTER TABLE items ADD COLUMN ebay_category_id INTEGER;")
else:
    cur.execute("
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY,
        sku TEXT UNIQUE,
        title TEXT,
        price REAL DEFAULT 0,
        qty_on_hand INTEGER DEFAULT 0,
        ebay_category_id INTEGER,
        status TEXT DEFAULT 'stocked'
    );
    ")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_items_status ON items(status);")
con.commit()
con.close()
print('[ok] categories/status migration complete')
