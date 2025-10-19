"""
Expenses Tab - Track and manage business expenses
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel, QDialog,
                             QFormLayout, QLineEdit, QTextEdit, QComboBox,
                             QDateEdit, QDoubleSpinBox, QMessageBox, QCheckBox,
                             QHeaderView, QFileDialog, QGroupBox)
from PyQt6.QtCore import Qt, QDate
from datetime import datetime


class ExpensesTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
        self.refresh_data()
    
    def init_ui(self):
        """Initialize the expenses tab UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("💵 Expense Tracking")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        header.addWidget(title)
        
        header.addStretch()
        
        add_btn = QPushButton("➕ Add Expense")
        add_btn.clicked.connect(self.add_expense_dialog)
        header.addWidget(add_btn)
        
        layout.addLayout(header)
        
        # Statistics bar
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("background-color: #E8F5E9; padding: 10px; border-radius: 4px;")
        stats_layout.addWidget(self.stats_label)
        layout.addLayout(stats_layout)
        
        # Expenses table
        self.table = QTableWidget()
        # We display the following columns: ID, Date, Amount, Category,
        # Connected Items (count) and Tax Deductible.  Previously the
        # "Vendor" column occupied the 5th position; it has been replaced
        # with a count of connected inventory items.
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Date", "Amount", "Category", "Items", "Tax Deductible"
        ])
        # Adjust column sizing.  Distribute available width evenly across
        # all columns to prevent any single column (such as Category)
        # from growing excessively wide.  Using Stretch here means each
        # column shares the table width proportionally.
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Table aesthetics
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.table)
        
        # Button bar at bottom
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        edit_btn = QPushButton("✏️ Edit Selected")
        edit_btn.clicked.connect(self.edit_expense_dialog)
        edit_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                font-size: 14px;
                min-width: 100px;
            }
        """)
        button_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.clicked.connect(self.delete_expense)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 6px 12px;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        button_layout.addWidget(delete_btn)
        
        layout.addLayout(button_layout)
    
    def refresh_data(self):
        """Refresh the expenses table"""
        expenses = self.db.get_expenses()
        
        # Update table
        self.table.setRowCount(len(expenses))
        
        for row, expense in enumerate(expenses):
            # ID
            self.table.setItem(row, 0, QTableWidgetItem(str(expense['id'])))
            # Date
            self.table.setItem(row, 1, QTableWidgetItem(expense['date'] or ''))
            # Amount
            self.table.setItem(row, 2, QTableWidgetItem(f"${expense['amount']:.2f}"))
            # Category
            self.table.setItem(row, 3, QTableWidgetItem(expense['category'] or ''))
            # Connected inventory items (count)
            try:
                item_count = self.db.get_expense_inventory_count(expense['id'])
            except Exception:
                item_count = 0
            self.table.setItem(row, 4, QTableWidgetItem(str(item_count)))
            
            # Tax deductible indicator
            deductible = "✓ Yes" if expense['tax_deductible'] else "✗ No"
            deductible_item = QTableWidgetItem(deductible)
            if expense['tax_deductible']:
                deductible_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                deductible_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 5, deductible_item)
        
        # Update statistics
        self.update_statistics(expenses)
    
    def update_statistics(self, expenses):
        """Update the statistics display"""
        total_expenses = sum([e['amount'] for e in expenses])
        deductible = sum([e['amount'] for e in expenses if e['tax_deductible']])
        non_deductible = total_expenses - deductible
        
        current_year = datetime.now().year
        year_deductible = self.db.get_total_deductible_expenses(current_year)
        
        stats_text = (f"Total Expenses: ${total_expenses:.2f} | "
                     f"Tax Deductible: ${deductible:.2f} | "
                     f"Non-Deductible: ${non_deductible:.2f} | "
                     f"{current_year} YTD Deductible: ${year_deductible:.2f}")
        self.stats_label.setText(stats_text)
    
    def add_expense_dialog(self):
        """Show dialog to add new expense"""
        try:
            dialog = AddEditExpenseDialog(self.db, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open expense dialog:\n{str(e)}")
            print(f"Error opening expense dialog: {e}")
            import traceback
            traceback.print_exc()
    
    def edit_expense(self, expense_id):
        """Show dialog to edit an expense"""
        dialog = AddEditExpenseDialog(self.db, expense_id=expense_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
    
    def edit_expense_dialog(self):
        """Show dialog to edit selected expense"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an expense to edit.")
            return
        
        expense_id = int(self.table.item(current_row, 0).text())
        self.edit_expense(expense_id)
    
    def view_expense(self, expense):
        """View full expense details"""
        # Convert to dict if it's a Row object
        if not isinstance(expense, dict):
            expense = dict(expense)
        
        # Get full expense details
        full_expense = self.db.get_expense(expense['id'])
        if not isinstance(full_expense, dict):
            full_expense = dict(full_expense)
        
        # Build inventory items section (this feature isn't implemented in DB yet)
        inventory_section = "<p><i>No inventory items connected</i></p>"
        
        details = f"""
        <h2>Expense Details</h2>
        <p><b>Date:</b> {full_expense.get('date', 'N/A')}</p>
        <p><b>Amount:</b> ${full_expense.get('amount', 0):.2f}</p>
        <p><b>Category:</b> {full_expense.get('category', 'N/A')}</p>
        <p><b>Vendor:</b> {full_expense.get('vendor') or 'N/A'}</p>
        <p><b>Payment Method:</b> {full_expense.get('payment_method') or 'N/A'}</p>
        <p><b>Tax Deductible:</b> {'Yes' if full_expense.get('tax_deductible') else 'No'}</p>
        <p><b>Description:</b> {full_expense.get('description') or 'N/A'}</p>
        <p><b>Notes:</b> {full_expense.get('notes') or 'N/A'}</p>
        {inventory_section}
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Expense Details")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(details)
        msg.exec()
    
    def delete_expense(self):
        """Delete selected expense"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an expense to delete.")
            return
        
        reply = QMessageBox.question(
            self,
            'Confirm Delete',
            'Are you sure you want to delete this expense?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            expense_id = int(self.table.item(current_row, 0).text())
            self.db.delete_expense(expense_id)
            self.refresh_data()


class AddEditExpenseDialog(QDialog):
    """Dialog for adding or editing expenses"""
    
    CATEGORIES = [
        "Inventory Purchase",
        "Shipping Supplies",
        "Storage/Rent",
        "Equipment & Tools",
        "Mileage/Travel",
        "Software/Subscriptions",
        "Office Supplies",
        "Marketing/Advertising",
        "Packaging Materials",
        "Professional Services",
        "Other"
    ]
    
    PAYMENT_METHODS = [
        "Cash",
        "Credit Card",
        "Debit Card",
        "PayPal",
        "Check",
        "Bank Transfer",
        "Other"
    ]

    # Define a default tax-deductible status for each category.  Most business
    # expenses are typically deductible, but "Other" is defaulted to False
    # so that the user can intentionally mark miscellaneous items as
    # non-deductible.  Feel free to adjust this mapping to reflect your
    # specific tax guidance.
    CATEGORY_TAX_DEDUCTIBLE_MAP = {
        "Inventory Purchase": True,
        "Shipping Supplies": True,
        "Storage/Rent": True,
        "Equipment & Tools": True,
        "Mileage/Travel": True,
        "Software/Subscriptions": True,
        "Office Supplies": True,
        "Marketing/Advertising": True,
        "Packaging Materials": True,
        "Professional Services": True,
        "Other": False,
    }
    
    def __init__(self, db, expense_id=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.expense_id = expense_id
        self.receipt_path = None
        self.selected_inventory_items = []  # FIXED: Initialize this!
        # Flag indicating whether we are editing an existing expense
        self.is_editing = expense_id is not None
        self.init_ui()
        
        if expense_id:
            self.load_expense_data()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        try:
            self.setWindowTitle("Add Expense" if not self.expense_id else "Edit Expense")
            self.setMinimumWidth(500)
            
            layout = QFormLayout(self)
        
            # Date
            self.date_input = QDateEdit()
            self.date_input.setDate(QDate.currentDate())
            self.date_input.setCalendarPopup(True)
            layout.addRow("Date*:", self.date_input)
            
            # Amount
            self.amount_input = QDoubleSpinBox()
            self.amount_input.setPrefix("$")
            self.amount_input.setMaximum(99999.99)
            self.amount_input.setDecimals(2)
            layout.addRow("Amount*:", self.amount_input)
            
            # Category
            self.category_combo = QComboBox()
            self.category_combo.addItems(self.CATEGORIES)
            layout.addRow("Category*:", self.category_combo)
            # Automatically set tax deductible based on category when it changes
            self.category_combo.currentIndexChanged.connect(self.on_category_changed)
            
            # Vendor
            self.vendor_input = QLineEdit()
            self.vendor_input.setPlaceholderText("e.g., Walmart, Amazon, Goodwill")
            layout.addRow("Vendor:", self.vendor_input)
            
            # Payment Method
            self.payment_combo = QComboBox()
            self.payment_combo.addItems(self.PAYMENT_METHODS)
            layout.addRow("Payment Method:", self.payment_combo)
            
            # Tax Deductible
            self.deductible_check = QCheckBox("This expense is tax deductible")
            self.deductible_check.setChecked(True)
            layout.addRow("", self.deductible_check)
            
            # Connected Inventory Items
            self.inventory_items_group = QGroupBox("Connected Inventory Items")
            inventory_layout = QVBoxLayout()
            
            # Add item selection
            item_header = QHBoxLayout()
            label = QLabel("Select Items:")
            item_header.addWidget(label)
            
            add_item_btn = QPushButton("➕ Add Item")
            add_item_btn.clicked.connect(self.add_inventory_item)
            add_item_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    font-size: 14px;
                    min-width: 80px;
                }
            """)
            item_header.addWidget(add_item_btn)
            inventory_layout.addLayout(item_header)
            
            # List of selected items
            self.inventory_items_layout = QVBoxLayout()
            inventory_layout.addLayout(self.inventory_items_layout)
            
            self.inventory_items_group.setLayout(inventory_layout)
            layout.addRow(self.inventory_items_group)
            
            # Store selected items
            self.selected_inventory_items = []
            
            # Description
            self.description_input = QTextEdit()
            self.description_input.setMaximumHeight(60)
            self.description_input.setPlaceholderText("Brief description of the expense")
            layout.addRow("Description:", self.description_input)
            
            # Notes
            self.notes_input = QTextEdit()
            self.notes_input.setMaximumHeight(60)
            self.notes_input.setPlaceholderText("Additional notes (optional)")
            layout.addRow("Notes:", self.notes_input)
            
            # Receipt
            receipt_layout = QHBoxLayout()
            self.receipt_label = QLabel("No receipt attached")
            receipt_layout.addWidget(self.receipt_label)
            
            attach_btn = QPushButton("📎 Attach Receipt")
            attach_btn.clicked.connect(self.attach_receipt)
            attach_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    font-size: 14px;
                    min-width: 100px;
                }
            """)
            receipt_layout.addWidget(attach_btn)
            
            layout.addRow("Receipt:", receipt_layout)
            
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            save_btn = QPushButton("💾 Save")
            save_btn.clicked.connect(self.save_expense)
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 6px 12px;
                    font-size: 14px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            button_layout.addWidget(save_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            cancel_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    font-size: 14px;
                    min-width: 80px;
                }
            """)
            button_layout.addWidget(cancel_btn)
            
            layout.addRow(button_layout)

            # Apply initial tax deductible setting based on the selected
            # category for new expenses (skip for editing existing ones).
            if not self.is_editing:
                # Delay the call slightly to ensure the combo box has been
                # populated and its signals are connected.
                self.on_category_changed()
        except Exception as e:
            print(f"Error initializing expense dialog: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to initialize dialog: {str(e)}")
    
    def add_inventory_item(self):
        """Show dialog to add an inventory item connection"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Connected Item")
        dialog.setMinimumWidth(400)
        
        layout = QFormLayout(dialog)
        
        # Item selection
        item_combo = QComboBox()
        inventory_items = self.db.get_inventory_items()
        for item in inventory_items:
            # Skip already selected items
            if not any(selected['id'] == item['id'] for selected in self.selected_inventory_items):
                item_combo.addItem(f"{item['title']} (${item['purchase_cost']:.2f})", item)
        layout.addRow("Select Item:", item_combo)
        
        # Amount allocation (optional)
        amount_input = QDoubleSpinBox()
        amount_input.setPrefix("$")
        amount_input.setMaximum(99999.99)
        amount_input.setDecimals(2)
        layout.addRow("Allocated Amount (optional):", amount_input)
        
        # Buttons
        button_box = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(dialog.accept)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 6px 12px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_box.addWidget(add_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                font-size: 14px;
                min-width: 80px;
            }
        """)
        button_box.addWidget(cancel_btn)
        
        layout.addRow(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted and item_combo.currentData():
            item = item_combo.currentData()
            item = dict(item)  # Convert from sqlite3.Row to dict
            item['allocated_amount'] = amount_input.value() if amount_input.value() > 0 else None
            self.selected_inventory_items.append(item)
            self.update_inventory_items_display()
    
    def update_inventory_items_display(self):
        """Update the display of selected inventory items"""
        # Clear existing items
        for i in reversed(range(self.inventory_items_layout.count())): 
            self.inventory_items_layout.itemAt(i).widget().setParent(None)
        
        # Add each selected item
        for item in self.selected_inventory_items:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            
            amount_text = f" (${item['allocated_amount']:.2f})" if item.get('allocated_amount') else ""
            label = QLabel(f"{item['title']}{amount_text}")
            item_layout.addWidget(label)
            
            remove_btn = QPushButton("❌")
            remove_btn.setMaximumWidth(30)
            remove_btn.clicked.connect(lambda checked, i=item: self.remove_inventory_item(i))
            item_layout.addWidget(remove_btn)
            
            self.inventory_items_layout.addWidget(item_widget)
    
    def remove_inventory_item(self, item):
        """Remove an inventory item from the selection"""
        self.selected_inventory_items = [i for i in self.selected_inventory_items if i['id'] != item['id']]
        self.update_inventory_items_display()

    def on_category_changed(self):
        """
        Update the tax-deductible checkbox based on the selected category.

        If the user is editing an existing expense, the checkbox will still
        update when the category changes.  However, the initial setting is
        applied only when creating a new expense (self.is_editing is False).
        """
        try:
            category = self.category_combo.currentText()
            default = self.CATEGORY_TAX_DEDUCTIBLE_MAP.get(category, True)
            # Only update the checkbox if it differs from the current state
            # to avoid unnecessary signal emissions.
            self.deductible_check.setChecked(bool(default))
        except Exception:
            # Gracefully ignore errors (e.g., if combo box is not yet fully
            # initialized)
            pass
    
    def load_expense_data(self):
        """Load existing expense data into form"""
        expense = self.db.get_expense(self.expense_id)
        if not expense:
            return
        
        # Convert to dict if it's a Row object
        if not isinstance(expense, dict):
            expense = dict(expense)
        
        date = QDate.fromString(expense.get('date', ''), "yyyy-MM-dd")
        self.date_input.setDate(date)
        
        self.amount_input.setValue(expense.get('amount', 0))
        
        if expense.get('category'):
            index = self.category_combo.findText(expense['category'])
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
        
        self.vendor_input.setText(expense.get('vendor') or '')
        
        if expense.get('payment_method'):
            index = self.payment_combo.findText(expense['payment_method'])
            if index >= 0:
                self.payment_combo.setCurrentIndex(index)
        
        self.deductible_check.setChecked(bool(expense.get('tax_deductible')))
        self.description_input.setPlainText(expense.get('description') or '')
        self.notes_input.setPlainText(expense.get('notes') or '')
        
        # Load previously connected inventory items
        try:
            self.selected_inventory_items = self.db.get_inventory_items_for_expense(self.expense_id)
            self.update_inventory_items_display()
        except Exception:
            self.selected_inventory_items = []
        
        if expense.get('receipt_path'):
            self.receipt_path = expense['receipt_path']
            self.receipt_label.setText(f"Receipt: {expense['receipt_path'].split('/')[-1]}")
    
    def attach_receipt(self):
        """Attach a receipt file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Receipt",
            "",
            "Images (*.png *.jpg *.jpeg *.pdf);;All Files (*)"
        )
        
        if file_path:
            self.receipt_path = file_path
            self.receipt_label.setText(f"Receipt: {file_path.split('/')[-1]}")
    
    def save_expense(self):
        """Save the expense to database"""
        try:
            # Validate
            if self.amount_input.value() == 0:
                QMessageBox.warning(self, "Required Field", "Please enter an amount.")
                return
            
            # Prepare data - remove inventory_items as it's not in database schema
            expense_data = {
                'date': self.date_input.date().toString("yyyy-MM-dd"),
                'amount': self.amount_input.value(),
                'category': self.category_combo.currentText(),
                'vendor': self.vendor_input.text().strip() or None,
                'payment_method': self.payment_combo.currentText(),
                'tax_deductible': 1 if self.deductible_check.isChecked() else 0,
                'description': self.description_input.toPlainText().strip() or None,
                'notes': self.notes_input.toPlainText().strip() or None,
                'receipt_path': self.receipt_path
            }
            
            # Persist the expense and retrieve its ID
            if self.expense_id:
                # Update existing expense
                self.db.update_expense(self.expense_id, expense_data)
                expense_id = self.expense_id
                success_message = "Expense updated successfully!"
            else:
                # Create new expense
                expense_id = self.db.add_expense(expense_data)
                success_message = "Expense added successfully!"

            # Manage linked inventory items
            # Remove existing links when editing
            self.db.clear_expense_inventory_links(expense_id)
            for item in self.selected_inventory_items:
                try:
                    allocated = item.get('allocated_amount') if isinstance(item, dict) else None
                    # Link in junction table
                    self.db.add_expense_inventory_link(expense_id, item['id'], allocated)
                    # Also update the inventory record's expense_id for quick reference
                    try:
                        self.db.update_inventory_item(item['id'], {'expense_id': expense_id})
                    except Exception:
                        pass
                except Exception:
                    # Continue linking other items if one fails
                    continue

            QMessageBox.information(self, "Success", success_message)
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save expense:\n{str(e)}")
            print(f"Error saving expense: {e}")
            import traceback
            traceback.print_exc()
