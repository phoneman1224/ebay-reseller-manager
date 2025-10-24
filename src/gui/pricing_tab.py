"""
Pricing Tab - Calculate optimal prices and compare shipping strategies
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QDoubleSpinBox, QGroupBox,
                             QFormLayout, QTextEdit, QMessageBox, QSpinBox,
                             QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt
import math


class PricingTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        """Initialize the pricing tab UI"""
        layout = QVBoxLayout(self)
        
        # Header
        title = QLabel("🏷️ Smart Pricing Calculator")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(title)
        
        # Main content in horizontal layout
        main_layout = QHBoxLayout()
        
        # Left side - Input form
        input_group = QGroupBox("Item & Cost Details")
        input_layout = QFormLayout()
        
        # Select inventory item
        self.item_combo = QComboBox()
        self.item_combo.addItem("-- Select from Inventory --", None)
        self.load_inventory_items()
        self.item_combo.currentIndexChanged.connect(self.on_item_selected)
        input_layout.addRow("Inventory Item:", self.item_combo)
        
        # Cost basis
        self.cost_input = QDoubleSpinBox()
        self.cost_input.setPrefix("$")
        self.cost_input.setMaximum(99999.99)
        self.cost_input.setDecimals(2)
        self.cost_input.valueChanged.connect(self.calculate_prices)
        input_layout.addRow("Cost Basis:", self.cost_input)
        
        # Target profit
        profit_layout = QHBoxLayout()
        
        self.profit_type_group = QButtonGroup()
        self.profit_dollar_radio = QRadioButton("Dollar Amount")
        self.profit_percent_radio = QRadioButton("Percent Margin")
        self.profit_dollar_radio.setChecked(True)
        self.profit_type_group.addButton(self.profit_dollar_radio)
        self.profit_type_group.addButton(self.profit_percent_radio)
        
        profit_layout.addWidget(self.profit_dollar_radio)
        profit_layout.addWidget(self.profit_percent_radio)
        
        input_layout.addRow("Profit Type:", profit_layout)
        
        self.profit_input = QDoubleSpinBox()
        self.profit_input.setPrefix("$")
        self.profit_input.setMaximum(99999.99)
        self.profit_input.setDecimals(2)
        self.profit_input.setValue(10.00)
        self.profit_input.valueChanged.connect(self.calculate_prices)
        self.profit_dollar_radio.toggled.connect(self.on_profit_type_changed)
        input_layout.addRow("Target Profit:", self.profit_input)
        
        # Shipping details
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setSuffix(" lbs")
        self.weight_input.setMaximum(999.99)
        self.weight_input.setDecimals(2)
        self.weight_input.setValue(1.0)
        self.weight_input.valueChanged.connect(self.calculate_prices)
        input_layout.addRow("Weight:", self.weight_input)
        
        # Dimensions
        dim_layout = QHBoxLayout()
        self.length_input = QSpinBox()
        self.length_input.setSuffix('"')
        self.length_input.setMaximum(999)
        self.length_input.setValue(12)
        dim_layout.addWidget(QLabel("L:"))
        dim_layout.addWidget(self.length_input)
        
        self.width_input = QSpinBox()
        self.width_input.setSuffix('"')
        self.width_input.setMaximum(999)
        self.width_input.setValue(8)
        dim_layout.addWidget(QLabel("W:"))
        dim_layout.addWidget(self.width_input)
        
        self.height_input = QSpinBox()
        self.height_input.setSuffix('"')
        self.height_input.setMaximum(999)
        self.height_input.setValue(4)
        dim_layout.addWidget(QLabel("H:"))
        dim_layout.addWidget(self.height_input)
        
        input_layout.addRow("Dimensions:", dim_layout)
        
        # eBay category (affects fees)
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Most Categories (12.9%)",
            "Books/Movies/Music (12.9%)",
            "Collectibles (12.9%)",
            "Electronics (12.9%)",
            "Clothing (12.9%)",
            "Jewelry (12.9%)",
        ])
        self.category_combo.currentIndexChanged.connect(self.calculate_prices)
        input_layout.addRow("eBay Category:", self.category_combo)
        
        # We intentionally omit the manual "Calculate Prices" button here.
        # The pricing calculations update dynamically whenever the
        # cost, profit, weight or category inputs change.  Removing
        # the button declutters the interface and reflects the fact
        # that no manual trigger is required.
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group, 1)
        
        # Right side - Results
        results_group = QGroupBox("Pricing Comparison")
        results_layout = QVBoxLayout()
        
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setMinimumHeight(400)
        results_layout.addWidget(self.results_display)
        
        # Recommendation label
        self.recommendation_label = QLabel()
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setStyleSheet("""
            background-color: #E8F5E9;
            padding: 10px;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
        """)
        results_layout.addWidget(self.recommendation_label)
        
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group, 1)
        
        layout.addLayout(main_layout)
        
        # Initial calculation
        self.calculate_prices()
    
    def load_inventory_items(self):
        """Load inventory items into dropdown"""
        self.item_combo.clear()  # Clear existing items first!
        self.item_combo.addItem("Select an item...", None)  # Add placeholder
        items = self.db.get_inventory_items(status='In Stock')
        for item in items:
            # Convert Row to dict and get cost
            if not isinstance(item, dict):
                item = dict(item)
            cost = item.get('cost') or item.get('purchase_price') or 0
            title = item.get('title', 'Untitled')[:40]
            display_text = f"{title} (${cost:.2f})"
            self.item_combo.addItem(display_text, item)
    
    def on_item_selected(self):
        """Handle inventory item selection"""
        item_data = self.item_combo.currentData()
        if item_data:
            cost = item_data.get('cost') or item_data.get('purchase_price') or 0
            self.cost_input.setValue(cost)
            # Use explicit None checks to allow 0 as a valid value
            if item_data.get('weight_lbs') is not None:
                self.weight_input.setValue(float(item_data.get('weight_lbs')))
            if item_data.get('length_in') is not None:
                self.length_input.setValue(int(item_data.get('length_in')))
            if item_data.get('width_in') is not None:
                self.width_input.setValue(int(item_data.get('width_in')))
            if item_data.get('height_in') is not None:
                self.height_input.setValue(int(item_data.get('height_in')))
            self.calculate_prices()
    
    def on_profit_type_changed(self):
        """Handle profit type change"""
        if self.profit_dollar_radio.isChecked():
            self.profit_input.setPrefix("$")
            self.profit_input.setSuffix("")
            self.profit_input.setValue(10.00)
        else:
            self.profit_input.setPrefix("")
            self.profit_input.setSuffix("%")
            self.profit_input.setValue(30.00)
        self.calculate_prices()

    def _get_fee_setting(self, key, default):
        value = self.db.get_setting(key)
        if value in (None, ""):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def calculate_shipping_cost(self, weight, length, width, height):
        """
        Estimate shipping cost using simplified USPS rates
        This is a rough estimate - actual costs vary by destination
        """
        # Calculate dimensional weight
        dim_weight = (length * width * height) / 166
        billable_weight = max(weight, dim_weight)
        
        # Simplified USPS Priority Mail estimates
        if billable_weight <= 1:
            return 8.00
        elif billable_weight <= 2:
            return 9.00
        elif billable_weight <= 3:
            return 10.50
        elif billable_weight <= 5:
            return 13.00
        elif billable_weight <= 10:
            return 17.00
        elif billable_weight <= 20:
            return 25.00
        else:
            return 35.00
    
    def calculate_ebay_fee(self, price):
        """Calculate eBay final value fee"""
        percent = self._get_fee_setting('ebay_fee_percent', 0.129)
        fixed = self._get_fee_setting('ebay_fee_fixed', 0.30)
        return (price * percent) + fixed

    def calculate_payment_fee(self, price):
        """Calculate payment processing fee"""
        percent = self._get_fee_setting('payment_fee_percent', 0.029)
        fixed = self._get_fee_setting('payment_fee_fixed', 0.30)
        return (price * percent) + fixed
    
    def calculate_prices(self):
        """Calculate and display pricing options"""
        cost = self.cost_input.value()
        if cost == 0:
            self.results_display.setText("Please enter a cost basis to calculate prices.")
            return
        
        # Get target profit
        if self.profit_dollar_radio.isChecked():
            target_profit = self.profit_input.value()
        else:
            # Convert percentage to dollar amount
            target_profit = cost * (self.profit_input.value() / 100)
        
        # Get shipping cost
        weight = self.weight_input.value()
        length = self.length_input.value()
        width = self.width_input.value()
        height = self.height_input.value()
        shipping_cost = self.calculate_shipping_cost(weight, length, width, height)

        ebay_percent = self._get_fee_setting('ebay_fee_percent', 0.129)
        ebay_fixed = self._get_fee_setting('ebay_fee_fixed', 0.30)
        payment_percent = self._get_fee_setting('payment_fee_percent', 0.029)
        payment_fixed = self._get_fee_setting('payment_fee_fixed', 0.30)

        combined_percent = 1 - (ebay_percent + payment_percent)
        combined_fixed = ebay_fixed + payment_fixed

        if combined_percent <= 0:
            self.results_display.setText(
                "Fee settings result in a combined percentage of 100% or more. "
                "Please adjust the fee rates in Settings."
            )
            self.recommendation_label.setText("")
            return

        # Calculate Option A: Free Shipping (rolled into price)
        # price - shipping - ebay_fee - payment_fee - cost = target_profit
        # => price * (1 - ebay_percent - payment_percent) = target_profit + cost + shipping + combined_fixed
        price_a = (target_profit + cost + shipping_cost + combined_fixed) / combined_percent
        price_a = math.ceil(price_a * 100) / 100  # Round up to nearest cent

        ebay_fee_a = self.calculate_ebay_fee(price_a)
        payment_fee_a = self.calculate_payment_fee(price_a)
        net_profit_a = price_a - shipping_cost - ebay_fee_a - payment_fee_a - cost

        # Calculate Option B: Calculated Shipping (buyer pays)
        # Here: price - ebay_fee - payment_fee - cost = target_profit
        # => price * (1 - ebay_percent - payment_percent) = target_profit + cost + combined_fixed
        price_b = (target_profit + cost + combined_fixed) / combined_percent
        price_b = math.ceil(price_b * 100) / 100

        ebay_fee_b = self.calculate_ebay_fee(price_b)
        payment_fee_b = self.calculate_payment_fee(price_b)
        net_profit_b = price_b - ebay_fee_b - payment_fee_b - cost
        
        # Display results
        results_html = f"""
        <html>
        <body style="font-family: Arial; font-size: 13px;">
        <h3 style="color: #333;">Item Cost: ${cost:.2f} | Target Profit: ${target_profit:.2f}</h3>
        <p style="color: #666;">Estimated Shipping: ${shipping_cost:.2f} (USPS Priority)</p>
        
        <hr>
        
        <div style="background-color: #E3F2FD; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
        <h3 style="color: #1976D2; margin-top: 0;">✅ OPTION A: FREE SHIPPING</h3>
        <table style="width: 100%;">
        <tr><td><b>List Price:</b></td><td style="text-align: right; font-size: 20px; color: #1976D2;"><b>${price_a:.2f}</b></td></tr>
        <tr><td>Shipping (absorbed):</td><td style="text-align: right;">-${shipping_cost:.2f}</td></tr>
        <tr><td>eBay Fee ({ebay_percent*100:.2f}% + ${ebay_fixed:.2f}):</td><td style="text-align: right;">-${ebay_fee_a:.2f}</td></tr>
        <tr><td>Payment Fee ({payment_percent*100:.2f}% + ${payment_fixed:.2f}):</td><td style="text-align: right;">-${payment_fee_a:.2f}</td></tr>
        <tr><td>Your Cost:</td><td style="text-align: right;">-${cost:.2f}</td></tr>
        <tr style="border-top: 2px solid #1976D2;"><td><b>Net Profit:</b></td><td style="text-align: right; color: green; font-size: 18px;"><b>${net_profit_a:.2f}</b></td></tr>
        </table>
        <p style="margin-top: 10px; color: #555;">
        <b>Pros:</b> Better eBay search ranking, simpler for buyers<br>
        <b>Cons:</b> Higher list price
        </p>
        </div>
        
        <div style="background-color: #FFF3E0; padding: 15px; border-radius: 8px;">
        <h3 style="color: #F57C00; margin-top: 0;">📦 OPTION B: CALCULATED SHIPPING</h3>
        <table style="width: 100%;">
        <tr><td><b>List Price:</b></td><td style="text-align: right; font-size: 20px; color: #F57C00;"><b>${price_b:.2f}</b></td></tr>
        <tr><td>Buyer Pays Shipping:</td><td style="text-align: right;">+${shipping_cost:.2f}</td></tr>
        <tr><td>eBay Fee ({ebay_percent*100:.2f}% + ${ebay_fixed:.2f}):</td><td style="text-align: right;">-${ebay_fee_b:.2f}</td></tr>
        <tr><td>Payment Fee ({payment_percent*100:.2f}% + ${payment_fixed:.2f}):</td><td style="text-align: right;">-${payment_fee_b:.2f}</td></tr>
        <tr><td>Your Cost:</td><td style="text-align: right;">-${cost:.2f}</td></tr>
        <tr style="border-top: 2px solid #F57C00;"><td><b>Net Profit:</b></td><td style="text-align: right; color: green; font-size: 18px;"><b>${net_profit_b:.2f}</b></td></tr>
        </table>
        <p style="margin-top: 10px; color: #555;">
        <b>Pros:</b> Lower list price, transparent costs<br>
        <b>Cons:</b> Buyers may prefer free shipping
        </p>
        </div>
        
        <hr>
        
        <p style="font-size: 12px; color: #666; margin-top: 15px;">
        <b>Note:</b> Shipping cost is estimated. Actual cost varies by destination.
        eBay fees shown are standard rates and may vary by category.
        </p>
        </body>
        </html>
        """
        
        self.results_display.setHtml(results_html)
        
        # Recommendation
        if weight <= 1 and price_a < 50:
            recommendation = f"🎯 <b>Recommendation: FREE SHIPPING</b><br>For lightweight items under $50, free shipping typically performs better in eBay search results."
        elif shipping_cost > 15:
            recommendation = f"🎯 <b>Recommendation: CALCULATED SHIPPING</b><br>For heavy items with high shipping costs (${shipping_cost:.2f}), buyers expect to pay shipping separately."
        else:
            recommendation = f"🎯 <b>Recommendation: FREE SHIPPING</b><br>Free shipping generally provides better visibility and conversion on eBay."
        
        self.recommendation_label.setText(recommendation)
    
    def refresh_data(self):
        """Refresh the pricing tab (reload inventory items)"""
        current_selection = self.item_combo.currentIndex()
        self.item_combo.clear()
        self.item_combo.addItem("-- Select from Inventory --", None)
        self.load_inventory_items()
        if current_selection >= 0 and current_selection < self.item_combo.count():
            self.item_combo.setCurrentIndex(current_selection)
