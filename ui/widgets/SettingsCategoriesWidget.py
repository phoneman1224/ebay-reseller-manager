from PyQt6 import QtWidgets, QtCore
from typing import Optional
from pathlib import Path
from services.category_service import CategoryService

class SettingsCategoriesWidget(QtWidgets.QWidget):
    categoryAdded = QtCore.pyqtSignal()
    categoryDeleted = QtCore.pyqtSignal()

    def __init__(self, db_path: Path, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.svc = CategoryService(db_path)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        toolbar = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit(self)
        self.search_edit.setPlaceholderText('Search categories...')
        self.btn_search = QtWidgets.QPushButton('Search', self)
        self.btn_add = QtWidgets.QPushButton('Add / Update', self)
        self.btn_delete = QtWidgets.QPushButton('Delete', self)
        toolbar.addWidget(self.search_edit, 1)
        toolbar.addWidget(self.btn_search)
        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_delete)
        layout.addLayout(toolbar)
        form = QtWidgets.QFormLayout()
        self.input_cat_id = QtWidgets.QLineEdit(self)
        self.input_cat_name = QtWidgets.QLineEdit(self)
        form.addRow('eBay Category ID:', self.input_cat_id)
        form.addRow('Category Name:', self.input_cat_name)
        layout.addLayout(form)
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['RowId', 'Category ID', 'Name'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)
        self.btn_search.clicked.connect(self.on_search)
        self.btn_add.clicked.connect(self.on_add_update)
        self.btn_delete.clicked.connect(self.on_delete)
        self.table.itemSelectionChanged.connect(self.on_select_row)

    def refresh(self, query: Optional[str] = None):
        rows = self.svc.list_categories(query)
        self.table.setRowCount(len(rows))
        for r, (rowid, cat_id, name) in enumerate(rows):
            self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(rowid)))
            self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(cat_id)))
            self.table.setItem(r, 2, QtWidgets.QTableWidgetItem(name))

    def on_search(self):
        self.refresh(self.search_edit.text().strip() or None)

    def on_add_update(self):
        try:
            cat_id = int(self.input_cat_id.text().strip())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, 'Invalid', 'Category ID must be an integer.')
            return
        name = self.input_cat_name.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, 'Invalid', 'Category Name is required.')
            return
        self.svc.upsert_category(cat_id, name)
        self.refresh()
        self.categoryAdded.emit()

    def on_delete(self):
        items = self.table.selectedItems()
        if not items:
            return
        cat_id_item = self.table.item(self.table.currentRow(), 1)
        if not cat_id_item:
            return
        cat_id = int(cat_id_item.text())
        self.svc.delete_category(cat_id)
        self.refresh()
        self.categoryDeleted.emit()

    def on_select_row(self):
        row = self.table.currentRow()
        if row < 0:
            return
        cat_id_item = self.table.item(row, 1)
        name_item = self.table.item(row, 2)
        if cat_id_item and name_item:
            self.input_cat_id.setText(cat_id_item.text())
            self.input_cat_name.setText(name_item.text())
