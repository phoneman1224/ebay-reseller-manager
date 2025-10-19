"""
Settings Dialog - Customize what you see in each tab
Allows users to show/hide columns and cards
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QGroupBox, QCheckBox, QScrollArea,
                             QWidget, QTabWidget, QMessageBox, QFormLayout,
                             QLineEdit, QSpinBox, QComboBox, QDialogButtonBox)
from PyQt6.QtCore import Qt
import json


class SettingsDialog(QDialog):
    """Settings dialog for customizing the application"""
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("⚙️ Application Settings")
        self.setModal(True)
        self.resize(700, 600)
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the settings dialog UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("⚙️ Customize Your Application")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Tab widget for different setting categories
        self.tabs = QTabWidget()
        
        # Dashboard Settings Tab
        self.dashboard_widget = self.create_dashboard_settings()
        self.tabs.addTab(self.dashboard_widget, "📊 Dashboard")
        
        # Inventory Settings Tab
        self.inventory_widget = self.create_inventory_settings()
        self.tabs.addTab(self.inventory_widget, "📦 Inventory")
        
        # Expenses Settings Tab
        self.expenses_widget = self.create_expenses_settings()
        self.tabs.addTab(self.expenses_widget, "💵 Expenses")
        
        # Sold Items Settings Tab
        self.sold_widget = self.create_sold_settings()
        self.tabs.addTab(self.sold_widget, "💰 Sold Items")
        
        # General Settings Tab
        self.general_widget = self.create_general_settings()
        self.tabs.addTab(self.general_widget, "🔧 General")
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("🔄 Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def create_dashboard_settings(self):
        """Create dashboard customization settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("Choose which cards to display on the Dashboard:")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Dashboard cards
        self.dashboard_checks = {}
        cards = [
            ("inventory", "📦 Inventory Card", "Shows total items and inventory value"),
            ("revenue", "💰 Revenue Card", "Shows year-to-date revenue and sales count"),
            ("expenses", "💵 Expenses Card", "Shows total expenses and tax deductions"),
            ("profit", "📈 Net Profit Card", "Shows profit and profit margin"),
            ("tax", "🧾 Tax Liability Card", "Shows estimated tax liability"),
            ("stats", "📊 Quick Stats Card", "Shows listing statistics and averages"),
        ]
        
        for key, title, desc in cards:
            group = QGroupBox(title)
            group_layout = QVBoxLayout()
            
            checkbox = QCheckBox("Show this card")
            checkbox.setChecked(True)
            self.dashboard_checks[key] = checkbox
            group_layout.addWidget(checkbox)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #666; font-size: 11px;")
            desc_label.setWordWrap(True)
            group_layout.addWidget(desc_label)
            
            group.setLayout(group_layout)
            scroll_layout.addWidget(group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def create_inventory_settings(self):
        """Create inventory tab customization settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("Choose which columns to display in the Inventory table:")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Column checkboxes
        self.inventory_checks = {}
        columns = [
            ("id", "ID", "Item ID number", False),  # Usually hidden
            ("title", "Title", "Item title/description", True),  # Required
            ("category", "Category", "Product category", True),
            ("sku", "SKU", "Stock keeping unit", True),
            ("brand", "Brand/Model", "Brand or model name", True),
            ("condition", "Condition", "Item condition", True),
            ("purchase_cost", "Purchase Cost", "What you paid for it", True),
            ("listed_price", "Listed Price", "Current listing price", True),
            ("status", "Status", "In Stock/Listed/Sold", True),  # Required
            ("storage", "Storage Location", "Where item is stored", True),
            ("item_number", "eBay Item #", "eBay item number", False),
            ("quantity", "Quantity", "Number of items", False),
            ("notes", "Notes", "Additional notes", True),
        ]
        
        for key, title, desc, default in columns:
            checkbox = QCheckBox(f"{title} - {desc}")
            checkbox.setChecked(default)
            if key in ["title", "status"]:
                checkbox.setEnabled(False)  # Required columns
                checkbox.setToolTip("This column is required and cannot be hidden")
            self.inventory_checks[key] = checkbox
            scroll_layout.addWidget(checkbox)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def create_expenses_settings(self):
        """Create expenses tab customization settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("Choose which columns to display in the Expenses table:")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Column checkboxes
        self.expenses_checks = {}
        columns = [
            ("id", "ID", "Expense ID number", False),
            ("date", "Date", "Expense date", True),  # Required
            ("amount", "Amount", "Expense amount", True),  # Required
            ("category", "Category", "Expense category", True),
            ("note", "Note/Description", "Expense details", True),
            ("tax_deductible", "Tax Deductible", "Deductible checkbox", True),
        ]
        
        for key, title, desc, default in columns:
            checkbox = QCheckBox(f"{title} - {desc}")
            checkbox.setChecked(default)
            if key in ["date", "amount"]:
                checkbox.setEnabled(False)  # Required columns
                checkbox.setToolTip("This column is required and cannot be hidden")
            self.expenses_checks[key] = checkbox
            scroll_layout.addWidget(checkbox)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def create_sold_settings(self):
        """Create sold items tab customization settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("Choose which columns to display in the Sold Items table:")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Column checkboxes
        self.sold_checks = {}
        columns = [
            ("id", "ID", "Item ID number", False),
            ("title", "Title", "Item title", True),  # Required
            ("sku", "SKU", "Stock keeping unit", True),
            ("sold_price", "Sold Price", "Sale price", True),  # Required
            ("purchase_cost", "Purchase Cost", "Original cost", True),
            ("profit", "Profit", "Calculated profit", True),
            ("sold_date", "Sold Date", "Date of sale", True),
            ("quantity", "Quantity", "Number sold", True),
            ("order_number", "Order Number", "eBay order number", True),
            ("item_number", "eBay Item #", "eBay item number", False),
        ]
        
        for key, title, desc, default in columns:
            checkbox = QCheckBox(f"{title} - {desc}")
            checkbox.setChecked(default)
            if key in ["title", "sold_price"]:
                checkbox.setEnabled(False)  # Required columns
                checkbox.setToolTip("This column is required and cannot be hidden")
            self.sold_checks[key] = checkbox
            scroll_layout.addWidget(checkbox)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def create_general_settings(self):
        """Create general application settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Category ID
        category_group = QGroupBox("Default eBay Category")
        category_layout = QFormLayout()
        
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("47140")
        category_layout.addRow("Category ID:", self.category_input)
        
        cat_info = QLabel("Default category for draft listings. Find IDs at: ebay.com/sellercenter")
        cat_info.setStyleSheet("color: #666; font-size: 11px;")
        cat_info.setWordWrap(True)
        category_layout.addRow("", cat_info)
        
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)
        
        # Tax Settings
        tax_group = QGroupBox("Tax Settings")
        tax_layout = QFormLayout()
        
        self.income_tax_rate = QSpinBox()
        self.income_tax_rate.setSuffix("%")
        self.income_tax_rate.setMaximum(50)
        self.income_tax_rate.setValue(22)
        tax_layout.addRow("Income Tax Rate:", self.income_tax_rate)
        
        self.se_tax_rate = QSpinBox()
        self.se_tax_rate.setSuffix("%")
        self.se_tax_rate.setMaximum(20)
        self.se_tax_rate.setValue(15)
        self.se_tax_rate.setEnabled(False)
        tax_layout.addRow("Self-Employment Tax:", self.se_tax_rate)
        
        tax_info = QLabel("These rates are used for tax liability estimates on the dashboard.")
        tax_info.setStyleSheet("color: #666; font-size: 11px;")
        tax_info.setWordWrap(True)
        tax_layout.addRow("", tax_info)
        
        tax_group.setLayout(tax_layout)
        layout.addWidget(tax_group)
        
        # Display Settings
        display_group = QGroupBox("Display Settings")
        display_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark (Coming Soon)"])
        self.theme_combo.setEnabled(False)
        display_layout.addRow("Theme:", self.theme_combo)
        
        self.compact_mode = QCheckBox("Use compact mode (smaller text/spacing)")
        display_layout.addRow("", self.compact_mode)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        layout.addStretch()
        
        return widget
    
    def load_settings(self):
        """Load settings from database"""
        try:
            # Get all settings
            settings = self.db.get_import_settings()
            
            # Dashboard cards
            dashboard_settings = settings.get("dashboard_cards", {})
            for key, checkbox in self.dashboard_checks.items():
                checkbox.setChecked(dashboard_settings.get(key, True))
            
            # Inventory columns
            inventory_settings = settings.get("inventory_columns", {})
            for key, checkbox in self.inventory_checks.items():
                if checkbox.isEnabled():  # Only load if not disabled (required columns)
                    checkbox.setChecked(inventory_settings.get(key, True))
            
            # Expenses columns
            expenses_settings = settings.get("expenses_columns", {})
            for key, checkbox in self.expenses_checks.items():
                if checkbox.isEnabled():
                    checkbox.setChecked(expenses_settings.get(key, True))
            
            # Sold items columns
            sold_settings = settings.get("sold_columns", {})
            for key, checkbox in self.sold_checks.items():
                if checkbox.isEnabled():
                    checkbox.setChecked(sold_settings.get(key, True))
            
            # General settings
            self.category_input.setText(str(settings.get("default_category_id", "47140")))
            self.income_tax_rate.setValue(int(settings.get("income_tax_rate", 22)))
            self.compact_mode.setChecked(settings.get("compact_mode", False))
            
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save_settings(self):
        """Save settings to database"""
        try:
            # Get current settings
            settings = self.db.get_import_settings()
            
            # Dashboard cards
            dashboard_cards = {}
            for key, checkbox in self.dashboard_checks.items():
                dashboard_cards[key] = checkbox.isChecked()
            settings["dashboard_cards"] = dashboard_cards
            
            # Inventory columns
            inventory_columns = {}
            for key, checkbox in self.inventory_checks.items():
                inventory_columns[key] = checkbox.isChecked()
            settings["inventory_columns"] = inventory_columns
            
            # Expenses columns
            expenses_columns = {}
            for key, checkbox in self.expenses_checks.items():
                expenses_columns[key] = checkbox.isChecked()
            settings["expenses_columns"] = expenses_columns
            
            # Sold items columns
            sold_columns = {}
            for key, checkbox in self.sold_checks.items():
                sold_columns[key] = checkbox.isChecked()
            settings["sold_columns"] = sold_columns
            
            # General settings
            settings["default_category_id"] = self.category_input.text().strip() or "47140"
            settings["income_tax_rate"] = self.income_tax_rate.value()
            settings["compact_mode"] = self.compact_mode.isChecked()
            
            # Save to database
            self.db.update_import_settings(settings)
            
            QMessageBox.information(
                self,
                "Settings Saved",
                "Your settings have been saved successfully!\n\n"
                "Some changes may require refreshing the tabs or restarting the application."
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{str(e)}")
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Reset dashboard
                for checkbox in self.dashboard_checks.values():
                    checkbox.setChecked(True)
                
                # Reset inventory (defaults from create_inventory_settings)
                defaults = {
                    "id": False, "title": True, "category": True, "sku": True,
                    "brand": True, "condition": True, "purchase_cost": True,
                    "listed_price": True, "status": True, "storage": True,
                    "item_number": False, "quantity": False, "notes": True
                }
                for key, checkbox in self.inventory_checks.items():
                    if checkbox.isEnabled():
                        checkbox.setChecked(defaults.get(key, True))
                
                # Reset expenses
                defaults = {"id": False, "date": True, "amount": True, 
                           "category": True, "note": True, "tax_deductible": True}
                for key, checkbox in self.expenses_checks.items():
                    if checkbox.isEnabled():
                        checkbox.setChecked(defaults.get(key, True))
                
                # Reset sold
                defaults = {
                    "id": False, "title": True, "sku": True, "sold_price": True,
                    "purchase_cost": True, "profit": True, "sold_date": True,
                    "quantity": True, "order_number": True, "item_number": False
                }
                for key, checkbox in self.sold_checks.items():
                    if checkbox.isEnabled():
                        checkbox.setChecked(defaults.get(key, True))
                
                # Reset general
                self.category_input.setText("47140")
                self.income_tax_rate.setValue(22)
                self.compact_mode.setChecked(False)
                
                QMessageBox.information(self, "Reset Complete", "All settings have been reset to defaults.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset settings:\n{str(e)}")
