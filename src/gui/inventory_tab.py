"""
Inventory Tab - Manage inventory items
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QLabel, QDialog,
                             QFormLayout, QLineEdit, QTextEdit, QComboBox,
                             QDateEdit, QDoubleSpinBox, QMessageBox, QHeaderView)
from PyQt6.QtCore import Qt, QDate
from datetime import datetime


class InventoryTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
        self.refresh_data()
    
    def init_ui(self):
        """Initialize the inventory tab UI"""
        layout = QVBoxLayout(self)
        
        # Header with title and buttons
        header = QHBoxLayout()
        
        title = QLabel("📦 Inventory Management")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Filter dropdown
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Items", "In Stock", "Listed", "Sold"])
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        header.addWidget(QLabel("Filter:"))
        header.addWidget(self.filter_combo)
        
        add_btn = QPushButton("➕ Add Item")
        add_btn.clicked.connect(self.add_item_dialog)
        header.addWidget(add_btn)
        
        import_btn = QPushButton("📄 Import from Excel")
        import_btn.clicked.connect(self.show_import_dialog)
        header.addWidget(import_btn)
        
        layout.addLayout(header)
        
        # Statistics bar
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("background-color: #E3F2FD; padding: 10px; border-radius: 4px;")
        stats_layout.addWidget(self.stats_label)
        layout.addLayout(stats_layout)
        
        # Inventory table
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "ID", "Title", "Category", "SKU", "Brand/Model", "Condition", 
            "Purchase Cost", "Start Price", "Status", "Storage", "Notes", "Actions"
        ])
        
        # Make table look nice
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.table)
        
        # Button bar at bottom
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        edit_btn = QPushButton("✏️ Edit Selected")
        edit_btn.clicked.connect(self.edit_item_dialog)
        button_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.clicked.connect(self.delete_item)
        delete_btn.setStyleSheet("background-color: #f44336;")
        button_layout.addWidget(delete_btn)
        
        layout.addLayout(button_layout)
    
    def refresh_data(self):
        """Refresh the inventory table"""
        # Get filter status
        filter_text = self.filter_combo.currentText()
        if filter_text == "All Items":
            items = self.db.get_inventory_items()
        else:
            items = self.db.get_inventory_items(status=filter_text.replace(" ", "_"))
        
        # Update table
        self.table.setRowCount(len(items))
        
        for row, item in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(str(item['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(item['title'] or ''))
            self.table.setItem(row, 2, QTableWidgetItem(item['category'] or ''))
            self.table.setItem(row, 3, QTableWidgetItem(item['sku'] or ''))
            
            brand_model = f"{item['brand'] or ''} {item['model'] or ''}".strip()
            self.table.setItem(row, 4, QTableWidgetItem(brand_model))
            
            self.table.setItem(row, 5, QTableWidgetItem(item['condition'] or ''))
            self.table.setItem(row, 6, QTableWidgetItem(f"${item['purchase_cost']:.2f}"))
            
            start_price = f"${item['start_price']:.2f}" if item['start_price'] else "N/A"
            self.table.setItem(row, 7, QTableWidgetItem(start_price))
            
            self.table.setItem(row, 8, QTableWidgetItem(item['status'] or 'In Stock'))
            self.table.setItem(row, 9, QTableWidgetItem(item['storage_location'] or ''))
            self.table.setItem(row, 10, QTableWidgetItem(item['notes'] or ''))
            
            # Actions - Multiple buttons in a widget
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(4)
            
            # View button
            view_btn = QPushButton("👁️ View")
            view_btn.setToolTip("View Details")
            view_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    font-size: 14px;
                    min-width: 80px;
                }
            """)
            view_btn.clicked.connect(lambda checked, i=item['id']: self.view_item(i))
            actions_layout.addWidget(view_btn)
            
            # Edit button
            edit_btn = QPushButton("✏️ Edit")
            edit_btn.setToolTip("Edit Item")
            edit_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    font-size: 14px;
                    min-width: 80px;
                }
            """)
            edit_btn.clicked.connect(lambda checked, i=item['id']: self.edit_item(i))
            actions_layout.addWidget(edit_btn)
            
            # Mark as Sold button (only for In Stock and Listed items)
            if item['status'] in ['In Stock', 'Listed']:
                sold_btn = QPushButton("💰 Sold")
                sold_btn.setToolTip("Mark as Sold")
                sold_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        padding: 6px 12px;
                        font-size: 14px;
                        min-width: 80px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
                sold_btn.clicked.connect(lambda checked, i=item['id']: self.mark_as_sold_dialog(i))
                actions_layout.addWidget(sold_btn)
            
            self.table.setCellWidget(row, 9, actions_widget)
        
        # Update statistics
        self.update_statistics(items)
    
    def update_statistics(self, items):
        """Update the statistics display"""
        total_items = len(items)
        in_stock = len([i for i in items if i['status'] == 'In Stock'])
        listed = len([i for i in items if i['status'] == 'Listed'])
        sold = len([i for i in items if i['status'] == 'Sold'])
        
        total_value = sum([i['purchase_cost'] for i in items if i['status'] == 'In Stock'])
        
        stats_text = f"Total Items: {total_items} | In Stock: {in_stock} | Listed: {listed} | Sold: {sold} | Inventory Value: ${total_value:.2f}"
        self.stats_label.setText(stats_text)
    
    def apply_filter(self):
        """Apply filter to table"""
        self.refresh_data()
    
    def add_item_dialog(self):
        """Show dialog to add new inventory item"""
        dialog = AddEditItemDialog(self.db, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
    
    def edit_item(self, item_id):
        """Show dialog to edit an item"""
        dialog = AddEditItemDialog(self.db, item_id=item_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
    
    def edit_item_dialog(self):
        """Show dialog to edit selected item"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an item to edit.")
            return
        
        item_id = int(self.table.item(current_row, 0).text())
        self.edit_item(item_id)
    
    def view_item(self, item_id):
        """View full item details"""
        item = self.db.get_inventory_item(item_id)
        if not item:
            return
        
        details = f"""
        <h2>{item['title']}</h2>
        <p><b>Brand:</b> {item['brand'] or 'N/A'}</p>
        <p><b>Model:</b> {item['model'] or 'N/A'}</p>
        <p><b>Condition:</b> {item['condition'] or 'N/A'}</p>
        <p><b>Purchase Cost:</b> ${item['purchase_cost']:.2f}</p>
        <p><b>Purchase Date:</b> {item['purchase_date'] or 'N/A'}</p>
        <p><b>Status:</b> {item['status']}</p>
        <p><b>Storage Location:</b> {item['storage_location'] or 'N/A'}</p>
        <p><b>Description:</b> {item['description'] or 'N/A'}</p>
        <p><b>Notes:</b> {item['notes'] or 'N/A'}</p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Item Details")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(details)
        msg.exec()
    
    def delete_item(self):
        """Delete selected item"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an item to delete.")
            return
        
        reply = QMessageBox.question(
            self,
            'Confirm Delete',
            'Are you sure you want to delete this item?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            item_id = int(self.table.item(current_row, 0).text())
            self.db.delete_inventory_item(item_id)
            self.refresh_data()
    
    def show_import_dialog(self):
        """Show the Excel import dialog"""
        from gui.excel_import import ExcelImportDialog
        dialog = ExcelImportDialog(parent=self, db=self.db)
        dialog.exec()
        self.refresh_data()
    
    def mark_as_sold_dialog(self, item_id):
        """Show dialog to mark item as sold"""
        item = self.db.get_inventory_item(item_id)
        
        if not item:
            QMessageBox.warning(self, "Not Found", "Item not found.")
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("💰 Mark as Sold")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        # Item info
        info_label = QLabel(f"<b>Item:</b> {item['title']}<br><b>Cost:</b> ${item['purchase_cost']:.2f}")
        info_label.setStyleSheet("""
            background-color: #E3F2FD;
            padding: 10px;
            border-radius: 4px;
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Form
        form = QFormLayout()
        
        # Sale Price
        sale_price_input = QLineEdit()
        sale_price_input.setPlaceholderText("Enter sale price")
        form.addRow("Sale Price ($):", sale_price_input)
        
        # Sale Date
        sale_date_input = QDateEdit()
        sale_date_input.setDate(QDate.currentDate())
        sale_date_input.setCalendarPopup(True)
        form.addRow("Sale Date:", sale_date_input)
        
        # Platform
        platform_input = QComboBox()
        platform_input.addItems(["eBay", "Mercari", "Poshmark", "Facebook Marketplace", "OfferUp", "Other"])
        form.addRow("Platform:", platform_input)
        
        # Fees
        fees_input = QLineEdit()
        fees_input.setPlaceholderText("Enter total fees (shipping + platform)")
        fees_input.setText("0.00")
        form.addRow("Total Fees ($):", fees_input)
        
        layout.addLayout(form)
        
        # Profit calculation
        profit_label = QLabel()
        profit_label.setStyleSheet("""
            background-color: #E8F5E9;
            padding: 10px;
            border-radius: 4px;
            font-weight: bold;
        """)
        layout.addWidget(profit_label)
        
        # Update profit calculation
        def update_profit():
            try:
                cost = float(item['purchase_cost'])
                sale_price = float(sale_price_input.text() or 0)
                fees = float(fees_input.text() or 0)
                profit = sale_price - cost - fees
                margin = (profit / cost * 100) if cost > 0 else 0
                
                profit_label.setText(
                    f"💰 Profit: ${profit:.2f} | Margin: {margin:.1f}%"
                )
                
                # Color code
                if profit > 0:
                    profit_label.setStyleSheet("""
                        background-color: #E8F5E9;
                        padding: 10px;
                        border-radius: 4px;
                        font-weight: bold;
                        color: #4CAF50;
                    """)
                else:
                    profit_label.setStyleSheet("""
                        background-color: #FFEBEE;
                        padding: 10px;
                        border-radius: 4px;
                        font-weight: bold;
                        color: #F44336;
                    """)
            except ValueError:
                profit_label.setText("⚠️ Enter valid numbers")
                profit_label.setStyleSheet("""
                    background-color: #FFF3E0;
                    padding: 10px;
                    border-radius: 4px;
                    font-weight: bold;
                """)
        
        sale_price_input.textChanged.connect(update_profit)
        fees_input.textChanged.connect(update_profit)
        update_profit()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💰 Mark as Sold")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(lambda: self.save_sold_item(
            dialog,
            item_id,
            sale_price_input.text(),
            sale_date_input.date().toString("yyyy-MM-dd"),
            platform_input.currentText(),
            fees_input.text()
        ))
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def save_sold_item(self, dialog, item_id, sale_price, sale_date, platform, fees):
        """Save item as sold"""
        try:
            sale_price_val = float(sale_price) if sale_price else 0
            fees_val = float(fees) if fees else 0
            
            if sale_price_val <= 0:
                QMessageBox.warning(self, "Invalid Price", "Please enter a valid sale price.")
                return
            
            # Mark as sold in database
            self.db.mark_item_as_sold(
                item_id,
                sale_price=sale_price_val,
                sale_date=sale_date,
                platform=platform,
                fees=fees_val
            )
            
            QMessageBox.information(
                self,
                "✅ Item Sold!",
                f"Item marked as sold!\n\n"
                f"Sale Price: ${sale_price_val:.2f}\n"
                f"Platform: {platform}\n\n"
                f"Check the 'Sold Items' tab to see your sales history!"
            )
            dialog.accept()
            self.refresh_data()
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for price and fees.")


class AddEditItemDialog(QDialog):
    """Dialog for adding or editing inventory items"""
    def __init__(self, db, item_id=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.item_id = item_id
        self.init_ui()
        
        if item_id:
            self.load_item_data()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("Add Inventory Item" if not self.item_id else "Edit Inventory Item")
        self.setMinimumWidth(500)
        
        layout = QFormLayout(self)
        
        # Form fields
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g., Vintage Canon Camera")
        layout.addRow("Title*:", self.title_input)
        
        self.brand_input = QLineEdit()
        layout.addRow("Brand:", self.brand_input)
        
        self.model_input = QLineEdit()
        layout.addRow("Model:", self.model_input)
        
        self.upc_input = QLineEdit()
        layout.addRow("UPC/ISBN:", self.upc_input)
        
        self.condition_combo = QComboBox()
        self.condition_combo.addItems(["New", "Like New", "Very Good", "Good", "Acceptable", "For Parts"])
        layout.addRow("Condition:", self.condition_combo)
        
        self.cost_input = QDoubleSpinBox()
        self.cost_input.setPrefix("$")
        self.cost_input.setMaximum(99999.99)
        self.cost_input.setDecimals(2)
        layout.addRow("Purchase Cost*:", self.cost_input)
        
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        layout.addRow("Purchase Date:", self.date_input)
        
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("e.g., Garage Sale, Goodwill")
        layout.addRow("Purchase Source:", self.source_input)
        
        self.storage_input = QLineEdit()
        self.storage_input.setPlaceholderText("e.g., Shelf A3, Box 12")
        layout.addRow("Storage Location:", self.storage_input)
        
        # Dimensions
        dim_layout = QHBoxLayout()
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setSuffix(" lbs")
        self.weight_input.setMaximum(999.99)
        dim_layout.addWidget(self.weight_input)
        
        self.length_input = QDoubleSpinBox()
        self.length_input.setSuffix(" in")
        self.length_input.setMaximum(999.99)
        dim_layout.addWidget(self.length_input)
        
        self.width_input = QDoubleSpinBox()
        self.width_input.setSuffix(" in")
        self.width_input.setMaximum(999.99)
        dim_layout.addWidget(self.width_input)
        
        self.height_input = QDoubleSpinBox()
        self.height_input.setSuffix(" in")
        self.height_input.setMaximum(999.99)
        dim_layout.addWidget(self.height_input)
        
        layout.addRow("Dimensions (W×L×H):", dim_layout)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        layout.addRow("Description:", self.description_input)
        
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        layout.addRow("Notes:", self.notes_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_item)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addRow(button_layout)
    
    def load_item_data(self):
        """Load existing item data into form"""
        item = self.db.get_inventory_item(self.item_id)
        if not item:
            return
        
        self.title_input.setText(item['title'] or '')
        self.brand_input.setText(item['brand'] or '')
        self.model_input.setText(item['model'] or '')
        self.upc_input.setText(item['upc_isbn'] or '')
        
        if item['condition']:
            index = self.condition_combo.findText(item['condition'])
            if index >= 0:
                self.condition_combo.setCurrentIndex(index)
        
        self.cost_input.setValue(item['purchase_cost'])
        
        if item['purchase_date']:
            date = QDate.fromString(item['purchase_date'], "yyyy-MM-dd")
            self.date_input.setDate(date)
        
        self.source_input.setText(item['purchase_source'] or '')
        self.storage_input.setText(item['storage_location'] or '')
        
        if item['weight_lbs']:
            self.weight_input.setValue(item['weight_lbs'])
        if item['length_in']:
            self.length_input.setValue(item['length_in'])
        if item['width_in']:
            self.width_input.setValue(item['width_in'])
        if item['height_in']:
            self.height_input.setValue(item['height_in'])
        
        self.description_input.setPlainText(item['description'] or '')
        self.notes_input.setPlainText(item['notes'] or '')
    
    def save_item(self):
        """Save the item to database"""
        # Validate required fields
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Required Field", "Please enter a title.")
            return
        
        if self.cost_input.value() == 0:
            QMessageBox.warning(self, "Required Field", "Please enter a purchase cost.")
            return
        
        # Prepare data
        item_data = {
            'title': self.title_input.text().strip(),
            'brand': self.brand_input.text().strip() or None,
            'model': self.model_input.text().strip() or None,
            'upc_isbn': self.upc_input.text().strip() or None,
            'condition': self.condition_combo.currentText(),
            'purchase_cost': self.cost_input.value(),
            'purchase_date': self.date_input.date().toString("yyyy-MM-dd"),
            'purchase_source': self.source_input.text().strip() or None,
            'storage_location': self.storage_input.text().strip() or None,
            'weight_lbs': self.weight_input.value() if self.weight_input.value() > 0 else None,
            'length_in': self.length_input.value() if self.length_input.value() > 0 else None,
            'width_in': self.width_input.value() if self.width_input.value() > 0 else None,
            'height_in': self.height_input.value() if self.height_input.value() > 0 else None,
            'description': self.description_input.toPlainText().strip() or None,
            'notes': self.notes_input.toPlainText().strip() or None,
        }
        
        # Save to database
        if self.item_id:
            self.db.update_inventory_item(self.item_id, item_data)
            QMessageBox.information(self, "Success", "Item updated successfully!")
        else:
            self.db.add_inventory_item(item_data)
            QMessageBox.information(self, "Success", "Item added successfully!")
        
        self.accept()
