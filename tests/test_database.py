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


if __name__ == '__main__':
    unittest.main()
