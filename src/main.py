#!/usr/bin/env python3
"""
eBay Reseller Manager
A comprehensive business management tool for eBay resellers

Main application entry point
"""
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from database import Database
from gui.main_window import MainWindow


def main():
    """Main application entry point"""
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("eBay Reseller Manager")
    app.setOrganizationName("eBay Reseller Tools")
    
    try:
        # Initialize database
        db = Database()
        
        # Create and show main window
        window = MainWindow(db)
        window.show()
        
        # Run application
        sys.exit(app.exec())
        
    except Exception as e:
        error_msg = QMessageBox()
        error_msg.setIcon(QMessageBox.Icon.Critical)
        error_msg.setWindowTitle("Application Error")
        error_msg.setText("An error occurred while starting the application:")
        error_msg.setInformativeText(str(e))
        error_msg.exec()
        sys.exit(1)


if __name__ == "__main__":
    main()
