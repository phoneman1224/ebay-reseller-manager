# src/gui/draft_select_dialog.py
from __future__ import annotations
from typing import List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QAbstractItemView
)
from PyQt6.QtCore import Qt

class DraftSelectDialog(QDialog):
    """
    Simple multi-select table with a filter box.
    Expects rows as list of dicts with keys: id, title, sku, status (if present).
    """
    def __init__(self, items: List[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Inventory Items")
        self.setMinimumSize(720, 420)
        self._items = [dict(r) for r in items]
        self._selected_ids: List[int] = []

        v = QVBoxLayout(self)

        # Filter
        top = QHBoxLayout()
        top.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Search title or SKU...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        top.addWidget(self.filter_edit)
        v.addLayout(top)

        # Table
        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["Select", "ID", "SKU", "Title"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.table)

        # Buttons
        btns = QHBoxLayout()
        self.btn_all = QPushButton("Select All")
        self.btn_none = QPushButton("Select None")
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_all.clicked.connect(self._select_all)
        self.btn_none.clicked.connect(self._select_none)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        for b in (self.btn_all, self.btn_none):
            btns.addWidget(b)
        btns.addStretch(1)
        for b in (self.btn_ok, self.btn_cancel):
            btns.addWidget(b)
        v.addLayout(btns)

        self._populate(self._items)

    def _populate(self, rows):
        self.table.setRowCount(0)
        for r in rows:
            rid = r.get("id")
            sku = r.get("sku","")
            title = r.get("title","")
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Checkbox cell using checkState on item
            chk = QTableWidgetItem("")
            chk.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
            chk.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, chk)

            id_cell = QTableWidgetItem("" if rid is None else str(rid))
            sku_cell = QTableWidgetItem(sku)
            title_cell = QTableWidgetItem(title)
            self.table.setItem(row, 1, id_cell)
            self.table.setItem(row, 2, sku_cell)
            self.table.setItem(row, 3, title_cell)

    def _apply_filter(self, text: str):
        q = (text or "").lower()
        if not q:
            self._populate(self._items); return
        filtered = []
        for r in self._items:
            if q in (r.get("title","").lower()) or q in (r.get("sku","").lower()):
                filtered.append(r)
        self._populate(filtered)

    def _select_all(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(Qt.CheckState.Checked)

    def _select_none(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)

    def selected_ids(self) -> List[int]:
        ids: List[int] = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                id_txt = self.table.item(row, 1).text().strip()
                if id_txt:
                    try:
                        ids.append(int(id_txt))
                    except Exception:
                        pass
        return ids

    def accept(self):
        self._selected_ids = self.selected_ids()
        super().accept()
