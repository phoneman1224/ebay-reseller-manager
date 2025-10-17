"""
Main Window for eBay Reseller Manager
FIXED VERSION - Added missing Pricing Tab
"""
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QLabel, QStatusBar, QMessageBox, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import sys
import os

# Import tab widgets
from gui.dashboard_tab import DashboardTab
from gui.inventory_tab import InventoryTab
from gui.expenses_tab import ExpensesTab
from gui.pricing_tab import PricingTab  # FIXED: Added missing import
from gui.sold_items_tab import SoldItemsTab
from gui.reports_tab import ReportsTab


class MainWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("eBay Reseller Manager")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        
        # Create tabs
        self.dashboard_tab = DashboardTab(self.db)
        self.inventory_tab = InventoryTab(self.db)
        self.expenses_tab = ExpensesTab(self.db)
        self.pricing_tab = PricingTab(self.db)  # FIXED: Added missing tab
        self.sold_items_tab = SoldItemsTab(self.db)
        self.reports_tab = ReportsTab(self.db)
        
        # Add tabs
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.tabs.addTab(self.inventory_tab, "📦 Inventory")
        self.tabs.addTab(self.expenses_tab, "💵 Expenses")
        self.tabs.addTab(self.pricing_tab, "🏷️ Price Calculator")  # FIXED: Added missing tab
        self.tabs.addTab(self.sold_items_tab, "💰 Sold Items")
        self.tabs.addTab(self.reports_tab, "📈 Reports")
        
        # Connect tab change signal to refresh data
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tabs)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Apply styling
        self.apply_stylesheet()
        
        # FIXED: Start maximized properly
        self.showMaximized()
    
    def apply_stylesheet(self):
        """Apply custom stylesheet for better appearance"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0066cc;
            }
            QTabBar::tab:hover {
                background-color: #d0d0d0;
            }
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
            QPushButton:pressed {
                background-color: #003d7a;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, 
            QDoubleSpinBox:focus, QComboBox:focus {
                border: 2px solid #0066cc;
            }
            QTableWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                gridline-color: #e0e0e0;
                background-color: white;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #0066cc;
                color: white;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: none;
                border-right: 1px solid #cccccc;
                border-bottom: 1px solid #cccccc;
                font-weight: bold;
            }
        """)
    
    def on_tab_changed(self, index):
        """Handle tab changes to refresh data"""
        current_tab = self.tabs.widget(index)
        
        # Refresh dashboard when switched to
        if isinstance(current_tab, DashboardTab):
            current_tab.refresh_dashboard()
        
        # Refresh sold items when switched to
        elif isinstance(current_tab, SoldItemsTab):
            current_tab.load_sold_items()
        
        # Refresh inventory when switched to
        elif isinstance(current_tab, InventoryTab):
            current_tab.load_inventory()
        
        # Refresh expenses when switched to
        elif isinstance(current_tab, ExpensesTab):
            current_tab.load_expenses()
        
        # FIXED: Refresh pricing tab when switched to
        elif isinstance(current_tab, PricingTab):
            current_tab.load_inventory_items()
        
        # Refresh reports when switched to
        elif isinstance(current_tab, ReportsTab):
            current_tab.generate_report()
    
    def show_message(self, title, message, icon=QMessageBox.Icon.Information):
        """Show a message box"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.exec()
    
    def closeEvent(self, event):
        """Handle window close event"""
        reply = QMessageBox.question(
            self,
            'Confirm Exit',
            'Are you sure you want to exit?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Close database connection
            self.db.close()
            event.accept()
        else:
            event.ignore()
