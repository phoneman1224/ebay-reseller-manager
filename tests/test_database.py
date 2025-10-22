"""
Unit tests for database module
"""
import unittest
import os
import sys
import tempfile
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import Database


class TestDatabase(unittest.TestCase):
    """Test cases for Database class"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db = Database(self.test_db.name)
    
    def tearDown(self):
        """Clean up test database"""
        self.db.close()
        if os.path.exists(self.test_db.name):
            os.unlink(self.test_db.name)
    
    def test_add_inventory_item(self):
        """Test adding an inventory item"""
        item_data = {
            'title': 'Test Item',
            'purchase_cost': 10.00,
            'condition': 'New'
        }
        item_id = self.db.add_inventory_item(item_data)
        self.assertIsNotNone(item_id)
        self.assertGreater(item_id, 0)
    
    def test_get_inventory_items(self):
        """Test retrieving inventory items"""
        # Add test item
        item_data = {
            'title': 'Test Item',
            'purchase_cost': 10.00,
            'condition': 'New'
        }
        self.db.add_inventory_item(item_data)

        # Retrieve items
        items = self.db.get_inventory_items()
        self.assertGreater(len(items), 0)
        self.assertEqual(items[0]['title'], 'Test Item')
        self.assertTrue(hasattr(items[0], 'get'))

    def test_update_mapping(self):
        """Mappings should be persisted and retrievable."""
        mapping = {'title': 'Title', 'sku': 'Custom label (SKU)'}
        self.db.update_mapping('active_listings', mapping)
        stored = self.db.get_mapping('active_listings')
        for key, value in mapping.items():
            self.assertEqual(stored.get(key), value)

    def test_inventory_items_expose_purchase_cost(self):
        """Inventory helpers should always expose a purchase_cost alias."""
        item_id = self.db.add_inventory_item({
            'title': 'Alias Item',
            'cost': 12.34,
            'condition': 'Used'
        })

        item = self.db.get_inventory_item(item_id)
        self.assertIn('purchase_cost', item)
        self.assertAlmostEqual(item['purchase_cost'], 12.34)

        items = self.db.get_inventory_items()
        self.assertTrue(any(abs(i['purchase_cost'] - 12.34) < 0.0001 for i in items))
    
    def test_add_expense(self):
        """Test adding an expense"""
        expense_data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'amount': 25.50,
            'category': 'Shipping Supplies',
            'tax_deductible': 1
        }
        expense_id = self.db.add_expense(expense_data)
        self.assertIsNotNone(expense_id)
        self.assertGreater(expense_id, 0)

        breakdown = self.db.get_expense_breakdown()
        self.assertTrue(any(entry['category'] == 'Shipping Supplies' for entry in breakdown))

    def test_get_inventory_value(self):
        """Test calculating inventory value"""
        # Add test items
        self.db.add_inventory_item({
            'title': 'Item 1',
            'purchase_cost': 10.00,
            'condition': 'New',
            'status': 'In Stock'
        })
        self.db.add_inventory_item({
            'title': 'Item 2',
            'purchase_cost': 15.00,
            'condition': 'New',
            'status': 'In Stock'
        })
        
        # Check value
        value = self.db.get_inventory_value()
        self.assertEqual(value, 25.00)
    
    def test_mark_item_as_sold(self):
        """Test marking item as sold"""
        # Add test item
        item_id = self.db.add_inventory_item({
            'title': 'Test Item',
            'purchase_cost': 10.00,
            'condition': 'New'
        })

        # Mark as sold
        self.db.mark_item_as_sold(
            item_id,
            sale_price=25.00,
            sale_date=datetime.now().strftime('%Y-%m-%d'),
            platform='eBay',
            fees=3.25
        )

        # Verify
        item = self.db.get_inventory_item(item_id)
        self.assertEqual(item['status'], 'Sold')
        self.assertEqual(item['sold_price'], 25.00)

    def test_update_inventory_item_accepts_purchase_cost(self):
        """Updating with purchase_cost should persist cost values."""
        item_id = self.db.add_inventory_item({
            'title': 'Cost Alias',
            'purchase_cost': 5.00,
            'condition': 'Used'
        })

        self.db.update_inventory_item(item_id, {
            'title': 'Updated Cost Alias',
            'purchase_cost': 7.25,
        })

        item = self.db.get_inventory_item(item_id)
        self.assertEqual(item['title'], 'Updated Cost Alias')
        self.assertAlmostEqual(item['purchase_cost'], 7.25)

    def test_import_orders_marks_existing_inventory_as_sold(self):
        """Orders CSV import should update matching inventory records."""
        item_id = self.db.add_inventory_item({
            'title': 'Widget',
            'sku': 'SKU-123',
            'purchase_cost': 9.99,
            'status': 'In Stock'
        })

        fd, path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('Order Number,Item Title,Sold For,Sold Date,Quantity,Custom Label\n')
                f.write('1001,Widget,$24.95,02/15/2025,1,SKU-123\n')

            result = self.db.normalize_csv_file(path)
            self.assertEqual(result['report_type'], 'orders')

            rows = result['normalized_rows']
            self.assertEqual(len(rows), 1)

            stats = self.db.import_normalized('orders', rows)
            self.assertGreaterEqual(stats['updated'], 1)

            item = self.db.get_inventory_item(item_id)
            self.assertEqual(item['status'], 'Sold')
            self.assertAlmostEqual(item['sold_price'], 24.95, places=2)
            self.assertTrue((item.get('sold_date') or '').startswith('2025-02-15'))
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_normalize_orders_respects_mapping(self):
        """Custom order mappings should drive CSV normalisation."""
        fd, path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("Order Number,Item Title,My Price,My Date,Qty,Custom Label\n")
                f.write("1234,Test Product,$45.67,01/02/2024,2,SKU-001\n")

            self.db.update_mapping('orders', {
                'title': 'Item Title',
                'sku': 'Custom Label',
                'sold_price': 'My Price',
                'sold_date': 'My Date',
                'quantity': 'Qty',
                'order_number': 'Order Number',
            })

            result = self.db.normalize_csv_file(path, report_type='orders')
            rows = result.get('normalized_rows', [])
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertAlmostEqual(row['sold_price'], 45.67)
            self.assertEqual(row['quantity'], 2)
            self.assertEqual(row['sku'], 'SKU-001')
            self.assertEqual(row['order_number'], '1234')
        finally:
            if os.path.exists(path):
                os.unlink(path)


if __name__ == '__main__':
    unittest.main()
