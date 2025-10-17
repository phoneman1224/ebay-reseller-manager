"""
Reports & Export Tab - Generate reports and export data
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QGroupBox, QFormLayout, QComboBox,
                             QTextEdit, QFileDialog, QMessageBox, QRadioButton,
                             QButtonGroup)
from PyQt6.QtCore import Qt
from datetime import datetime
import csv
import os


class ReportsTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        """Initialize the reports tab UI"""
        layout = QVBoxLayout(self)
        
        # Header
        title = QLabel("📈 Reports & Export")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(title)
        
        subtitle = QLabel("Export your data to CSV files for accounting, tax prep, or analysis")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        
        # Export sections in two columns
        main_layout = QHBoxLayout()
        
        # Left column
        left_column = QVBoxLayout()
        
        # Quick Reports
        quick_reports_group = QGroupBox("📊 Quick Reports")
        quick_layout = QVBoxLayout()
        
        inventory_report_btn = QPushButton("📦 Export Inventory Report")
        inventory_report_btn.clicked.connect(self.export_inventory_report)
        quick_layout.addWidget(inventory_report_btn)
        
        expense_report_btn = QPushButton("💵 Export Expense Report")
        expense_report_btn.clicked.connect(self.export_expense_report)
        quick_layout.addWidget(expense_report_btn)
        
        sales_report_btn = QPushButton("💰 Export Sales Report")
        sales_report_btn.clicked.connect(self.export_sales_report)
        quick_layout.addWidget(sales_report_btn)
        
        profit_loss_btn = QPushButton("📊 Export Profit & Loss Statement")
        profit_loss_btn.clicked.connect(self.export_profit_loss)
        quick_layout.addWidget(profit_loss_btn)
        
        tax_report_btn = QPushButton("🧾 Export Tax Deductions Report")
        tax_report_btn.clicked.connect(self.export_tax_report)
        quick_layout.addWidget(tax_report_btn)
        
        quick_reports_group.setLayout(quick_layout)
        left_column.addWidget(quick_reports_group)
        
        # Analytics
        analytics_group = QGroupBox("📈 Business Analytics")
        analytics_layout = QVBoxLayout()
        
        self.analytics_display = QTextEdit()
        self.analytics_display.setReadOnly(True)
        self.analytics_display.setMaximumHeight(250)
        analytics_layout.addWidget(self.analytics_display)
        
        refresh_analytics_btn = QPushButton("🔄 Refresh Analytics")
        refresh_analytics_btn.clicked.connect(self.load_analytics)
        analytics_layout.addWidget(refresh_analytics_btn)
        
        analytics_group.setLayout(analytics_layout)
        left_column.addWidget(analytics_group)
        
        main_layout.addLayout(left_column)
        
        # Right column
        right_column = QVBoxLayout()
        
        # Custom Export
        custom_export_group = QGroupBox("🎯 Custom Export")
        custom_layout = QFormLayout()
        
        self.export_type_combo = QComboBox()
        self.export_type_combo.addItems([
            "All Data (Complete Backup)",
            "Inventory Only",
            "Expenses Only",
            "Sales Only",
            "Active Listings Only",
            "Sold Items Only"
        ])
        custom_layout.addRow("Export Type:", self.export_type_combo)
        
        self.year_filter_combo = QComboBox()
        self.year_filter_combo.addItem("All Years", None)
        current_year = datetime.now().year
        for year in range(current_year, current_year - 5, -1):
            self.year_filter_combo.addItem(str(year), year)
        custom_layout.addRow("Filter by Year:", self.year_filter_combo)
        
        custom_export_btn = QPushButton("📥 Export Custom Data")
        custom_export_btn.setStyleSheet("background-color: #4CAF50; padding: 10px;")
        custom_export_btn.clicked.connect(self.export_custom)
        custom_layout.addRow("", custom_export_btn)
        
        custom_export_group.setLayout(custom_layout)
        right_column.addWidget(custom_export_group)
        
        # Export Log
        log_group = QGroupBox("📝 Export Log")
        log_layout = QVBoxLayout()
        
        self.export_log = QTextEdit()
        self.export_log.setReadOnly(True)
        self.export_log.setMaximumHeight(300)
        self.export_log.setPlaceholderText("Export history will appear here...")
        log_layout.addWidget(self.export_log)
        
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(lambda: self.export_log.clear())
        log_layout.addWidget(clear_log_btn)
        
        log_group.setLayout(log_layout)
        right_column.addWidget(log_group)
        
        main_layout.addLayout(right_column)
        
        layout.addLayout(main_layout)
        
        # Load initial analytics
        self.load_analytics()
    
    def export_inventory_report(self):
        """Export inventory report to CSV"""
        filename = self.get_save_filename("inventory_report")
        if not filename:
            return
        
        try:
            items = self.db.get_inventory_items()
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow([
                    'ID', 'Title', 'Brand', 'Model', 'Condition', 'Purchase Date',
                    'Purchase Cost', 'Purchase Source', 'Storage Location', 'Status',
                    'eBay Item ID', 'Listed Date', 'Listed Price', 'Sold Date', 'Sold Price'
                ])
                
                # Data
                for item in items:
                    writer.writerow([
                        item['id'], item['title'], item['brand'], item['model'],
                        item['condition'], item['purchase_date'], item['purchase_cost'],
                        item['purchase_source'], item['storage_location'], item['status'],
                        item['ebay_item_id'], item['listed_date'], item['listed_price'],
                        item['sold_date'], item['sold_price']
                    ])
            
            self.log_export(f"Inventory Report: {len(items)} items exported")
            QMessageBox.information(
                self, "Export Complete",
                f"Inventory report exported successfully!\n\n{len(items)} items exported to:\n{filename}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export inventory report:\n\n{str(e)}")
    
    def export_expense_report(self):
        """Export expense report to CSV"""
        filename = self.get_save_filename("expense_report")
        if not filename:
            return
        
        try:
            expenses = self.db.get_expenses()
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow([
                    'ID', 'Date', 'Amount', 'Vendor', 'Category', 'Description',
                    'Payment Method', 'Tax Deductible', 'Notes'
                ])
                
                # Data
                total = 0
                deductible_total = 0
                for expense in expenses:
                    writer.writerow([
                        expense['id'], expense['date'], expense['amount'],
                        expense['vendor'], expense['category'], expense['description'],
                        expense['payment_method'], 
                        'Yes' if expense['tax_deductible'] else 'No',
                        expense['notes']
                    ])
                    total += expense['amount']
                    if expense['tax_deductible']:
                        deductible_total += expense['amount']
                
                # Summary rows
                writer.writerow([])
                writer.writerow(['TOTAL EXPENSES:', '', total])
                writer.writerow(['TAX DEDUCTIBLE:', '', deductible_total])
            
            self.log_export(f"Expense Report: {len(expenses)} expenses exported")
            QMessageBox.information(
                self, "Export Complete",
                f"Expense report exported successfully!\n\n"
                f"{len(expenses)} expenses totaling ${total:,.2f}\n"
                f"Tax deductible: ${deductible_total:,.2f}\n\n"
                f"Saved to: {filename}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export expense report:\n\n{str(e)}")
    
    def export_sales_report(self):
        """Export sales report to CSV"""
        filename = self.get_save_filename("sales_report")
        if not filename:
            return
        
        try:
            sales = self.db.get_sales()
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow([
                    'ID', 'Inventory ID', 'eBay Order ID', 'Sale Date', 'Sale Price',
                    'Shipping Paid', 'eBay Fee', 'Payment Fee', 'Shipping Cost',
                    'Net Profit', 'Buyer Username'
                ])
                
                # Data
                total_revenue = 0
                total_profit = 0
                for sale in sales:
                    writer.writerow([
                        sale['id'], sale['inventory_id'], sale['ebay_order_id'],
                        sale['sale_date'], sale['sale_price'], sale['shipping_paid'],
                        sale['ebay_fee'], sale['payment_fee'], sale['shipping_cost'],
                        sale['net_profit'], sale['buyer_username']
                    ])
                    total_revenue += sale['sale_price']
                    total_profit += sale['net_profit'] if sale['net_profit'] else 0
                
                # Summary rows
                writer.writerow([])
                writer.writerow(['TOTAL REVENUE:', '', '', '', total_revenue])
                writer.writerow(['TOTAL NET PROFIT:', '', '', '', '', '', '', '', '', total_profit])
            
            self.log_export(f"Sales Report: {len(sales)} sales exported")
            QMessageBox.information(
                self, "Export Complete",
                f"Sales report exported successfully!\n\n"
                f"{len(sales)} sales totaling ${total_revenue:,.2f}\n"
                f"Net profit: ${total_profit:,.2f}\n\n"
                f"Saved to: {filename}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export sales report:\n\n{str(e)}")
    
    def export_profit_loss(self):
        """Export profit & loss statement to CSV"""
        filename = self.get_save_filename("profit_loss_statement")
        if not filename:
            return
        
        try:
            # Get data
            current_year = datetime.now().year
            revenue = self.db.get_total_revenue(current_year)
            expenses = self.db.get_total_deductible_expenses(current_year)
            profit = self.db.get_total_profit(current_year)
            expense_breakdown = self.db.get_expense_breakdown(current_year)
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow(['PROFIT & LOSS STATEMENT'])
                writer.writerow([f'Year: {current_year}'])
                writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}'])
                writer.writerow([])
                
                # Revenue
                writer.writerow(['REVENUE'])
                writer.writerow(['Gross Sales', revenue])
                writer.writerow([])
                
                # Expenses
                writer.writerow(['EXPENSES'])
                for category in expense_breakdown:
                    writer.writerow([category['category'], category['total']])
                writer.writerow(['Total Expenses', expenses])
                writer.writerow([])
                
                # Net Profit
                writer.writerow(['NET PROFIT', profit])
                writer.writerow([])
                
                # Margin
                margin = (profit / revenue * 100) if revenue > 0 else 0
                writer.writerow(['Profit Margin', f'{margin:.1f}%'])
            
            self.log_export(f"P&L Statement exported for {current_year}")
            QMessageBox.information(
                self, "Export Complete",
                f"Profit & Loss statement exported!\n\n"
                f"Revenue: ${revenue:,.2f}\n"
                f"Expenses: ${expenses:,.2f}\n"
                f"Net Profit: ${profit:,.2f}\n\n"
                f"Saved to: {filename}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export P&L statement:\n\n{str(e)}")
    
    def export_tax_report(self):
        """Export tax deductions report to CSV"""
        filename = self.get_save_filename("tax_deductions")
        if not filename:
            return
        
        try:
            current_year = datetime.now().year
            expenses = self.db.get_expenses()
            
            # Filter deductible expenses for current year
            deductible = [e for e in expenses 
                         if e['tax_deductible'] and 
                         e['date'] and e['date'].startswith(str(current_year))]
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow(['TAX DEDUCTIONS REPORT'])
                writer.writerow([f'Year: {current_year}'])
                writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}'])
                writer.writerow([])
                
                writer.writerow([
                    'Date', 'Amount', 'Vendor', 'Category', 'Description', 'Payment Method'
                ])
                
                # Data
                total = 0
                category_totals = {}
                
                for expense in deductible:
                    writer.writerow([
                        expense['date'], expense['amount'], expense['vendor'],
                        expense['category'], expense['description'], expense['payment_method']
                    ])
                    total += expense['amount']
                    
                    # Track by category
                    cat = expense['category']
                    category_totals[cat] = category_totals.get(cat, 0) + expense['amount']
                
                # Summary
                writer.writerow([])
                writer.writerow(['SUMMARY BY CATEGORY'])
                for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
                    writer.writerow([cat, amount])
                
                writer.writerow([])
                writer.writerow(['TOTAL TAX DEDUCTIBLE EXPENSES', total])
            
            self.log_export(f"Tax Deductions Report: ${total:,.2f}")
            QMessageBox.information(
                self, "Export Complete",
                f"Tax deductions report exported!\n\n"
                f"{len(deductible)} deductible expenses\n"
                f"Total: ${total:,.2f}\n\n"
                f"Saved to: {filename}\n\n"
                f"Share this with your accountant!"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export tax report:\n\n{str(e)}")
    
    def export_custom(self):
        """Export custom data based on user selection"""
        export_type = self.export_type_combo.currentText()
        year = self.year_filter_combo.currentData()
        
        if "All Data" in export_type:
            # Export everything
            self.export_inventory_report()
            self.export_expense_report()
            self.export_sales_report()
        elif "Inventory" in export_type:
            self.export_inventory_report()
        elif "Expenses" in export_type:
            self.export_expense_report()
        elif "Sales" in export_type:
            self.export_sales_report()
        elif "Active Listings" in export_type:
            self.export_filtered_inventory("Listed")
        elif "Sold Items" in export_type:
            self.export_filtered_inventory("Sold")
    
    def export_filtered_inventory(self, status):
        """Export inventory filtered by status"""
        filename = self.get_save_filename(f"inventory_{status.lower()}")
        if not filename:
            return
        
        try:
            items = self.db.get_inventory_items(status=status)
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                writer.writerow([
                    'ID', 'Title', 'Brand', 'Condition', 'Purchase Cost',
                    'Listed Price', 'Sold Price', 'Status'
                ])
                
                for item in items:
                    writer.writerow([
                        item['id'], item['title'], item['brand'], item['condition'],
                        item['purchase_cost'], item['listed_price'], item['sold_price'],
                        item['status']
                    ])
            
            self.log_export(f"{status} Inventory: {len(items)} items")
            QMessageBox.information(
                self, "Export Complete",
                f"Exported {len(items)} {status} items to:\n{filename}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export:\n\n{str(e)}")
    
    def load_analytics(self):
        """Load and display business analytics"""
        try:
            current_year = datetime.now().year
            
            # Get data
            revenue = self.db.get_total_revenue(current_year)
            expenses = self.db.get_total_deductible_expenses(current_year)
            profit = self.db.get_total_profit(current_year)
            inventory_value = self.db.get_inventory_value()
            
            inventory_items = self.db.get_inventory_items()
            in_stock = len([i for i in inventory_items if i['status'] == 'In Stock'])
            listed = len([i for i in inventory_items if i['status'] == 'Listed'])
            sold = len([i for i in inventory_items if i['status'] == 'Sold'])
            
            # Calculate metrics
            profit_margin = (profit / revenue * 100) if revenue > 0 else 0
            avg_sale_price = revenue / sold if sold > 0 else 0
            avg_profit_per_sale = profit / sold if sold > 0 else 0
            
            # Expense breakdown
            expense_breakdown = self.db.get_expense_breakdown(current_year)
            top_expenses = sorted(expense_breakdown, key=lambda x: x['total'], reverse=True)[:3]
            
            analytics_html = f"""
<h3 style="color: #2196F3;">Business Analytics - {current_year}</h3>

<h4>Revenue & Profit:</h4>
<table width="100%">
<tr><td><b>Total Revenue:</b></td><td align="right">${revenue:,.2f}</td></tr>
<tr><td><b>Total Expenses:</b></td><td align="right">${expenses:,.2f}</td></tr>
<tr><td><b>Net Profit:</b></td><td align="right" style="color: {'green' if profit > 0 else 'red'}"><b>${profit:,.2f}</b></td></tr>
<tr><td><b>Profit Margin:</b></td><td align="right"><b>{profit_margin:.1f}%</b></td></tr>
</table>

<h4>Inventory:</h4>
<table width="100%">
<tr><td>In Stock:</td><td align="right">{in_stock} items</td></tr>
<tr><td>Listed on eBay:</td><td align="right">{listed} items</td></tr>
<tr><td>Sold:</td><td align="right">{sold} items</td></tr>
<tr><td><b>Total Inventory Value:</b></td><td align="right"><b>${inventory_value:,.2f}</b></td></tr>
</table>

<h4>Sales Metrics:</h4>
<table width="100%">
<tr><td>Avg Sale Price:</td><td align="right">${avg_sale_price:.2f}</td></tr>
<tr><td>Avg Profit/Sale:</td><td align="right">${avg_profit_per_sale:.2f}</td></tr>
</table>

<h4>Top Expense Categories:</h4>
<ul>
{"".join([f"<li>{cat['category']}: ${cat['total']:,.2f}</li>" for cat in top_expenses[:3]])}
</ul>
            """
            
            self.analytics_display.setHtml(analytics_html)
            
        except Exception as e:
            self.analytics_display.setText(f"Error loading analytics: {str(e)}")
    
    def get_save_filename(self, default_name):
        """Get filename for saving export"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{default_name}_{timestamp}.csv"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Export",
            default_filename,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        return filename
    
    def log_export(self, message):
        """Add message to export log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.export_log.append(f"[{timestamp}] {message}")
    
    def refresh_data(self):
        """Refresh tab data"""
        self.load_analytics()
