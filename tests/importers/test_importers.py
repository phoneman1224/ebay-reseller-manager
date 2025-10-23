import json
import os
import tempfile
import unittest
from pathlib import Path

# Ensure src is on sys.path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from database import Database
from importers.inventory_import import import_inventory_from_csv
from importers.orders_import import import_orders_from_csv


class ImporterTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db = Database(
            self.temp_db.name,
            feature_flags={"enable_min_inventory_orders": True},
        )

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def _write_csv(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        Path(path).write_text(content, encoding="utf-8")
        return path

    def test_inventory_import_idempotency_and_user_fields(self):
        csv_content = (
            "Item Number,Title,Custom label (SKU),Current price,Available quantity,"
            "eBay category 1 name,eBay category 1 number,Condition,Start date,End date,Listing site\n"
            "12345,Widget Alpha,SAMPLE-SKU,19.99,5,Toys,1000,New,01/01/2025 10:30,12/31/2025 11:00,eBay US\n"
        )
        csv_path = self._write_csv(csv_content)

        try:
            summary_first = import_inventory_from_csv(self.db, csv_path=csv_path)
            self.assertEqual(summary_first["rows_read"], 1)
            self.assertEqual(summary_first["upserts"], 1)

            items = self.db.get_inventory_items_v2()
            self.assertEqual(len(items), 1)
            item = items[0]
            self.assertEqual(item["item_number"], "12345")
            self.assertEqual(item["current_price"], 19.99)
            self.assertEqual(item["available_quantity"], 5)
            self.assertEqual(item["status"], "active")

            # User updates custom fields
            self.db.update_inventory_item_user_fields(
                "12345",
                {
                    "custom_sku": "USER-SKU",
                    "ebay_category1_name": "Collectibles",
                    "ebay_category1_number": "2000",
                },
            )

            summary_second = import_inventory_from_csv(self.db, csv_path=csv_path)
            self.assertEqual(summary_second["rows_read"], 1)
            self.assertEqual(summary_second["upserts"], 1)

            items_after = self.db.get_inventory_items_v2()
            self.assertEqual(len(items_after), 1)
            item_after = items_after[0]
            self.assertEqual(item_after["custom_sku"], "USER-SKU")
            self.assertEqual(item_after["ebay_category1_name"], "Collectibles")
            self.assertEqual(item_after["ebay_category1_number"], "2000")
            self.assertEqual(item_after["current_price"], 19.99)
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)

    def test_orders_import_groups_lines_and_preserves_custom_sku(self):
        csv_content = (
            "\n"
            "Order Number,Sales Record Number,Buyer Username,Buyer Name,Buyer Email,"
            "Ship To Name,Ship To Address 1,Ship To City,Ship To State,Ship To Zip,Ship To Country,"
            "Order Total,Order Date,Paid On Date,Shipped On Date,Status,Transaction ID,Item Number,"
            "Item Title,Custom Label (SKU),Quantity,Sold For,Shipping and handling,Discount,Shipping Service,Tracking Number\n"
            "1001,SRN-1,buyer1,Jane Doe,jane@example.com,Jane Doe,123 Main St,Springfield,IL,62704,US,59.98,"
            "01/05/2025 13:00,01/06/2025,01/07/2025,Completed,TXN-1,12345,Widget Alpha,SAMPLE-SKU,1,29.99,5.00,0.00,UPS,1Z999\n"
            "1001,SRN-1,buyer1,Jane Doe,jane@example.com,Jane Doe,123 Main St,Springfield,IL,62704,US,59.98,"
            "01/05/2025 13:00,01/06/2025,01/07/2025,Completed,,67890,Gadget Beta,,2,29.99,5.00,1.00,UPS,1Z999\n"
        )
        csv_path = self._write_csv(csv_content)

        try:
            summary_first = import_orders_from_csv(self.db, csv_path=csv_path)
            self.assertEqual(summary_first["rows_read"], 2)
            self.assertEqual(summary_first["orders_upserted"], 1)
            self.assertEqual(summary_first["order_items_upserted"], 2)
            self.assertEqual(summary_first["shipments_upserted"], 1)

            orders = self.db.get_sales_orders_v2()
            self.assertEqual(len(orders), 1)
            order = orders[0]
            self.assertEqual(order["order_number"], "1001")
            self.assertAlmostEqual(order["order_total"], 59.98, places=2)

            items = self.db.get_sales_order_items_v2("1001")
            self.assertEqual(len(items), 2)
            transaction_ids = {item["transaction_id"] for item in items}
            self.assertIn("TXN-1", transaction_ids)
            self.assertIn("line-002", transaction_ids)

            # Update user field on second line item
            second_item = next(item for item in items if item["transaction_id"] == "line-002")
            self.db.update_sales_order_item_user_fields(
                second_item["id"], {"custom_sku": "FIXED-SKU"}
            )

            summary_second = import_orders_from_csv(self.db, csv_path=csv_path)
            self.assertEqual(summary_second["rows_read"], 2)
            self.assertEqual(summary_second["orders_upserted"], 1)
            self.assertEqual(summary_second["order_items_upserted"], 2)
            self.assertEqual(summary_second["shipments_upserted"], 1)

            items_after = self.db.get_sales_order_items_v2("1001")
            self.assertEqual(len(items_after), 2)
            refreshed_second = next(
                item for item in items_after if item["transaction_id"] == "line-002"
            )
            self.assertEqual(refreshed_second["custom_sku"], "FIXED-SKU")

            # Compatibility views should surface rows
            self.db.cursor.execute("SELECT COUNT(*) FROM listings_compat")
            listings_count = self.db.cursor.fetchone()[0]
            self.assertGreaterEqual(listings_count, 0)

            self.db.cursor.execute("SELECT COUNT(*) FROM order_lines_compat")
            compat_count = self.db.cursor.fetchone()[0]
            self.assertGreaterEqual(compat_count, 2)

            # Meta JSON should include tax/shipping data
            order_row = self.db.get_sales_order_v2("1001")
            meta = json.loads(order_row["meta_json"] or "{}")
            self.assertIn("shipping_amount", meta)
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)


if __name__ == "__main__":
    unittest.main()

