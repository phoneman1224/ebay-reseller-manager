"""
Dialog for adding/editing expenses with inventory item linking
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                           QComboBox, QDateEdit, QTextEdit, QPushButton,
                           QCheckBox, QHBoxLayout, QMessageBox, QLabel)
from PyQt6.QtCore import Qt, QDate

from .value_helpers import resolve_cost, format_currency

class ExpenseDialog(QDialog):
    def __init__(self, parent=None, db=None, expense_data=None):
        super().__init__(parent)
        self.db = db
        self.expense_data = expense_data
        self.init_ui()
        
    def init_ui(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("Add/Edit Expense")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Create form
        form = QFormLayout()
        
        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Date:", self.date_edit)
        
        # Amount
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("Enter amount")
        form.addRow("Amount ($):", self.amount_edit)
        
        # Vendor
        self.vendor_edit = QLineEdit()
        self.vendor_edit.setPlaceholderText("Enter vendor name")
        form.addRow("Vendor:", self.vendor_edit)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Inventory Purchase",
            "Shipping Supplies",
            "Storage",
            "Tools & Equipment",
            "Transportation",
            "Marketing",
            "Software & Services",
            "Other"
        ])
        form.addRow("Category:", self.category_combo)
        
        # Link to Inventory Item
        self.inventory_combo = QComboBox()
        self.inventory_combo.addItem("None", None)  # Default option
        self.load_inventory_items()
        form.addRow("Link to Item:", self.inventory_combo)
        
        # Description
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Enter description")
        self.desc_edit.setMaximumHeight(100)
        form.addRow("Description:", self.desc_edit)
        
        # Payment Method
        self.payment_combo = QComboBox()
        self.payment_combo.addItems([
            "Cash",
            "Credit Card",
            "Debit Card",
            "PayPal",
            "Other"
        ])
        form.addRow("Payment Method:", self.payment_combo)
        
        # Tax Deductible
        self.tax_check = QCheckBox("Tax Deductible")
        self.tax_check.setChecked(True)
        form.addRow("", self.tax_check)
        
        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Enter any additional notes")
        self.notes_edit.setMaximumHeight(100)
        form.addRow("Notes:", self.notes_edit)
        
        layout.addLayout(form)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_expense)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Fill in existing data if editing
        if self.expense_data:
            self.fill_expense_data()
    
    def load_inventory_items(self):
        """Load inventory items into combo box"""
        try:
            items = self.db.get_inventory_items(status="In Stock")
            for item in items:
                title = item.get('title') or 'Untitled'
                cost_text = format_currency(resolve_cost(item))
                display_text = f"{title} ({cost_text})"
                self.inventory_combo.addItem(display_text, item['id'])
        except Exception as e:
            print(f"Error loading inventory items: {e}")
    
    def fill_expense_data(self):
        """Fill in existing expense data when editing"""
        try:
            date = QDate.fromString(self.expense_data['date'], "yyyy-MM-dd")
            self.date_edit.setDate(date)
            self.amount_edit.setText(str(self.expense_data['amount']))
            self.vendor_edit.setText(self.expense_data.get('vendor', ''))
            
            category_index = self.category_combo.findText(self.expense_data['category'])
            if category_index >= 0:
                self.category_combo.setCurrentIndex(category_index)
            
            if self.expense_data.get('inventory_id'):
                inventory_index = self.inventory_combo.findData(self.expense_data['inventory_id'])
                if inventory_index >= 0:
                    self.inventory_combo.setCurrentIndex(inventory_index)
            
            self.desc_edit.setText(self.expense_data.get('description', ''))
            
            payment_index = self.payment_combo.findText(self.expense_data.get('payment_method', ''))
            if payment_index >= 0:
                self.payment_combo.setCurrentIndex(payment_index)
            
            self.tax_check.setChecked(bool(self.expense_data.get('tax_deductible', True)))
            self.notes_edit.setText(self.expense_data.get('notes', ''))
        except Exception as e:
            print(f"Error filling expense data: {e}")
    
    def save_expense(self):
        """Save the expense"""
        try:
            # Validate amount
            try:
                amount = float(self.amount_edit.text())
                if amount <= 0:
                    raise ValueError("Amount must be greater than 0")
            except ValueError:
                QMessageBox.warning(self, "Invalid Amount", "Please enter a valid amount greater than 0.")
                return
            
            # Build expense data
            expense_data = {
                'date': self.date_edit.date().toString("yyyy-MM-dd"),
                'amount': amount,
                'vendor': self.vendor_edit.text(),
                'category': self.category_combo.currentText(),
                'description': self.desc_edit.toPlainText(),
                'payment_method': self.payment_combo.currentText(),
                'tax_deductible': int(self.tax_check.isChecked()),
                'notes': self.notes_edit.toPlainText()
            }
            
            # Get linked inventory item
            inventory_id = self.inventory_combo.currentData()
            if inventory_id:
                expense_data['inventory_id'] = inventory_id
            
            if self.expense_data:  # Editing existing expense
                self.db.update_expense(self.expense_data['id'], expense_data)
            else:  # New expense
                expense_id = self.db.add_expense(expense_data)
                
                # Update inventory item if linked
                if inventory_id:
                    self.db.update_inventory_item(inventory_id, {'expense_id': expense_id})
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save expense: {str(e)}")