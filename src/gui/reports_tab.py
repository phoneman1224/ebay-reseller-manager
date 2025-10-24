# src/gui/reports_tab.py
from __future__ import annotations

import os
import csv
import datetime
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QFormLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QCheckBox, QFileDialog,
    QMessageBox, QSizePolicy
)


class ReportsTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    # ------------------------------ UI

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        # LEFT
        quick_group = self._build_quick_reports_group()
        analytics_group = self._build_business_analytics_group()

        grid.addWidget(quick_group,     0, 0)
        grid.addWidget(analytics_group, 1, 0)

        # RIGHT
        custom_group = self._build_custom_export_group()
        log_group    = self._build_export_log_group()

        grid.addWidget(custom_group, 0, 1)
        grid.addWidget(log_group,    1, 1)

        layout.addLayout(grid)
        self.load_analytics()

    def _btn_style(self) -> str:
        return (
            "QPushButton {"
            "  background-color: #1976D2; color: white; padding: 8px 10px;"
            "  border: none; border-radius: 4px; font-size: 14px;}"
            "QPushButton:hover { background-color: #1565C0; }"
            "QPushButton:pressed { background-color: #0D47A1; }"
        )

    def _secondary_btn_style(self) -> str:
        return (
            "QPushButton {"
            "  background-color: #4CAF50; color: white; padding: 8px 10px;"
            "  border: none; border-radius: 4px; font-size: 14px;}"
            "QPushButton:hover { background-color: #43A047; }"
            "QPushButton:pressed { background-color: #2E7D32; }"
        )

    # ------------------------------ Groups (left/right columns)

    def _build_quick_reports_group(self) -> QGroupBox:
        g = QGroupBox("Quick Reports")
        g.setStyleSheet("QGroupBox{font-size:13px;margin-top:6px;}QGroupBox::title{left:6px;padding:2px 4px;}")
        v = QVBoxLayout(g); v.setContentsMargins(8,6,8,6); v.setSpacing(6)

        btn_inv = QPushButton("📦 Export Inventory Report")
        btn_inv.setStyleSheet(self._btn_style())
        btn_inv.clicked.connect(self.export_inventory_report)

        btn_exp = QPushButton("💵 Export Expense Report")
        btn_exp.setStyleSheet(self._btn_style())
        btn_exp.clicked.connect(self.export_expense_report)

        v.addWidget(btn_inv)
        v.addWidget(btn_exp)
        v.addStretch(1)
        return g

    def _build_business_analytics_group(self) -> QGroupBox:
        g = QGroupBox("Business Analytics")
        g.setStyleSheet("QGroupBox{font-size:13px;margin-top:6px;}QGroupBox::title{left:6px;padding:2px 4px;}")
        v = QVBoxLayout(g); v.setContentsMargins(8,6,8,6); v.setSpacing(6)
        self.analytics_box = QTextEdit(); self.analytics_box.setReadOnly(True)
        self.analytics_box.setMinimumHeight(120)
        v.addWidget(self.analytics_box)
        return g

    def _build_custom_export_group(self) -> QGroupBox:
        g = QGroupBox("Custom Export")
        g.setStyleSheet("QGroupBox{font-size:13px;margin-top:6px;}QGroupBox::title{left:6px;padding:2px 4px;}")
        f = QFormLayout(g); f.setContentsMargins(8,6,8,6); f.setSpacing(6)

        self.custom_path_edit = QLineEdit()
        self.custom_path_edit.setPlaceholderText("Choose where to save the custom CSV…")
        choose_btn = QPushButton("Browse…"); choose_btn.setStyleSheet(self._btn_style())
        choose_btn.clicked.connect(self._browse_custom_save)

        row = QWidget(); rowl = QHBoxLayout(row); rowl.setContentsMargins(0,0,0,0); rowl.setSpacing(6)
        rowl.addWidget(self.custom_path_edit); rowl.addWidget(choose_btn)
        f.addRow("Output file:", row)

        export_btn = QPushButton("📥 Export Custom Data")
        export_btn.setStyleSheet(self._secondary_btn_style())
        export_btn.clicked.connect(self.export_custom)
        f.addRow("", export_btn)
        return g

    def _build_export_log_group(self) -> QGroupBox:
        g = QGroupBox("Export Log")
        g.setStyleSheet("QGroupBox{font-size:13px;margin-top:6px;}QGroupBox::title{left:6px;padding:2px 4px;}")
        v = QVBoxLayout(g); v.setContentsMargins(8,6,8,6); v.setSpacing(6)
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True); self.log_view.setMinimumHeight(100)
        v.addWidget(self.log_view)
        return g

    # ------------------------------ Actions

    def log(self, msg: str):
        try:
            self.log_view.append(msg)
        except Exception:
            pass

    # Quick reports
    def export_inventory_report(self):
        try:
            items = self.db.get_inventory_items() if hasattr(self.db, "get_inventory_items") else []
            if not items:
                QMessageBox.information(self, "No Data", "No inventory items found.")
                return
            path, _ = QFileDialog.getSaveFileName(self, "Save Inventory Report", "inventory_report.csv", "CSV Files (*.csv)")
            if not path: return
            keys = [k for k in items[0].keys()]
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
                for r in items: w.writerow(dict(r))
            self.log(f"Inventory report exported to: {path}")
            QMessageBox.information(self, "Exported", f"Inventory report saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    def export_expense_report(self):
        try:
            rows = self.db.get_expenses() if hasattr(self.db, "get_expenses") else []
            if not rows:
                QMessageBox.information(self, "No Data", "No expenses found."); return
            path, _ = QFileDialog.getSaveFileName(self, "Save Expense Report", "expense_report.csv", "CSV Files (*.csv)")
            if not path: return
            keys = [k for k in rows[0].keys()]
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
                for r in rows: w.writerow(dict(r))
            self.log(f"Expense report exported to: {path}")
            QMessageBox.information(self, "Exported", f"Expense report saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    # Custom export
    def _browse_custom_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Custom Export", "custom_export.csv", "CSV Files (*.csv)")
        if path: self.custom_path_edit.setText(path)

    def export_custom(self):
        path = self.custom_path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "Choose file", "Please choose an output file.")
            return
        try:
            rows = []
            if hasattr(self.db, "get_inventory_items"):
                rows += [dict(r) for r in self.db.get_inventory_items()]
            if hasattr(self.db, "get_expenses"):
                rows += [dict(r) for r in self.db.get_expenses()]
            if not rows:
                QMessageBox.information(self, "No Data", "Nothing to export."); return
            keys = sorted({k for r in rows for k in r.keys()})
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
                for r in rows: w.writerow(r)
            self.log(f"Custom export saved to: {path}")
            QMessageBox.information(self, "Exported", f"Custom export saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    # Analytics
    def load_analytics(self):
        try:
            inv_count = len(self.db.get_inventory_items()) if hasattr(self.db, "get_inventory_items") else 0
            exp_count = len(self.db.get_expenses()) if hasattr(self.db, "get_expenses") else 0
            self.analytics_box.setPlainText(
                f"Inventory items: {inv_count}\n"
                f"Expense records: {exp_count}\n"
                f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception:
            self.analytics_box.setPlainText("Analytics unavailable.")
