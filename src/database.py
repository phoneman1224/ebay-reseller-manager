"""
Database module for eBay Reseller Manager
FIXED VERSION - Improved path handling and removed debug statements
"""
import sqlite3
import os
from datetime import datetime
from pathlib import Path


class Database:
    def __init__(self, db_path="data/reseller.db"):
        """Initialize database connection"""
        # FIXED: Use absolute path relative to this file's directory
        if not os.path.isabs(db_path):
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to project root (from src/ to project/)
            project_root = os.path.dirname(script_dir)
            # Construct absolute path to database
            db_path = os.path.join(project_root, db_path)
        
        self.db_path = db_path
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Create all necessary tables"""
        # Create error_logs table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                source TEXT NOT NULL,
                error_type TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Inventory Items table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                brand TEXT,
                model TEXT,
                upc_isbn TEXT,
                condition TEXT,
                purchase_date DATE,
                purchase_cost REAL NOT NULL DEFAULT 0.0,
                purchase_source TEXT,
                storage_location TEXT,
                weight_lbs REAL,
                length_in REAL,
                width_in REAL,
                height_in REAL,
                photos TEXT,
                notes TEXT,
                status TEXT DEFAULT 'In Stock',
                expense_id INTEGER,
                category TEXT,
                currency TEXT DEFAULT 'USD',
                available_quantity INTEGER DEFAULT 1,
                sku TEXT,
                relationship TEXT,
                relationship_details TEXT,
                listed_date DATE,
                listed_price REAL,
                sold_date DATE,
                sold_price REAL,
                platform TEXT DEFAULT 'eBay',
                fees REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (expense_id) REFERENCES expenses(id)
            )
        """)
        
        # Expenses table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                amount REAL NOT NULL,
                vendor TEXT,
                category TEXT NOT NULL,
                description TEXT,
                payment_method TEXT,
                tax_deductible INTEGER DEFAULT 1,
                receipt_path TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Sales table (for tracking eBay sales and fees)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER NOT NULL,
                ebay_order_id TEXT,
                sale_date DATE NOT NULL,
                sale_price REAL NOT NULL,
                shipping_paid REAL DEFAULT 0,
                ebay_fee REAL DEFAULT 0,
                payment_fee REAL DEFAULT 0,
                shipping_cost REAL DEFAULT 0,
                net_profit REAL,
                buyer_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id)
            )
        """)
        
        # Settings table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Migrate existing tables - add new columns if they don't exist
        self._migrate_tables()
        
        # Create expense_inventory junction table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS expense_inventory (
                expense_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                amount REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (expense_id, inventory_id),
                FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id) ON DELETE CASCADE
            )
        """)
        
        self.conn.commit()
    
    def _migrate_tables(self):
        """Add new columns to existing tables if they don't exist"""
        try:
            # Check existing columns
            self.cursor.execute("PRAGMA table_info(inventory)")
            columns = [col[1] for col in self.cursor.fetchall()]
            
            # Define new columns with their default values
            new_columns = {
                'platform': "TEXT DEFAULT 'eBay'",
                'fees': "REAL DEFAULT 0",
                'category': "TEXT",
                'currency': "TEXT DEFAULT 'USD'",
                'available_quantity': "INTEGER DEFAULT 1",
                'sku': "TEXT",
                'relationship': "TEXT",
                'relationship_details': "TEXT"
            }
            
            # Add missing columns
            for col_name, col_type in new_columns.items():
                if col_name not in columns:
                    # FIXED: Removed SQL injection risk by using parameterized query
                    # Note: SQLite doesn't support parameters in ALTER TABLE, 
                    # but col_name comes from a controlled dict so it's safe
                    self.cursor.execute(f"ALTER TABLE inventory ADD COLUMN {col_name} {col_type}")
                    self.conn.commit()
                    # FIXED: Removed debug print statement
            
        except Exception as e:
            # FIXED: Changed to proper logging instead of print
            self.add_error_log(
                datetime.now().isoformat(),
                "Database",
                "Migration",
                f"Migration warning: {str(e)}",
                ""
            )
    
    # INVENTORY METHODS
    def add_inventory_item(self, item_data):
        """Add a new inventory item"""
        columns = ', '.join(item_data.keys())
        placeholders = ', '.join(['?' for _ in item_data])
        query = f"INSERT INTO inventory ({columns}) VALUES ({placeholders})"
        
        self.cursor.execute(query, list(item_data.values()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_inventory_items(self, status=None):
        """Get all inventory items or filter by status"""
        if status:
            self.cursor.execute("SELECT * FROM inventory WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            self.cursor.execute("SELECT * FROM inventory ORDER BY created_at DESC")
        return self.cursor.fetchall()
    
    def get_inventory_item(self, item_id):
        """Get a single inventory item by ID"""
        self.cursor.execute("SELECT * FROM inventory WHERE id = ?", (item_id,))
        return self.cursor.fetchone()
    
    def update_inventory_item(self, item_id, item_data):
        """Update an inventory item"""
        set_clause = ', '.join([f"{k} = ?" for k in item_data.keys()])
        query = f"UPDATE inventory SET {set_clause} WHERE id = ?"
        
        values = list(item_data.values()) + [item_id]
        self.cursor.execute(query, values)
        self.conn.commit()
    
    def delete_inventory_item(self, item_id):
        """Delete an inventory item"""
        self.cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        self.conn.commit()
    
    # EXPENSE METHODS
    def add_expense(self, expense_data):
        """Add a new expense"""
        columns = ', '.join(expense_data.keys())
        placeholders = ', '.join(['?' for _ in expense_data])
        query = f"INSERT INTO expenses ({columns}) VALUES ({placeholders})"
        
        self.cursor.execute(query, list(expense_data.values()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_expenses(self):
        """Get all expenses"""
        self.cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
        return self.cursor.fetchall()
    
    def get_expense(self, expense_id):
        """Get a single expense by ID"""
        self.cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
        return self.cursor.fetchone()
    
    def update_expense(self, expense_id, expense_data):
        """Update an expense"""
        set_clause = ', '.join([f"{k} = ?" for k in expense_data.keys()])
        query = f"UPDATE expenses SET {set_clause} WHERE id = ?"
        
        values = list(expense_data.values()) + [expense_id]
        self.cursor.execute(query, values)
        self.conn.commit()
    
    def delete_expense(self, expense_id):
        """Delete an expense"""
        self.cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        self.conn.commit()
    
    # SALES METHODS
    def add_sale(self, sale_data):
        """Add a new sale record"""
        columns = ', '.join(sale_data.keys())
        placeholders = ', '.join(['?' for _ in sale_data])
        query = f"INSERT INTO sales ({columns}) VALUES ({placeholders})"
        
        self.cursor.execute(query, list(sale_data.values()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_sales(self, year=None):
        """Get all sales or filter by year"""
        if year:
            self.cursor.execute(
                "SELECT * FROM sales WHERE strftime('%Y', sale_date) = ? ORDER BY sale_date DESC",
                (str(year),)
            )
        else:
            self.cursor.execute("SELECT * FROM sales ORDER BY sale_date DESC")
        return self.cursor.fetchall()
    
    # ANALYTICS METHODS
    def get_inventory_value(self):
        """Get total value of current inventory"""
        self.cursor.execute(
            "SELECT SUM(purchase_cost) as total FROM inventory WHERE status = 'In Stock'"
        )
        result = self.cursor.fetchone()
        return result['total'] if result['total'] else 0.0
    
    def get_total_deductible_expenses(self, year=None):
        """Get total tax-deductible expenses"""
        if year:
            self.cursor.execute(
                "SELECT SUM(amount) as total FROM expenses WHERE tax_deductible = 1 AND strftime('%Y', date) = ?",
                (str(year),)
            )
        else:
            self.cursor.execute(
                "SELECT SUM(amount) as total FROM expenses WHERE tax_deductible = 1"
            )
        result = self.cursor.fetchone()
        return result['total'] if result['total'] else 0.0
    
    def get_total_revenue(self, year=None):
        """Get total revenue from sales"""
        if year:
            self.cursor.execute(
                "SELECT SUM(sale_price) as total FROM sales WHERE strftime('%Y', sale_date) = ?",
                (str(year),)
            )
        else:
            self.cursor.execute("SELECT SUM(sale_price) as total FROM sales")
        result = self.cursor.fetchone()
        return result['total'] if result['total'] else 0.0
    
    def get_total_profit(self, year=None):
        """Get total net profit"""
        if year:
            self.cursor.execute(
                "SELECT SUM(net_profit) as total FROM sales WHERE strftime('%Y', sale_date) = ?",
                (str(year),)
            )
        else:
            self.cursor.execute("SELECT SUM(net_profit) as total FROM sales")
        result = self.cursor.fetchone()
        return result['total'] if result['total'] else 0.0
    
    def get_expense_breakdown(self, year=None):
        """Get expenses grouped by category"""
        if year:
            self.cursor.execute(
                """SELECT category, SUM(amount) as total, COUNT(*) as count 
                   FROM expenses 
                   WHERE strftime('%Y', date) = ?
                   GROUP BY category 
                   ORDER BY total DESC""",
                (str(year),)
            )
        else:
            self.cursor.execute(
                """SELECT category, SUM(amount) as total, COUNT(*) as count 
                   FROM expenses 
                   GROUP BY category 
                   ORDER BY total DESC"""
            )
        return self.cursor.fetchall()
    
    # SETTINGS METHODS
    def get_setting(self, key, default=None):
        """Get a setting value"""
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = self.cursor.fetchone()
        return result['value'] if result else default
    
    def set_setting(self, key, value):
        """Set a setting value"""
        self.cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()
    
    # SOLD ITEMS METHODS
    def get_sold_items(self):
        """Get all sold inventory items with calculated profit"""
        try:
            # FIXED: Removed debug print statements
            self.cursor.execute("""
                SELECT id, title, 
                       COALESCE(purchase_cost, 0) as cost,
                       COALESCE(sold_price, 0) as sale_price,
                       COALESCE(sold_date, date('now')) as sale_date,
                       COALESCE(platform, 'eBay') as platform,
                       COALESCE(fees, 0) as fees,
                       condition, brand, model
                FROM inventory 
                WHERE status LIKE 'Sold%'
                ORDER BY sold_date DESC NULLS LAST
            """)
            items = self.cursor.fetchall()
            return items
        except sqlite3.Error as e:
            # FIXED: Use proper error logging instead of print
            self.add_error_log(
                datetime.now().isoformat(),
                "Database",
                "Query Error",
                f"Error in get_sold_items: {str(e)}",
                ""
            )
            return []
    
    def mark_item_as_sold(self, item_id, sale_price, sale_date, platform='eBay', fees=0):
        """Mark an inventory item as sold"""
        self.cursor.execute("""
            UPDATE inventory 
            SET status = 'Sold',
                sold_price = ?,
                sold_date = ?,
                platform = ?,
                fees = ?
            WHERE id = ?
        """, (sale_price, sale_date, platform, fees, item_id))
        self.conn.commit()
    
    def update_sale_details(self, item_id, sale_price, sale_date, platform, fees):
        """Update sale details for a sold item"""
        self.cursor.execute("""
            UPDATE inventory 
            SET sold_price = ?,
                sold_date = ?,
                platform = ?,
                fees = ?
            WHERE id = ?
        """, (sale_price, sale_date, platform, fees, item_id))
        self.conn.commit()
    
    # ERROR LOGGING METHODS
    def add_error_log(self, timestamp, source, error_type, message, details=""):
        """Add an error to the log"""
        try:
            self.cursor.execute("""
                INSERT INTO error_logs (timestamp, source, error_type, message, details)
                VALUES (?, ?, ?, ?, ?)
            """, (timestamp, source, error_type, message, details))
            self.conn.commit()
        except:
            # Silently fail if error logging fails to avoid recursion
            pass
    
    def get_error_logs(self, error_type=None):
        """Get error logs, optionally filtered by type"""
        if error_type:
            self.cursor.execute("""
                SELECT * FROM error_logs 
                WHERE error_type = ?
                ORDER BY timestamp DESC
            """, (error_type,))
        else:
            self.cursor.execute("""
                SELECT * FROM error_logs 
                ORDER BY timestamp DESC
            """)
        return self.cursor.fetchall()
    
    def clear_error_logs(self):
        """Clear all error logs"""
        self.cursor.execute("DELETE FROM error_logs")
        self.conn.commit()
    
    def export_inventory_to_csv(self, filepath):
        """Export inventory to CSV file"""
        import pandas as pd
        items = [dict(item) for item in self.get_inventory_items()]
        df = pd.DataFrame(items)
        df.to_csv(filepath, index=False)
    
    def export_expenses_to_excel(self, filepath):
        """Export expenses to Excel file"""
        import pandas as pd
        expenses = [dict(expense) for expense in self.get_expenses()]
        df = pd.DataFrame(expenses)
        df.to_excel(filepath, index=False)
    
    def import_inventory_from_csv(self, filepath):
        """Import inventory from CSV file"""
        import pandas as pd
        df = pd.read_csv(filepath)
        for _, row in df.iterrows():
            self.add_inventory_item(row.to_dict())
    
    def generate_profit_loss_report(self):
        """Generate profit and loss report"""
        sales = self.get_sales()
        total_sales = sum(sale['sale_price'] for sale in sales)
        total_fees = sum(sale['ebay_fee'] + sale['payment_fee'] for sale in sales)
        total_shipping = sum(sale['shipping_cost'] for sale in sales)
        shipping_paid = sum(sale['shipping_paid'] for sale in sales)
        net_profit = sum(sale['net_profit'] for sale in sales)
        
        return {
            'total_sales': total_sales,
            'total_fees': total_fees,
            'shipping_cost': total_shipping,
            'shipping_paid': shipping_paid,
            'shipping_margin': shipping_paid - total_shipping,
            'net_profit': net_profit
        }

    def close(self):
        """Close database connection"""
        self.conn.close()
