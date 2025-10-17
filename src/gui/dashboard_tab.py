"""
Dashboard Tab - Overview of business metrics
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGroupBox, QGridLayout, QFrame)
from PyQt6.QtCore import Qt
from datetime import datetime


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
        
        # Main metrics in cards
        metrics_layout = QGridLayout()
        
        # Inventory Card
        self.inventory_card = self.create_metric_card(
            "📦 Inventory",
            "0 items",
            "$0.00",
            "#E3F2FD"
        )
        metrics_layout.addWidget(self.inventory_card, 0, 0)
        
        # Revenue Card
        self.revenue_card = self.create_metric_card(
            "💰 Revenue (YTD)",
            "$0.00",
            "0 sales",
            "#E8F5E9"
        )
        metrics_layout.addWidget(self.revenue_card, 0, 1)
        
        # Expenses Card
        self.expenses_card = self.create_metric_card(
            "💵 Expenses (YTD)",
            "$0.00",
            "Tax Deductible: $0.00",
            "#FFF3E0"
        )
        metrics_layout.addWidget(self.expenses_card, 0, 2)
        
        # Profit Card
        self.profit_card = self.create_metric_card(
            "📈 Net Profit (YTD)",
            "$0.00",
            "Margin: 0%",
            "#F3E5F5"
        )
        metrics_layout.addWidget(self.profit_card, 1, 0)
        
        # Tax Liability Card
        self.tax_card = self.create_metric_card(
            "🧾 Est. Tax Liability",
            "$0.00",
            "Self-Emp + Income Tax",
            "#FFEBEE"
        )
        metrics_layout.addWidget(self.tax_card, 1, 1)
        
        # Quick Stats Card
        self.stats_card = self.create_metric_card(
            "📊 Quick Stats",
            "Items Listed: 0",
            "Avg Sale: $0.00",
            "#E0F2F1"
        )
        metrics_layout.addWidget(self.stats_card, 1, 2)
        
        layout.addLayout(metrics_layout)
        
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
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        card_layout.addWidget(title_label)
        
        main_label = QLabel(main_value)
        main_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #333; margin: 10px 0;")
        card_layout.addWidget(main_label)
        
        sub_label = QLabel(sub_value)
        sub_label.setStyleSheet("font-size: 16px; color: #555;")
        card_layout.addWidget(sub_label)
        
        # Store labels for updating
        card.main_label = main_label
        card.sub_label = sub_label
        
        return card
    
    def refresh_data(self):
        """Refresh all dashboard data"""
        current_year = datetime.now().year
        
        # Inventory metrics
        inventory_items = self.db.get_inventory_items(status='In Stock')
        inventory_value = self.db.get_inventory_value()
        inventory_count = len(inventory_items)
        
        self.inventory_card.main_label.setText(f"{inventory_count} items")
        self.inventory_card.sub_label.setText(f"Value: ${inventory_value:.2f}")
        
        # Revenue metrics
        total_revenue = self.db.get_total_revenue(current_year)
        sales = self.db.get_sales()
        year_sales = [s for s in sales if s['sale_date'].startswith(str(current_year))]
        sales_count = len(year_sales)
        
        self.revenue_card.main_label.setText(f"${total_revenue:.2f}")
        self.revenue_card.sub_label.setText(f"{sales_count} sales this year")
        
        # Expenses metrics
        all_expenses = self.db.get_expenses()
        year_expenses = [e for e in all_expenses if e['date'].startswith(str(current_year))]
        total_expenses = sum([e['amount'] for e in year_expenses])
        deductible_expenses = self.db.get_total_deductible_expenses(current_year)
        
        self.expenses_card.main_label.setText(f"${total_expenses:.2f}")
        self.expenses_card.sub_label.setText(f"Tax Deductible: ${deductible_expenses:.2f}")
        
        # Profit metrics
        total_profit = self.db.get_total_profit(current_year)
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        self.profit_card.main_label.setText(f"${total_profit:.2f}")
        self.profit_card.sub_label.setText(f"Margin: {profit_margin:.1f}%")
        
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
        self.tax_card.sub_label.setText(f"SE: ${self_employment_tax:.2f} | Income: ${estimated_income_tax:.2f}")
        
        # Quick stats
        listed_items = self.db.get_inventory_items(status='Listed')
        listed_count = len(listed_items)
        avg_sale = (total_revenue / sales_count) if sales_count > 0 else 0
        
        self.stats_card.main_label.setText(f"Items Listed: {listed_count}")
        self.stats_card.sub_label.setText(f"Avg Sale: ${avg_sale:.2f}")
        
        # Expense breakdown
        expense_breakdown = self.db.get_expense_breakdown(current_year)
        if expense_breakdown:
            breakdown_text = "<b>Top Categories:</b><br>"
            for category in expense_breakdown[:5]:  # Top 5
                breakdown_text += f"• {category['category']}: ${category['total']:.2f} ({category['count']} expenses)<br>"
            self.expense_breakdown_label.setText(breakdown_text)
        else:
            self.expense_breakdown_label.setText("No expenses recorded yet")
        
        # Recent activity
        recent_sales = self.db.get_sales()[:5]
        recent_items = self.db.get_inventory_items()[:5]
        
        activity_text = ""
        if recent_sales:
            activity_text += "<b>Recent Sales:</b><br>"
            for sale in recent_sales:
                item = self.db.get_inventory_item(sale['inventory_id'])
                if item:
                    activity_text += f"• {item['title'][:30]}: ${sale['sale_price']:.2f} ({sale['sale_date']})<br>"
        
        if recent_items:
            activity_text += "<br><b>Recently Added to Inventory:</b><br>"
            for item in recent_items:
                activity_text += f"• {item['title'][:30]} - ${item['purchase_cost']:.2f}<br>"
        
        if activity_text:
            self.recent_activity_label.setText(activity_text)
        else:
            self.recent_activity_label.setText("No recent activity")
