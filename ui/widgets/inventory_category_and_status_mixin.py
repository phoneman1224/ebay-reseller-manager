from PyQt6 import QtWidgets
from pathlib import Path
from services.category_service import CategoryService
from services.item_service import ItemService, VALID_STATUSES

class InventoryCategoryStatusMixin:
    def _init_category_status_ui(self, db_path: Path):
        self._db_path = Path(db_path)
        self._cat_svc = CategoryService(self._db_path)
        self._item_svc = ItemService(self._db_path)
        if not hasattr(self, 'combo_category'):
            self.combo_category = QtWidgets.QComboBox(self)
        if not hasattr(self, 'combo_status'):
            self.combo_status = QtWidgets.QComboBox(self)
        self.combo_status.clear()
        self.combo_status.addItems(VALID_STATUSES)
        self._populate_category_combo()

    def _populate_category_combo(self):
        self.combo_category.clear()
        rows = self._cat_svc.list_categories()
        for _, cat_id, name in rows:
            self.combo_category.addItem(f"{name} ({cat_id})", userData=cat_id)

    def load_item_into_form(self, item_row: tuple):
        if not item_row:
            return
        self._current_item_id = item_row[0]
        ebay_cat = item_row[5]
        status = item_row[6] or 'stocked'
        idx = self.combo_status.findText(status)
        if idx >= 0:
            self.combo_status.setCurrentIndex(idx)
        if ebay_cat is not None:
            for i in range(self.combo_category.count()):
                if self.combo_category.itemData(i) == ebay_cat:
                    self.combo_category.setCurrentIndex(i)
                    break

    def save_item_from_form(self):
        cat_id = self.combo_category.currentData()
        if getattr(self, '_current_item_id', None) and cat_id is not None:
            self._item_svc.set_category(self._current_item_id, int(cat_id))
        status = self.combo_status.currentText()
        if getattr(self, '_current_item_id', None) and status:
            self._item_svc.set_status(self._current_item_id, status)
