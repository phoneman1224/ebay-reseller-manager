"""
Main Window for eBay Reseller Manager
FIXED VERSION - Added missing Pricing Tab
"""
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QLabel, QStatusBar, QMessageBox, QApplication, QDialog)
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
from gui.draft_listings_tab import DraftListingsTab


class MainWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("eBay Reseller Manager")
        self.setGeometry(100, 100, 1200, 800)  # Reasonable size, not huge
        self.setMinimumSize(1000, 700)
        
        # Create menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        settings_action = file_menu.addAction("⚙️ Settings")
        settings_action.triggered.connect(self.open_settings)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        
        # Create tabs with error handling
        try:
            self.dashboard_tab = DashboardTab(self.db)
        except Exception as e:
            print(f"Error creating Dashboard tab: {e}")
            self.dashboard_tab = QWidget()  # Fallback empty widget
        
        try:
            self.inventory_tab = InventoryTab(self.db)
        except Exception as e:
            print(f"Error creating Inventory tab: {e}")
            self.inventory_tab = QWidget()
        
        try:
            self.expenses_tab = ExpensesTab(self.db)
        except Exception as e:
            print(f"Error creating Expenses tab: {e}")
            self.expenses_tab = QWidget()
        
        try:
            self.pricing_tab = PricingTab(self.db)  # FIXED: Added missing tab
        except Exception as e:
            print(f"Error creating Pricing tab: {e}")
            self.pricing_tab = QWidget()
        
        try:
            self.sold_items_tab = SoldItemsTab(self.db)
        except Exception as e:
            print(f"Error creating Sold Items tab: {e}")
            self.sold_items_tab = QWidget()
        
        try:
            self.reports_tab = ReportsTab(self.db)
        except Exception as e:
            print(f"Error creating Reports tab: {e}")
            self.reports_tab = QWidget()
        
        try:
            self.draft_listings_tab = DraftListingsTab(self.db)
        except Exception as e:
            print(f"Error creating Draft Listings tab: {e}")
            self.draft_listings_tab = QWidget()
        
        # Add tabs
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.tabs.addTab(self.inventory_tab, "📦 Inventory")
        self.tabs.addTab(self.expenses_tab, "💵 Expenses")
        self.tabs.addTab(self.pricing_tab, "🏷️ Price Calculator")  # FIXED: Added missing tab
        self.tabs.addTab(self.sold_items_tab, "💰 Sold Items")
        self.tabs.addTab(self.draft_listings_tab, "📝 Draft Listings")
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
                color: #333333; /* Dark tab text for readability */
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0066cc;
                color: #333333; /* Maintain dark text on selected tab */
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
                color: #333333; /* Ensure text is dark on a light background */
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, 
            QDoubleSpinBox:focus, QComboBox:focus {
                border: 2px solid #0066cc;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #e0e0e0;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #666;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 2px solid #cccccc;
                selection-background-color: #0066cc;
                selection-color: #ffffff;
                outline: 0px;
                show-decoration-selected: 1;
            }
            QComboBox QListView {
                background-color: #ffffff;
                border: none;
                outline: 0px;
            }
            QComboBox QListView::item {
                height: 28px;
                padding-left: 10px;
                padding-right: 10px;
                background-color: #ffffff;
                color: #000000;
                border: none;
            }
            QComboBox QListView::item:hover {
                background-color: #bbdefb;
                color: #000000;
            }
            QComboBox QListView::item:selected {
                background-color: #0066cc;
                color: #ffffff;
            }
            QComboBox QListView::item:selected:hover {
                background-color: #0052a3;
                color: #ffffff;
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
        try:
            current_tab = self.tabs.widget(index)
            
            # Refresh dashboard when switched to
            if isinstance(current_tab, DashboardTab):
                if hasattr(current_tab, 'refresh_dashboard'):
                    current_tab.refresh_dashboard()
                elif hasattr(current_tab, 'refresh_data'):
                    current_tab.refresh_data()
            
            # Refresh sold items when switched to
            elif isinstance(current_tab, SoldItemsTab):
                if hasattr(current_tab, 'load_sold_items'):
                    current_tab.load_sold_items()
            
            # Refresh inventory when switched to
            elif isinstance(current_tab, InventoryTab):
                if hasattr(current_tab, 'load_inventory'):
                    current_tab.load_inventory()
            
            # Refresh expenses when switched to
            elif isinstance(current_tab, ExpensesTab):
                if hasattr(current_tab, 'load_expenses'):
                    current_tab.load_expenses()
            
            # FIXED: Refresh pricing tab when switched to
            elif isinstance(current_tab, PricingTab):
                if hasattr(current_tab, 'load_inventory_items'):
                    current_tab.load_inventory_items()
            
            # Refresh reports when switched to
            elif isinstance(current_tab, ReportsTab):
                if hasattr(current_tab, 'generate_report'):
                    current_tab.generate_report()
            
            # Refresh draft listings when switched to
            elif isinstance(current_tab, DraftListingsTab):
                if hasattr(current_tab, 'load_inventory'):
                    current_tab.load_inventory()
        except Exception as e:
            # Silently ignore tab refresh errors to prevent crashes
            print(f"Warning: Error refreshing tab: {e}")
    
    def show_message(self, title, message, icon=QMessageBox.Icon.Information):
        """Show a message box"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.exec()
    
    def open_settings(self):
        """Open the settings dialog"""
        from gui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh all tabs to apply new settings
            self.refresh_all_tabs()
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About eBay Reseller Manager",
            "<h2>eBay Reseller Manager</h2>"
            "<p>Version 2.0</p>"
            "<p>A comprehensive business management tool for eBay resellers.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Inventory Management</li>"
            "<li>Expense Tracking</li>"
            "<li>Pricing Calculator</li>"
            "<li>Sales Analytics</li>"
            "<li>eBay CSV Import/Export</li>"
            "<li>Draft Listings Generator</li>"
            "<li>Lot Listing Creator</li>"
            "</ul>"
            "<p>Built with Python & PyQt6</p>"
        )
    
    def refresh_all_tabs(self):
        """Refresh all tabs to apply new settings"""
        try:
            # Refresh each tab
            if hasattr(self.dashboard_tab, 'refresh_dashboard'):
                self.dashboard_tab.refresh_dashboard()
            elif hasattr(self.dashboard_tab, 'refresh_data'):
                self.dashboard_tab.refresh_data()
            
            if hasattr(self.inventory_tab, 'load_inventory'):
                self.inventory_tab.load_inventory()
            
            if hasattr(self.expenses_tab, 'load_expenses'):
                self.expenses_tab.load_expenses()
            
            if hasattr(self.sold_items_tab, 'load_sold_items'):
                self.sold_items_tab.load_sold_items()
            
            if hasattr(self.draft_listings_tab, 'load_inventory'):
                self.draft_listings_tab.load_inventory()
        except Exception as e:
            print(f"Error refreshing tabs: {e}")
    
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
