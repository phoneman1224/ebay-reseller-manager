# src/gui/reports_tab.py
from __future__ import annotations

import os
import csv
import datetime
from typing import Optional, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QFormLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QCheckBox, QFileDialog,
    QMessageBox, QSizePolicy
)

# Optional mapping editor (ok if missing)
try:
    from .import_mapping_dialog import ImportMappingDialog
    HAVE_MAPPING_DIALOG = True
except Exception:
    HAVE_MAPPING_DIALOG = False

# New item selector dialog (we add this file below)
try:
    from .draft_select_dialog import DraftSelectDialog
    HAVE_SELECT_DIALOG = True
except Exception:
    HAVE_SELECT_DIALOG = False


class ReportsTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._selected_item_ids: List[int] = []
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
        import_group = self._build_ebay_import_group(compact=True)  # MOVED LEFT

        grid.addWidget(quick_group,     0, 0)
        grid.addWidget(analytics_group, 1, 0)
        grid.addWidget(import_group,    2, 0)

        # RIGHT
        custom_group = self._build_custom_export_group()
        log_group    = self._build_export_log_group()
        draft_group  = self._build_ebay_drafts_group(compact=True)

        grid.addWidget(custom_group, 0, 1)
        grid.addWidget(log_group,    1, 1)
        grid.addWidget(draft_group,  2, 1)

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

    def _build_ebay_import_group(self, compact: bool=False) -> QGroupBox:
        title = "eBay Import (Database-Normalized)"
        g = QGroupBox(title)
        g.setStyleSheet("QGroupBox{font-size:13px;margin-top:6px;}QGroupBox::title{left:6px;padding:2px 4px;}")
        f = QFormLayout(g); f.setContentsMargins(8,6,8,6); f.setVerticalSpacing(6); f.setHorizontalSpacing(8)

        self.ebay_csv_path = QLineEdit()
        self.ebay_csv_path.setPlaceholderText("Select any eBay CSV (Active, Orders, etc.)")
        browse = QPushButton("Browse…"); browse.setStyleSheet(self._btn_style()); browse.clicked.connect(self.browse_ebay_csv)

        rowp = QWidget(); rpl = QHBoxLayout(rowp); rpl.setContentsMargins(0,0,0,0); rpl.setSpacing(6)
        rpl.addWidget(self.ebay_csv_path); rpl.addWidget(browse)
        f.addRow("CSV file:", rowp)

        self.chk_dry = QCheckBox("Dry run (preview only)"); self.chk_dry.setChecked(True)
        f.addRow("", self.chk_dry)

        # Vertical stack so nothing squishes
        self.btn_detect = QPushButton("Detect & Preview"); self.btn_detect.setMinimumHeight(32)
        self.btn_detect.setStyleSheet(self._btn_style()); self.btn_detect.clicked.connect(self.preview_import)
        f.addRow(self.btn_detect)

        self.btn_import = QPushButton("Import Now"); self.btn_import.setMinimumHeight(32)
        self.btn_import.setStyleSheet(self._btn_style()); self.btn_import.clicked.connect(self.execute_import)
        f.addRow(self.btn_import)

        self.btn_mapping = QPushButton("Edit Mapping…"); self.btn_mapping.setMinimumHeight(32)
        self.btn_mapping.setStyleSheet(self._btn_style()); self.btn_mapping.clicked.connect(self.edit_mapping)
        self.btn_mapping.setEnabled(HAVE_MAPPING_DIALOG)
        f.addRow(self.btn_mapping)

        self.preview_box = QTextEdit(); self.preview_box.setReadOnly(True)
        self.preview_box.setFixedHeight(150)   # bigger so you can actually see rows
        f.addRow("Preview:", self.preview_box)

        if compact:
            g.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        return g

    def _build_ebay_drafts_group(self, compact: bool=False) -> QGroupBox:
        g = QGroupBox("eBay Draft Listings")
        g.setStyleSheet("QGroupBox{font-size:13px;margin-top:6px;}QGroupBox::title{left:6px;padding:2px 4px;}")
        f = QFormLayout(g); f.setContentsMargins(8,6,8,6); f.setVerticalSpacing(6); f.setHorizontalSpacing(8)

        self.category_id_edit = QLineEdit(); self.category_id_edit.setPlaceholderText("Default Category ID (e.g., 47140)")
        try:
            settings = self.db.get_import_settings()
            default_cat = settings.get("default_category_id")
            if default_cat: self.category_id_edit.setText(str(default_cat))
        except Exception:
            pass
        f.addRow("Category ID:", self.category_id_edit)

        # NEW: select items button
        self.btn_select = QPushButton("Select Items…")
        self.btn_select.setStyleSheet(self._btn_style())
        self.btn_select.clicked.connect(self.open_item_selector)
        f.addRow(self.btn_select)

        # Generate drafts from selected (or all unsold if none selected)
        self.btn_generate = QPushButton("Generate Drafts")
        self.btn_generate.setMinimumHeight(32)
        self.btn_generate.setStyleSheet(self._secondary_btn_style())
        self.btn_generate.clicked.connect(self.generate_drafts_clicked)
        f.addRow(self.btn_generate)

        if compact:
            g.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
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

    # eBay Import
    def browse_ebay_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select eBay CSV", "", "CSV Files (*.csv)")
        if path: self.ebay_csv_path.setText(path)

    def preview_import(self):
        path = self.ebay_csv_path.text().strip()
        if not path: return QMessageBox.warning(self, "Choose file", "Please select an eBay CSV.")
        if not hasattr(self.db, "normalize_csv_file"):
            return QMessageBox.warning(self, "Not available", "Database normalize method not found.")
        try:
            res = self.db.normalize_csv_file(path, report_type=None, dry_run=True)
            rtype = res.get("report_type"); rows = res.get("normalized_rows", []); warns = res.get("warnings", [])
            self.preview_box.clear()
            self.preview_box.append(f"Detected report type: {rtype or 'Unknown'}")
            self.preview_box.append(f"Rows parsed: {len(rows)}")
            if warns:
                self.preview_box.append("Warnings:")
                for w in warns[:10]: self.preview_box.append(f"  - {w}")
            for i, r in enumerate(rows[:10]):  # show more lines now
                self.preview_box.append(f"{i+1}. {r}")
        except Exception as e:
            QMessageBox.critical(self, "Preview failed", str(e))

    def execute_import(self):
        path = self.ebay_csv_path.text().strip()
        if not path: return QMessageBox.warning(self, "Choose file", "Please select an eBay CSV.")
        if not (hasattr(self.db, "normalize_csv_file") and hasattr(self.db, "import_normalized")):
            return QMessageBox.warning(self, "Not available", "Import/normalize methods not found.")
        try:
            res = self.db.normalize_csv_file(path, report_type=None, dry_run=True)
            rtype = res.get("report_type"); rows = res.get("normalized_rows", [])
            if not rtype: return QMessageBox.warning(self, "Unknown type", "Could not detect report type. Adjust mapping and try again.")
            if not rows:  return QMessageBox.warning(self, "No rows", "No rows were parsed. Check mapping.")
            stats = self.db.import_normalized(rtype, rows)
            self.preview_box.append(f"Imported: {stats}")
            QMessageBox.information(self, "Done", f"Import completed.\n{stats}")
            # refresh tabs if available
            for path_attr in ("inventory_tab", "sold_items_tab"):
                try:
                    getattr(self.parent().parent(), path_attr).refresh_data()
                except Exception:
                    pass
            self.load_analytics()
        except Exception as e:
            QMessageBox.critical(self, "Import failed", str(e))

    def edit_mapping(self):
        if not HAVE_MAPPING_DIALOG:
            return QMessageBox.information(self, "Mapping Editor", "Mapping dialog isn’t installed in this build.")
        ImportMappingDialog(self.db, self).exec()

    # eBay Drafts
    def open_item_selector(self):
        if not HAVE_SELECT_DIALOG or not hasattr(self.db, "get_inventory_items"):
            return QMessageBox.information(self, "Not available", "Item selector or inventory API not available.")
        items = self.db.get_inventory_items()
        dlg = DraftSelectDialog(items, parent=self)
        if dlg.exec():
            self._selected_item_ids = dlg.selected_ids()

    def generate_drafts_clicked(self):
        if not hasattr(self.db, "get_inventory_items"):
            return QMessageBox.warning(self, "Not available", "Inventory API not found.")
        try:
            items = [dict(r) for r in self.db.get_inventory_items()]
        except Exception as e:
            return QMessageBox.critical(self, "Error", f"Could not read inventory: {e}")

        # Decide which records to include
        selected_ids = set(self._selected_item_ids or [])
        rows = []
        for r in items:
            status = (r.get("status") or "").lower()
            if selected_ids:
                if r.get("id") not in selected_ids:
                    continue
            else:
                if status == "sold":
                    continue  # default: only unsold if no selection
            rows.append(r)

        if not rows:
            return QMessageBox.information(self, "Nothing to export", "No matching items to include.")

        out_path, _ = QFileDialog.getSaveFileName(self, "Save eBay Draft CSV", "ebay-drafts-for-upload.csv", "CSV Files (*.csv)")
        if not out_path:
            return

        cat_id = self.category_id_edit.text().strip() or "47140"

        info_rows = [
            ["#INFO","Version=0.0.2","Template= eBay-draft-listings-template_US","","","","","","",""],
            ["#INFO","Action and Category ID are required: set Action='Draft' + valid Category ID","","","","","","","","",""],
            ["#INFO","Complete drafts: https://www.ebay.com/sh/lst/drafts","","","","","","","","",""],
            ["#INFO","","","","","","","","",""],
        ]
        header = [
            "Action(SiteID=US|Country=US|Currency=USD|Version=1193|CC=UTF-8)",
            "Custom label (SKU)","Category ID","Title","UPC","Price","Quantity",
            "Item photo URL","Condition ID","Description","Format"
        ]
        cond_map = {
            "New": 1000, "New with tags": 1000, "New other": 1500, "Open box": 1500, "New (other)":1500,
            "Manufacturer refurbished": 2000, "Seller refurbished": 2500, "Used": 3000,
            "Good": 3000, "Very Good": 3000, "Acceptable": 3000, "For parts or not working": 7000
        }
        def to_cond_id(s: Optional[str]) -> str:
            return str(cond_map.get((s or "Used").strip(), 3000))
        def pick_price(row) -> str:
            for k in ("listed_price","price","purchase_price","cost"):
                if k in row and row[k] not in (None,""):
                    try: return str(float(row[k]))
                    except Exception: return str(row[k])
            return ""

        out_rows = []
        for r in rows:
            out_rows.append([
                "Draft",
                r.get("sku",""),
                r.get("category_id", cat_id) or cat_id,
                r.get("title",""),
                r.get("upc",""),
                pick_price(r),
                r.get("quantity", 1) or 1,
                r.get("image_url",""),
                to_cond_id(r.get("condition","Used")),
                r.get("description",""),
                "FixedPrice"
            ])

        try:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f); w.writerows(info_rows); w.writerow(header); w.writerows(out_rows)
            QMessageBox.information(self, "Drafts created", f"Wrote {len(out_rows)} draft rows to:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Write failed", str(e))
