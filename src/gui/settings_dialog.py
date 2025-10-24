"""
Settings Dialog - Customize what you see in each tab
Allows users to show/hide columns and cards
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QGroupBox, QCheckBox, QScrollArea,
                             QWidget, QTabWidget, QMessageBox, QFormLayout,
                             QLineEdit, QSpinBox, QComboBox, QDialogButtonBox,
                             QDoubleSpinBox)
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
        self.category_rows = []
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

        # eBay categories
        category_group = QGroupBox("eBay Listing Categories")
        category_layout = QVBoxLayout()

        default_form = QFormLayout()
        self.default_category_combo = QComboBox()
        self.default_category_combo.setEditable(True)
        self.default_category_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        line_edit = self.default_category_combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText("47140")
            line_edit.setReadOnly(False)
        default_form.addRow("Default Category:", self.default_category_combo)
        category_layout.addLayout(default_form)

        cat_info = QLabel(
            "Manage reusable eBay categories with friendly names. "
            "The selected default is applied when creating drafts."
        )
        cat_info.setStyleSheet("color: #666; font-size: 11px;")
        cat_info.setWordWrap(True)
        category_layout.addWidget(cat_info)

        self.category_rows_layout = QVBoxLayout()
        category_layout.addLayout(self.category_rows_layout)

        # Seed the editor with a blank row so users can immediately type a
        # category even before saved settings have been loaded.
        self.add_category_row(update=False)

        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        add_category_btn = QPushButton("➕ Add Category")
        add_category_btn.clicked.connect(lambda: self.add_category_row())
        controls_layout.addWidget(add_category_btn)
        category_layout.addLayout(controls_layout)

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

        self.se_tax_rate = QDoubleSpinBox()
        self.se_tax_rate.setSuffix("%")
        self.se_tax_rate.setDecimals(2)
        self.se_tax_rate.setMaximum(30.0)
        self.se_tax_rate.setValue(15.30)
        tax_layout.addRow("Self-Employment Tax:", self.se_tax_rate)
        
        tax_info = QLabel("These rates are used for tax liability estimates on the dashboard.")
        tax_info.setStyleSheet("color: #666; font-size: 11px;")
        tax_info.setWordWrap(True)
        tax_layout.addRow("", tax_info)
        
        tax_group.setLayout(tax_layout)
        layout.addWidget(tax_group)

        # Fee Settings
        fees_group = QGroupBox("Fee Settings")
        fees_layout = QFormLayout()

        self.ebay_fee_percent = QDoubleSpinBox()
        self.ebay_fee_percent.setSuffix("%")
        self.ebay_fee_percent.setDecimals(2)
        self.ebay_fee_percent.setMaximum(30.0)
        self.ebay_fee_percent.setValue(12.90)
        fees_layout.addRow("eBay Final Value Fee:", self.ebay_fee_percent)

        self.ebay_fee_fixed = QDoubleSpinBox()
        self.ebay_fee_fixed.setPrefix("$")
        self.ebay_fee_fixed.setDecimals(2)
        self.ebay_fee_fixed.setMaximum(10.0)
        self.ebay_fee_fixed.setValue(0.30)
        fees_layout.addRow("eBay Fixed Fee:", self.ebay_fee_fixed)

        self.payment_fee_percent = QDoubleSpinBox()
        self.payment_fee_percent.setSuffix("%")
        self.payment_fee_percent.setDecimals(2)
        self.payment_fee_percent.setMaximum(15.0)
        self.payment_fee_percent.setValue(2.90)
        fees_layout.addRow("Payment Processing Fee:", self.payment_fee_percent)

        self.payment_fee_fixed = QDoubleSpinBox()
        self.payment_fee_fixed.setPrefix("$")
        self.payment_fee_fixed.setDecimals(2)
        self.payment_fee_fixed.setMaximum(10.0)
        self.payment_fee_fixed.setValue(0.30)
        fees_layout.addRow("Payment Fixed Fee:", self.payment_fee_fixed)

        fees_info = QLabel(
            "These fee rates are used by the pricing calculator when estimating profits."
        )
        fees_info.setStyleSheet("color: #666; font-size: 11px;")
        fees_info.setWordWrap(True)
        fees_layout.addRow("", fees_info)

        fees_group.setLayout(fees_layout)
        layout.addWidget(fees_group)
        
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

    def clear_category_rows(self):
        """Remove all configured category rows."""
        while self.category_rows:
            row = self.category_rows.pop()
            widget = row.get("widget")
            if widget:
                self.category_rows_layout.removeWidget(widget)
                widget.deleteLater()
        self.update_default_category_options()

    def add_category_row(self, name: str = "", number: str = "", *, update: bool = True):
        """Append a configurable eBay category entry."""

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Category name")
        name_edit.setText(name or "")

        number_edit = QLineEdit()
        number_edit.setPlaceholderText("Category number")
        number_edit.setText(number or "")

        remove_btn = QPushButton("🗑")
        remove_btn.setToolTip("Remove category")
        remove_btn.setMaximumWidth(32)

        def _remove_row():
            self.category_rows_layout.removeWidget(row_widget)
            row_widget.deleteLater()
            self.category_rows = [r for r in self.category_rows if r.get("widget") is not row_widget]
            self.update_default_category_options()

        remove_btn.clicked.connect(_remove_row)

        name_edit.textChanged.connect(lambda *_: self.update_default_category_options())
        number_edit.textChanged.connect(lambda *_: self.update_default_category_options())

        row_layout.addWidget(name_edit)
        row_layout.addWidget(number_edit)
        row_layout.addWidget(remove_btn)

        self.category_rows_layout.addWidget(row_widget)
        self.category_rows.append({
            "widget": row_widget,
            "name": name_edit,
            "number": number_edit,
        })

        if update:
            self.update_default_category_options()

    def update_default_category_options(self, selected_id: str = None):
        """Refresh the default category dropdown based on configured rows."""

        if not hasattr(self, "default_category_combo"):
            return

        if selected_id is None:
            selected_id = (self.default_category_combo.currentData() or "").strip()
            if not selected_id:
                selected_id = self.default_category_combo.currentText().strip()
        else:
            selected_id = str(selected_id).strip()

        entries = []
        seen = set()
        for row in self.category_rows:
            name = (row.get("name").text() or "").strip()
            number = (row.get("number").text() or "").strip()
            if not name and not number:
                continue
            value = number or name
            if value in seen:
                continue
            seen.add(value)
            if name and number:
                label = f"{name} ({number})"
            else:
                label = name or number
            entries.append((label, value))

        self.default_category_combo.blockSignals(True)
        self.default_category_combo.clear()
        self.default_category_combo.addItem("(None)", "")
        for label, value in entries:
            self.default_category_combo.addItem(label, value)

        if selected_id:
            index = self.default_category_combo.findData(selected_id)
            if index < 0:
                index = self.default_category_combo.findText(selected_id)
            if index >= 0:
                self.default_category_combo.setCurrentIndex(index)
            else:
                self.default_category_combo.setEditText(selected_id)
        else:
            self.default_category_combo.setCurrentIndex(0)
            self.default_category_combo.setEditText("")

        self.default_category_combo.blockSignals(False)
    
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
            categories, default_category = self.db.get_configured_categories(settings)
            self.clear_category_rows()
            if categories:
                for entry in categories:
                    self.add_category_row(
                        entry.get("name") or "",
                        entry.get("number") or "",
                        update=False,
                    )
            else:
                self.add_category_row(update=False)

            self.update_default_category_options(default_category)

            income_rate = settings.get("income_tax_rate")
            if income_rate is None:
                stored_income = self.db.get_setting("income_tax_rate")
                if stored_income not in (None, ""):
                    try:
                        income_rate = float(stored_income) * 100
                    except (TypeError, ValueError):
                        income_rate = None
            try:
                self.income_tax_rate.setValue(int(round(float(income_rate))))
            except (TypeError, ValueError):
                self.income_tax_rate.setValue(22)

            se_tax_rate = settings.get("self_employment_tax_rate")
            if se_tax_rate is None:
                stored_se = self.db.get_setting("self_employment_tax_rate")
                if stored_se not in (None, ""):
                    try:
                        se_tax_rate = float(stored_se) * 100
                    except (TypeError, ValueError):
                        se_tax_rate = None
            try:
                self.se_tax_rate.setValue(float(se_tax_rate))
            except (TypeError, ValueError):
                self.se_tax_rate.setValue(15.30)

            def _load_fee_value(key, default, *, is_percent=False):
                value = settings.get(key)
                if value is None:
                    stored = self.db.get_setting(key)
                    if stored not in (None, ""):
                        try:
                            value = float(stored) * (100 if is_percent else 1)
                        except (TypeError, ValueError):
                            value = None
                return value if value is not None else default

            self.ebay_fee_percent.setValue(
                float(_load_fee_value("ebay_fee_percent", 12.90, is_percent=True))
            )
            self.ebay_fee_fixed.setValue(float(_load_fee_value("ebay_fee_fixed", 0.30)))
            self.payment_fee_percent.setValue(
                float(_load_fee_value("payment_fee_percent", 2.90, is_percent=True))
            )
            self.payment_fee_fixed.setValue(float(_load_fee_value("payment_fee_fixed", 0.30)))

            self.compact_mode.setChecked(settings.get("compact_mode", False))

            if hasattr(self, "general_widget"):
                self.general_widget.setEnabled(True)

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
            categories_payload = []
            for row in self.category_rows:
                name = (row.get("name").text() or "").strip()
                number = (row.get("number").text() or "").strip()
                if not name and not number:
                    continue
                categories_payload.append({
                    "name": name or None,
                    "number": number or None,
                })
            settings["ebay_categories"] = categories_payload

            default_category_value = (self.default_category_combo.currentData() or "").strip()
            if not default_category_value:
                default_category_value = self.default_category_combo.currentText().strip()
            settings["default_category_id"] = default_category_value or "47140"
            settings["income_tax_rate"] = self.income_tax_rate.value()
            settings["self_employment_tax_rate"] = self.se_tax_rate.value()
            settings["ebay_fee_percent"] = self.ebay_fee_percent.value()
            settings["ebay_fee_fixed"] = self.ebay_fee_fixed.value()
            settings["payment_fee_percent"] = self.payment_fee_percent.value()
            settings["payment_fee_fixed"] = self.payment_fee_fixed.value()
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
                self.clear_category_rows()
                self.add_category_row(update=False)
                self.update_default_category_options("47140")
                self.default_category_combo.setEditText("47140")
                self.income_tax_rate.setValue(22)
                self.se_tax_rate.setValue(15.30)
                self.ebay_fee_percent.setValue(12.90)
                self.ebay_fee_fixed.setValue(0.30)
                self.payment_fee_percent.setValue(2.90)
                self.payment_fee_fixed.setValue(0.30)
                self.compact_mode.setChecked(False)
                
                QMessageBox.information(self, "Reset Complete", "All settings have been reset to defaults.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset settings:\n{str(e)}")
