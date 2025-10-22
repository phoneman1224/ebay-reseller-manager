"""
Sold Items Tab - Track your sales history and profits
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QGroupBox, QMessageBox, QDialog, QFormLayout,
                             QLineEdit, QDateEdit, QComboBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from datetime import datetime


from .value_helpers import resolve_cost


class SoldItemsTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_sold_items()
    
    def init_ui(self):
        """Initialize the sold items tab UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("💰 Sold Items - Sales History")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Summary stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("""
            background-color: #E8F5E9;
            padding: 10px;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
            font-weight: bold;
        """)
        header_layout.addWidget(self.stats_label)
        
        layout.addLayout(header_layout)
        
        # Info banner
        info = QLabel(
            "📊 Track all your sales, profits, and performance. "
            "Items marked as 'Sold' from Inventory appear here."
        )
        info.setStyleSheet("""
            background-color: #E3F2FD;
            padding: 8px;
            border-radius: 4px;
            border-left: 4px solid #2196F3;
        """)
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Filters
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout()
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Sales",
            "This Month",
            "Last 30 Days",
            "This Year"
        ])
        self.filter_combo.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Show:"))
        filter_layout.addWidget(self.filter_combo)
        
        filter_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_sold_items)
        filter_layout.addWidget(refresh_btn)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Sold items table
        self.sold_table = QTableWidget()
        self.sold_table.setColumnCount(9)
        self.sold_table.setHorizontalHeaderLabels([
            "Sold Date",
            "Title",
            "Purchase Cost",
            "Sold Price",
            "Platform",
            "Fees",
            "Net Profit",
            "Margin %",
            "Actions"
        ])
        
        # Set column widths
        header = self.sold_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title column
        for i in [0, 2, 3, 4, 5, 6, 7, 8]:  # Other columns fixed
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.sold_table.setAlternatingRowColors(True)
        self.sold_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.sold_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.sold_table)
    
    def load_sold_items(self, date_from=None, date_to=None):
        """Load sold items from database with optional date filtering"""
        try:
            # Use get_sales for better filtering support
            items = self.db.get_sales(date_from=date_from, date_to=date_to)
            
            self.sold_table.setRowCount(len(items))
            
            total_revenue = 0
            total_cost = 0
            total_fees = 0
            total_profit = 0
            
            for row, item in enumerate(items):
                try:
                    # Convert sqlite3.Row to dict
                    if not isinstance(item, dict):
                        item = dict(item)
                    
                    # Sold Date
                    sold_date = str(item.get('sold_date', 'N/A'))
                    self.sold_table.setItem(row, 0, QTableWidgetItem(sold_date))
                    
                    # Title
                    title = str(item.get('title', 'Untitled'))
                    self.sold_table.setItem(row, 1, QTableWidgetItem(title))
                    
                    # Purchase Cost
                    cost = resolve_cost(item)
                    self.sold_table.setItem(row, 2, QTableWidgetItem(f"${cost:.2f}"))
                    
                    # Sold Price
                    try:
                        sold_price = float(item.get('sold_price', 0))
                    except (ValueError, TypeError):
                        sold_price = 0.0
                    self.sold_table.setItem(row, 3, QTableWidgetItem(f"${sold_price:.2f}"))
                    
                    # Platform
                    platform = str(item.get('platform', 'eBay'))
                    self.sold_table.setItem(row, 4, QTableWidgetItem(platform))
                    
                    # Fees
                    try:
                        fees = float(item.get('fees', 0))
                    except (ValueError, TypeError):
                        fees = 0.0
                    self.sold_table.setItem(row, 5, QTableWidgetItem(f"${fees:.2f}"))
                    
                    # Net Profit
                    profit = sold_price - cost - fees
                    profit_item = QTableWidgetItem(f"${profit:.2f}")
                    
                    # Color code profit
                    if profit > 0:
                        profit_item.setForeground(QColor("#4CAF50"))  # Green
                    elif profit < 0:
                        profit_item.setForeground(QColor("#F44336"))  # Red
                    
                    profit_item.setFont(QFont("Arial", weight=QFont.Weight.Bold))
                    self.sold_table.setItem(row, 6, profit_item)
                    
                    # Margin %
                    if cost > 0:
                        margin = (profit / cost) * 100
                        margin_item = QTableWidgetItem(f"{margin:.1f}%")
                        
                        # Color code margin
                        if margin >= 100:
                            margin_item.setForeground(QColor("#4CAF50"))  # Green
                        elif margin >= 50:
                            margin_item.setForeground(QColor("#8BC34A"))  # Light green
                        elif margin >= 0:
                            margin_item.setForeground(QColor("#FF9800"))  # Orange
                        else:
                            margin_item.setForeground(QColor("#F44336"))  # Red
                        
                        self.sold_table.setItem(row, 7, margin_item)
                    else:
                        self.sold_table.setItem(row, 7, QTableWidgetItem("N/A"))
                    
                    # Actions button
                    actions_btn = QPushButton("📝")
                    # Apply a compact style to the action button so it fits neatly
                    # within the table cell and remains legible. Use a smaller
                    # font size and a fixed maximum width similar to the
                    # inventory tab action buttons.
                    actions_btn.setMaximumWidth(32)
                    actions_btn.setToolTip("Edit Sale Details")
                    actions_btn.setStyleSheet(
                        """
                        QPushButton {
                            padding: 4px;
                            font-size: 14px;
                            background-color: #FF9800;
                            color: white;
                            border-radius: 3px;
                        }
                        QPushButton:hover {
                            background-color: #F57C00;
                        }
                        """
                    )
                    item_id = item.get('id')
                    if item_id is not None:
                        actions_btn.clicked.connect(lambda checked, i=item_id: self.edit_sale(i))
                    self.sold_table.setCellWidget(row, 8, actions_btn)
                    
                    # Update totals
                    total_revenue += sold_price
                    total_cost += cost
                    total_fees += fees
                    total_profit += profit
                
                except Exception as e:
                    print(f"Error processing sold item at row {row}: {e}")
                    continue

            # Update stats
            total_sales = len(items)
            avg_profit = total_profit / total_sales if total_sales > 0 else 0
            
            self.stats_label.setText(
                f"📊 {total_sales} Sales | "
                f"💰 ${total_revenue:.2f} Revenue | "
                f"💵 ${total_profit:.2f} Profit | "
                f"📈 ${avg_profit:.2f} Avg"
            )
            
        except Exception as e:
            print(f"Error loading sold items: {e}")
            QMessageBox.warning(
                self, 
                "Error", 
                "There was an error loading the sold items. Please try again or contact support if the problem persists."
            )
    
    def apply_filters(self):
        """Apply date filters to sold items"""
        filter_type = self.filter_combo.currentText()

        # Calculate date range based on filter type
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta

        date_from = None
        date_to = None
        today = datetime.now().date()

        if filter_type == "This Month":
            # First day of current month to today
            date_from = today.replace(day=1).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        elif filter_type == "Last 30 Days":
            # 30 days ago to today
            date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        elif filter_type == "This Year":
            # January 1st of current year to today
            date_from = today.replace(month=1, day=1).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        # else: "All Sales" - no date filtering (date_from and date_to remain None)

        # Load sold items with date filter
        self.load_sold_items(date_from=date_from, date_to=date_to)
    
    def edit_sale(self, item_id):
        """Edit sale details"""
        # Get item details and convert to a regular dict for safe key access.
        item = self.db.get_inventory_item(item_id)
        if not item:
            QMessageBox.warning(self, "Not Found", "Item not found.")
            return
        # sqlite3.Row does not implement dict.get; convert if necessary
        if not isinstance(item, dict):
            item = dict(item)
        
        # Create edit dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Sale Details")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        # Form
        form = QFormLayout()

        # Title (read-only) - use .get() for defensive access
        title_label = QLabel(item.get('title', 'Untitled'))
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: bold;")
        form.addRow("Item:", title_label)
        
        # Sold Price (field stored as sold_price in the inventory table)
        sale_price_input = QLineEdit()
        sale_price_input.setText(str(item.get('sold_price', '')))
        sale_price_input.setPlaceholderText("Enter sold price")
        form.addRow("Sold Price ($):", sale_price_input)

        # Sold Date (field stored as sold_date in the inventory table)
        sale_date_input = QDateEdit()
        sale_date_str = item.get('sold_date', '')
        if sale_date_str:
            try:
                date_obj = datetime.strptime(sale_date_str, '%Y-%m-%d')
                sale_date_input.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
            except Exception:
                sale_date_input.setDate(QDate.currentDate())
        else:
            sale_date_input.setDate(QDate.currentDate())
        sale_date_input.setCalendarPopup(True)
        form.addRow("Sold Date:", sale_date_input)

        # Platform
        platform_input = QComboBox()
        platform_input.addItems(["eBay", "Mercari", "Poshmark", "Facebook", "Other"])
        current_platform = item.get('platform', 'eBay')
        platform_input.setCurrentText(current_platform)
        form.addRow("Platform:", platform_input)

        # Fees (stored in the fees column)
        fees_input = QLineEdit()
        fees_input.setText(str(item.get('fees', '')))
        fees_input.setPlaceholderText("Enter fees paid")
        form.addRow("Fees Paid ($):", fees_input)
        
        layout.addLayout(form)
        
        # Profit calculation display
        profit_label = QLabel()
        profit_label.setStyleSheet("""
            background-color: #E8F5E9;
            padding: 10px;
            border-radius: 4px;
            font-weight: bold;
        """)
        layout.addWidget(profit_label)
        
        # Update profit calculation when values change
        def update_profit():
            """Recalculate profit based on current inputs."""
            try:
                # Use purchase_cost as the base cost of goods sold.
                cost = resolve_cost(item) or 0.0
                sale_price = float(sale_price_input.text() or 0)
                fees_value = float(fees_input.text() or 0)
                profit = sale_price - cost - fees_value
                margin = (profit / cost * 100) if cost > 0 else 0

                profit_label.setText(
                    f"💰 Cost: ${cost:.2f} | "
                    f"Sale: ${sale_price:.2f} | "
                    f"Fees: ${fees_value:.2f} | "
                    f"Profit: ${profit:.2f} ({margin:.1f}%)"
                )
            except ValueError:
                profit_label.setText("⚠️ Enter valid numbers")
        
        sale_price_input.textChanged.connect(update_profit)
        fees_input.textChanged.connect(update_profit)
        update_profit()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(lambda: self.save_sale_edit(
            dialog, item_id,
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
    
    def save_sale_edit(self, dialog, item_id, sale_price, sale_date, platform, fees):
        """Save edited sale details"""
        try:
            sale_price_val = float(sale_price) if sale_price else 0
            fees_val = float(fees) if fees else 0
            
            # Update in database
            self.db.update_sale_details(
                item_id,
                sale_price=sale_price_val,
                sale_date=sale_date,
                platform=platform,
                fees=fees_val
            )
            
            QMessageBox.information(self, "✅ Saved", "Sale details updated successfully!")
            dialog.accept()
            self.load_sold_items()
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for price and fees.")
    
    def refresh_data(self):
        """Refresh the sold items list"""
        self.load_sold_items()
