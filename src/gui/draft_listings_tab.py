"""
Draft Listings Tab - Create eBay draft listing CSV files
Supports individual listings and lot listings (multiple items combined)
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QLineEdit, QTextEdit, QGroupBox, QFormLayout,
                             QSpinBox, QDoubleSpinBox, QFileDialog, QMessageBox,
                             QComboBox, QCheckBox, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt
from datetime import datetime
import csv
import os


class DraftListingsTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.selected_items = []  # Track selected items for lot listings
        self.init_ui()
        self.load_inventory()
    
    def init_ui(self):
        """Initialize the draft listings tab UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("📝 Draft Listings Generator")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        header.addWidget(title)
        header.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh Inventory")
        refresh_btn.clicked.connect(self.load_inventory)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # Instructions
        info_label = QLabel(
            "💡 Select items from inventory below, then choose to create individual drafts "
            "or combine into a lot listing."
        )
        info_label.setStyleSheet("background-color: #E3F2FD; padding: 10px; border-radius: 4px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Settings section
        settings_group = QGroupBox("Draft Settings")
        settings_layout = QFormLayout()
        
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("47140 (Clothing, Shoes & Accessories)")
        default_cat = self.db.get_setting("default_category_id", "47140")
        self.category_input.setText(str(default_cat))
        settings_layout.addRow("Default Category ID:", self.category_input)
        
        save_cat_btn = QPushButton("💾 Save as Default")
        save_cat_btn.clicked.connect(self.save_default_category)
        settings_layout.addRow("", save_cat_btn)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Inventory table with checkboxes
        table_label = QLabel("📦 Available Inventory (In Stock Items)")
        table_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        layout.addWidget(table_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "☑", "Title", "SKU", "Condition", "Purchase Cost", 
            "Listed Price", "Category ID", "Description"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # SKU
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Condition
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Cost
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Price
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Category
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Description
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("☑ Select All")
        select_all_btn.clicked.connect(self.select_all_items)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("☐ Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_items)
        button_layout.addWidget(deselect_all_btn)
        
        button_layout.addStretch()
        
        self.selected_count_label = QLabel("Selected: 0 items")
        self.selected_count_label.setStyleSheet("font-weight: bold;")
        button_layout.addWidget(self.selected_count_label)
        
        layout.addLayout(button_layout)
        
        # Generate buttons
        generate_layout = QHBoxLayout()
        generate_layout.addStretch()
        
        individual_btn = QPushButton("📄 Generate Individual Drafts")
        individual_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        individual_btn.clicked.connect(self.generate_individual_drafts)
        generate_layout.addWidget(individual_btn)
        
        lot_btn = QPushButton("📦 Create Lot Listing")
        lot_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        lot_btn.clicked.connect(self.create_lot_listing)
        generate_layout.addWidget(lot_btn)
        
        generate_layout.addStretch()
        layout.addLayout(generate_layout)
    
    def load_inventory(self):
        """Load available inventory items (In Stock status)"""
        try:
            items = self.db.get_items_for_drafts("In Stock")
            
            self.table.setRowCount(0)
            
            for item in items:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Checkbox
                checkbox = QCheckBox()
                checkbox.stateChanged.connect(self.update_selected_count)
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                self.table.setCellWidget(row, 0, checkbox_widget)
                
                # Store item data in checkbox
                checkbox.setProperty("item_data", dict(item))
                
                # Data columns
                self.table.setItem(row, 1, QTableWidgetItem(str(item.get("title", ""))))
                self.table.setItem(row, 2, QTableWidgetItem(str(item.get("sku", ""))))
                self.table.setItem(row, 3, QTableWidgetItem(str(item.get("condition", ""))))
                
                cost = item.get("purchase_price") or item.get("cost") or 0
                self.table.setItem(row, 4, QTableWidgetItem(f"${cost:.2f}"))
                
                price = item.get("listed_price") or 0
                self.table.setItem(row, 5, QTableWidgetItem(f"${price:.2f}"))
                
                category = item.get("category_id", "")
                self.table.setItem(row, 6, QTableWidgetItem(str(category)))
                
                desc = item.get("description", "")
                if desc and len(desc) > 50:
                    desc = desc[:50] + "..."
                self.table.setItem(row, 7, QTableWidgetItem(desc))
            
            self.update_selected_count()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load inventory:\n{str(e)}")
    
    def select_all_items(self):
        """Select all items in the table"""
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
    
    def deselect_all_items(self):
        """Deselect all items in the table"""
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
    
    def update_selected_count(self):
        """Update the count of selected items"""
        count = 0
        self.selected_items = []
        
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    count += 1
                    item_data = checkbox.property("item_data")
                    if item_data:
                        self.selected_items.append(item_data)
        
        self.selected_count_label.setText(f"Selected: {count} items")
    
    def save_default_category(self):
        """Save the default category ID"""
        category_id = self.category_input.text().strip()
        if category_id:
            self.db.set_setting("default_category_id", category_id)
            QMessageBox.information(self, "Saved", f"Default category ID saved: {category_id}")
        else:
            QMessageBox.warning(self, "Invalid", "Please enter a category ID")
    
    def generate_individual_drafts(self):
        """Generate individual draft listings for each selected item"""
        if not self.selected_items:
            QMessageBox.warning(self, "No Items", "Please select at least one item to create drafts")
            return
        
        # Get save location
        default_filename = f"eBay-draft-listings-{datetime.now().strftime('%b-%d-%Y-%H-%M-%S')}.csv"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Draft Listings CSV",
            default_filename,
            "CSV Files (*.csv)"
        )
        
        if not filepath:
            return
        
        try:
            category_id = self.category_input.text().strip() or "47140"
            condition_map = self.db.get_condition_id_mapping()
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                # Write header lines (eBay format requirements)
                csvfile.write('#INFO,Version=0.0.2,Template= eBay-draft-listings-template_US,,,,,,,,\n')
                csvfile.write('#INFO Action and Category ID are required fields. 1) Set Action to Draft 2) Please find the category ID for your listings here: https://pages.ebay.com/sellerinformation/news/categorychanges.html,,,,,,,,,,\n')
                csvfile.write('"#INFO After you\'ve successfully uploaded your draft from the Seller Hub Reports tab, complete your drafts to active listings here: https://www.ebay.com/sh/lst/drafts",,,,,,,,,,\n')
                csvfile.write('#INFO,,,,,,,,,,\n')
                
                # Column headers
                writer = csv.writer(csvfile)
                writer.writerow([
                    'Action(SiteID=US|Country=US|Currency=USD|Version=1193|CC=UTF-8)',
                    'Custom label (SKU)',
                    'Category ID',
                    'Title',
                    'UPC',
                    'Price',
                    'Quantity',
                    'Item photo URL',
                    'Condition ID',
                    'Description',
                    'Format'
                ])
                
                # Write each item
                for item in self.selected_items:
                    condition_text = item.get('condition', 'Used')
                    condition_id = condition_map.get(condition_text, '3000')
                    
                    price = item.get('listed_price') or item.get('purchase_price') or 0
                    
                    description = item.get('description', '')
                    if not description:
                        description = f"<p>{item.get('title', 'Item')}</p>"
                    
                    writer.writerow([
                        'Draft',
                        item.get('sku', ''),
                        item.get('category_id') or category_id,
                        item.get('title', ''),
                        item.get('upc', ''),
                        f"{price:.2f}",
                        item.get('quantity', 1),
                        item.get('image_url', ''),
                        condition_id,
                        description,
                        'FixedPrice'
                    ])
            
            QMessageBox.information(
                self,
                "Success",
                f"Draft listings generated successfully!\n\n"
                f"File: {filepath}\n"
                f"Items: {len(self.selected_items)}\n\n"
                f"Upload this file to eBay Seller Hub → Listings → Upload multiple listings"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate drafts:\n{str(e)}")
    
    def create_lot_listing(self):
        """Create a lot listing combining multiple items"""
        if len(self.selected_items) < 2:
            QMessageBox.warning(
                self,
                "Not Enough Items",
                "Please select at least 2 items to create a lot listing"
            )
            return
        
        # Show lot listing dialog
        dialog = LotListingDialog(self.selected_items, self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            lot_data = dialog.get_lot_data()
            self.save_lot_draft(lot_data)
    
    def save_lot_draft(self, lot_data):
        """Save a lot listing draft to CSV"""
        # Get save location
        default_filename = f"eBay-lot-draft-{datetime.now().strftime('%b-%d-%Y-%H-%M-%S')}.csv"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Lot Draft CSV",
            default_filename,
            "CSV Files (*.csv)"
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                # Write header lines
                csvfile.write('#INFO,Version=0.0.2,Template= eBay-draft-listings-template_US,,,,,,,,\n')
                csvfile.write('#INFO Action and Category ID are required fields. 1) Set Action to Draft 2) Please find the category ID for your listings here: https://pages.ebay.com/sellerinformation/news/categorychanges.html,,,,,,,,,,\n')
                csvfile.write('"#INFO After you\'ve successfully uploaded your draft from the Seller Hub Reports tab, complete your drafts to active listings here: https://www.ebay.com/sh/lst/drafts",,,,,,,,,,\n')
                csvfile.write('#INFO,,,,,,,,,,\n')
                
                # Column headers
                writer = csv.writer(csvfile)
                writer.writerow([
                    'Action(SiteID=US|Country=US|Currency=USD|Version=1193|CC=UTF-8)',
                    'Custom label (SKU)',
                    'Category ID',
                    'Title',
                    'UPC',
                    'Price',
                    'Quantity',
                    'Item photo URL',
                    'Condition ID',
                    'Description',
                    'Format'
                ])
                
                # Write lot listing
                writer.writerow([
                    'Draft',
                    lot_data['sku'],
                    lot_data['category_id'],
                    lot_data['title'],
                    '',
                    f"{lot_data['price']:.2f}",
                    1,
                    '',
                    lot_data['condition_id'],
                    lot_data['description'],
                    'FixedPrice'
                ])
            
            QMessageBox.information(
                self,
                "Success",
                f"Lot draft listing created successfully!\n\n"
                f"File: {filepath}\n\n"
                f"Upload this file to eBay Seller Hub"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save lot draft:\n{str(e)}")


class LotListingDialog(QDialog):
    """Dialog for creating a lot listing from multiple items"""
    
    def __init__(self, items, db, parent=None):
        super().__init__(parent)
        self.items = items
        self.db = db
        self.setWindowTitle("Create Lot Listing")
        self.setModal(True)
        self.resize(600, 500)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Items included
        items_group = QGroupBox(f"Items Included ({len(self.items)} items)")
        items_layout = QVBoxLayout()
        
        items_text = QTextEdit()
        items_text.setReadOnly(True)
        items_text.setMaximumHeight(100)
        
        item_list = []
        total_cost = 0
        for item in self.items:
            title = item.get('title', 'Untitled')
            sku = item.get('sku', '')
            cost = item.get('purchase_price') or item.get('cost') or 0
            total_cost += cost
            item_list.append(f"• {title} (SKU: {sku}) - ${cost:.2f}")
        
        items_text.setPlainText('\n'.join(item_list))
        items_layout.addWidget(items_text)
        
        total_label = QLabel(f"<b>Total Cost: ${total_cost:.2f}</b>")
        items_layout.addWidget(total_label)
        
        items_group.setLayout(items_layout)
        layout.addWidget(items_group)
        
        # Lot details
        details_group = QGroupBox("Lot Listing Details")
        details_layout = QFormLayout()
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Lot of 5 Vintage Items...")
        # Auto-generate title suggestion
        suggested_title = f"Lot of {len(self.items)} Items"
        self.title_input.setText(suggested_title)
        details_layout.addRow("Lot Title:", self.title_input)
        
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("LOT-001")
        self.sku_input.setText(f"LOT-{datetime.now().strftime('%m%d%H%M')}")
        details_layout.addRow("Lot SKU:", self.sku_input)
        
        self.price_input = QDoubleSpinBox()
        self.price_input.setPrefix("$")
        self.price_input.setMaximum(99999.99)
        self.price_input.setDecimals(2)
        # Suggest price as sum of costs + 20% markup
        suggested_price = total_cost * 1.2
        self.price_input.setValue(suggested_price)
        details_layout.addRow("Lot Price:", self.price_input)
        
        self.category_input = QLineEdit()
        default_cat = self.db.get_setting("default_category_id", "47140")
        self.category_input.setText(str(default_cat))
        details_layout.addRow("Category ID:", self.category_input)
        
        self.condition_combo = QComboBox()
        self.condition_combo.addItems([
            "Used", "New", "Like New", "Very Good", 
            "Good", "Acceptable", "For parts or not working"
        ])
        details_layout.addRow("Condition:", self.condition_combo)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Description
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout()
        
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Describe the lot...")
        
        # Auto-generate description
        auto_desc = f"<p><b>Lot of {len(self.items)} Items</b></p>\n<p>This lot includes:</p>\n<ul>\n"
        for item in self.items:
            auto_desc += f"<li>{item.get('title', 'Item')}</li>\n"
        auto_desc += "</ul>\n<p>All items sold as-is.</p>"
        
        self.description_input.setPlainText(auto_desc)
        desc_layout.addWidget(self.description_input)
        
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_lot_data(self):
        """Get the lot listing data"""
        condition_map = self.db.get_condition_id_mapping()
        condition_text = self.condition_combo.currentText()
        condition_id = condition_map.get(condition_text, '3000')
        
        return {
            'title': self.title_input.text(),
            'sku': self.sku_input.text(),
            'price': self.price_input.value(),
            'category_id': self.category_input.text(),
            'condition_id': condition_id,
            'description': self.description_input.toPlainText(),
            'items': self.items
        }
