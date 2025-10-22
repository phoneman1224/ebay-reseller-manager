"""
Dashboard Tab - Overview of business metrics
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGroupBox, QGridLayout, QFrame, QSizePolicy, QScrollArea)
from PyQt6.QtCore import Qt
from datetime import datetime


from .value_helpers import resolve_cost, format_currency


class DashboardTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
        self.refresh_data()
    
    def init_ui(self):
        """Initialize the dashboard UI"""
        layout = QVBoxLayout(self)
        
        # Header
        title = QLabel("📊 Business Dashboard")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Current year label
        current_year = datetime.now().year
        year_label = QLabel(f"Year: {current_year}")
        year_label.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(year_label)
        
        # Main metrics in cards - place the grid inside a scroll area so
        # overflowing content is scrollable when the window is small.
        metrics_widget = QWidget()
        metrics_layout = QGridLayout(metrics_widget)
        metrics_layout.setSpacing(15)
        
        # Inventory Card
        self.inventory_card = self.create_metric_card(
            "📦 Inventory",
            "0 items",
            "Val: $0.00",
            "#E3F2FD"
        )
        metrics_layout.addWidget(self.inventory_card, 0, 0)
        
        # Revenue Card
        # Create the revenue card first and place it in column 1. A revenue card
        # displays year‑to‑date revenue metrics along with the number of sales.
        self.revenue_card = self.create_metric_card(
            "💰 Revenue (YTD)",
            "$0.00",
            "0 sales YTD",
            "#E8F5E9"
        )
        metrics_layout.addWidget(self.revenue_card, 0, 1)

        # Expenses Card
        # Create the expenses card and place it in column 2. This card was
        # mistakenly added using the revenue card widget in the original code,
        # causing duplicate widgets and layout issues. It now correctly uses
        # the expenses_card variable when adding to the grid.
        self.expenses_card = self.create_metric_card(
            "💵 Expenses (YTD)",
            "$0.00",
            "Deductible: $0.00",
            "#FFF3E0"
        )
        metrics_layout.addWidget(self.expenses_card, 0, 2)
        
        # Profit Card
        self.profit_card = self.create_metric_card(
            "📈 Net Profit (YTD)",
            "$0.00",
            "Mrg: 0%",
            "#F3E5F5"
        )
        metrics_layout.addWidget(self.profit_card, 1, 0)
        
        # Tax Liability Card
        self.tax_card = self.create_metric_card(
            "🧾 Est. Tax Liability",
            "$0.00",
            "SE + Inc Tax",
            "#FFEBEE"
        )
        metrics_layout.addWidget(self.tax_card, 1, 1)
        
        # Quick Stats Card
        self.stats_card = self.create_metric_card(
            "📊 Quick Stats",
            "Items Listed: 0",
            "Avg: $0.00",
            "#E0F2F1"
        )
        metrics_layout.addWidget(self.stats_card, 1, 2)
        
        # Evenly distribute the available space across the three columns. Using
        # stretch factors of 1 allows the cards to resize proportionally with
        # the window instead of forcing fixed minimum widths. This provides
        # better responsiveness on different screen sizes and avoids clipping
        # when text values grow.
        for i in range(3):
            metrics_layout.setColumnStretch(i, 1)
        # Row stretch factors are intentionally left unset because the
        # scroll area will handle vertical overflow.  Allowing the cards to
        # assume their natural size prevents vertical squishing on tall
        # windows while the scroll area provides scrollability on small
        # windows.
        
        # Wrap the metrics widget in a scroll area.  Setting widgetResizable
        # ensures the scroll area resizes its contents appropriately.  This
        # prevents the cards from being clipped when the window is too small
        # and allows vertical scrolling if necessary.
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(metrics_widget)
        layout.addWidget(scroll_area)
        layout.addStretch()  # Push everything to top
        
        # Expense Breakdown
        expense_group = QGroupBox("Expense Breakdown by Category")
        expense_layout = QVBoxLayout()
        self.expense_breakdown_label = QLabel("No expenses recorded yet")
        self.expense_breakdown_label.setWordWrap(True)
        expense_layout.addWidget(self.expense_breakdown_label)
        expense_group.setLayout(expense_layout)
        layout.addWidget(expense_group)
        
        # Recent Activity
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout()
        self.recent_activity_label = QLabel("No recent activity")
        self.recent_activity_label.setWordWrap(True)
        activity_layout.addWidget(self.recent_activity_label)
        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group)
        
        layout.addStretch()
    
    def create_metric_card(self, title, main_value, sub_value, color):
        """Create a metric card widget"""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        # Allow the card to expand both horizontally and vertically within the
        # grid layout.  Using an expanding size policy ensures that the
        # cards scale appropriately when the window is resized and prevents
        # them from being squeezed or clipped.
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Set a minimum height for the card but allow it to grow if the content
        # wraps onto multiple lines (e.g., on smaller screens). This prevents
        # labels from being clipped or overlapping when the window is narrow.
        # Provide a modest minimum height so the card can accommodate wrapped
        # text without enforcing a tall footprint.  The scroll area will
        # handle cases where more vertical space is required.
        card.setMinimumHeight(140)
        # Reduce the minimum width to avoid overly wide cards on small screens.
        # The grid layout will still distribute available space evenly across
        # columns due to the stretch factors.
        card.setMinimumWidth(200)
        # Allow the card to expand horizontally with its layout. Removing the
        # explicit maximum width lets the grid layout determine a suitable width
        # based on the available space and the column stretch factors.
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(5)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        card_layout.addWidget(title_label)
        
        main_label = QLabel(main_value)
        # Use a more moderate font size for the primary value to prevent
        # overflow on narrow windows.  The font remains bold for emphasis.
        main_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        main_label.setWordWrap(True)
        card_layout.addWidget(main_label)

        sub_label = QLabel(sub_value)
        # Reduce the subtitle font slightly and allow it to wrap cleanly.
        sub_label.setStyleSheet("font-size: 11px; color: #555;")
        sub_label.setWordWrap(True)
        card_layout.addWidget(sub_label)
        
        card_layout.addStretch()
        
        # Store labels for updating
        card.main_label = main_label
        card.sub_label = sub_label
        
        return card
    
    def refresh_data(self):
        """Refresh all dashboard data"""
        current_year = datetime.now().year
        
        # Inventory metrics
        inventory_items = [dict(item) for item in self.db.get_inventory_items(status='In Stock')]
        inventory_value = self.db.get_inventory_value()
        inventory_count = len(inventory_items)
        
        self.inventory_card.main_label.setText(f"{inventory_count} items")
        # Shorten "Value" to "Val" to save space
        self.inventory_card.sub_label.setText(f"Val: ${inventory_value:.2f}")
        
        # Revenue metrics
        total_revenue = self.db.get_total_revenue(current_year)
        sales = [dict(row) for row in self.db.get_sales()]
        year_sales = [s for s in sales if (s.get('sold_date') or '').startswith(str(current_year))]
        sales_count = sum(int(s.get('quantity') or 1) for s in year_sales)
        
        self.revenue_card.main_label.setText(f"${total_revenue:.2f}")
        # Display sales count with "YTD" abbreviation for Year‑To‑Date
        self.revenue_card.sub_label.setText(f"{sales_count} sales YTD")
        
        # Expenses metrics
        all_expenses = [dict(expense) for expense in self.db.get_expenses()]
        year_expenses = [e for e in all_expenses if (e.get('date') or '').startswith(str(current_year))]
        total_expenses = sum(float(e.get('amount') or 0) for e in year_expenses)
        deductible_expenses = self.db.get_total_deductible_expenses(current_year)
        
        self.expenses_card.main_label.setText(f"${total_expenses:.2f}")
        # Shorten "Tax Deductible" to "Deductible" to conserve space
        self.expenses_card.sub_label.setText(f"Deductible: ${deductible_expenses:.2f}")
        
        # Profit metrics
        total_profit = self.db.get_total_profit(current_year)
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        self.profit_card.main_label.setText(f"${total_profit:.2f}")
        # Shorten "Margin" to "Mrg" for brevity
        self.profit_card.sub_label.setText(f"Mrg: {profit_margin:.1f}%")
        
        # Tax liability (simplified calculation)
        # Taxable income = Revenue - COGS - Deductible Expenses
        # This is a rough estimate
        taxable_income = max(0, total_profit)
        
        # Self-employment tax (15.3% on net profit)
        self_employment_tax = taxable_income * 0.153
        
        # Estimated income tax (using 22% as rough estimate - user should set their bracket)
        income_tax_rate = float(self.db.get_setting('income_tax_rate', '0.22'))
        estimated_income_tax = taxable_income * income_tax_rate
        
        total_tax_liability = self_employment_tax + estimated_income_tax
        
        self.tax_card.main_label.setText(f"${total_tax_liability:.2f}")
        # Shorten "Income" to "Inc" to reduce length
        self.tax_card.sub_label.setText(f"SE: ${self_employment_tax:.2f} | Inc: ${estimated_income_tax:.2f}")
        
        # Quick stats
        listed_items = self.db.get_inventory_items(status='Listed')
        listed_count = len(listed_items)
        avg_sale = (total_revenue / sales_count) if sales_count > 0 else 0
        
        # The quick stats card shows how many items are listed and the average sale price.
        self.stats_card.main_label.setText(f"Items Listed: {listed_count}")
        # Abbreviate "Avg Sale" to simply "Avg" to save space
        self.stats_card.sub_label.setText(f"Avg: ${avg_sale:.2f}")
        
        # Expense breakdown
        expense_breakdown = self.db.get_expense_breakdown(current_year)
        if expense_breakdown:
            breakdown_text = "<b>Top Categories:</b><br>"
            for entry in expense_breakdown[:5]:  # Top 5
                breakdown_text += (
                    f"• {entry['category']}: ${entry['total']:.2f} "
                    f"({entry['count']} expenses)<br>"
                )
            self.expense_breakdown_label.setText(breakdown_text)
        else:
            self.expense_breakdown_label.setText("No expenses recorded yet")
        
        # Recent activity
        recent_sales = sales[:5]
        recent_items = [dict(item) for item in self.db.get_inventory_items()[:5]]

        activity_text = ""
        if recent_sales:
            activity_text += "<b>Recent Sales:</b><br>"
            for sale in recent_sales:
                title = (sale.get('title') or 'Untitled')[:30]
                sold_price = sale.get('sold_price')
                sold_price_text = f"${sold_price:.2f}" if isinstance(sold_price, (int, float)) else "N/A"
                sold_date = sale.get('sold_date') or 'N/A'
                quantity = int(sale.get('quantity') or 1)
                quantity_suffix = f" x{quantity}" if quantity > 1 else ""
                activity_text += f"• {title}{quantity_suffix}: {sold_price_text} ({sold_date})<br>"

        if recent_items:
            activity_text += "<br><b>Recently Added to Inventory:</b><br>"
            for item in recent_items:
                if not isinstance(item, dict):
                    item = dict(item)
                title = (item.get('title') or 'Untitled')[:30]
                cost_text = format_currency(resolve_cost(item))
                activity_text += f"• {title} - {cost_text}<br>"
        
        if activity_text:
            self.recent_activity_label.setText(activity_text)
        else:
            self.recent_activity_label.setText("No recent activity")
