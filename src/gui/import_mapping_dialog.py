"""
Import Mapping Dialog
----------------------

This dialog allows the user to view and edit the mappings from eBay report
column names to the internal fields used by the application. Mappings are
persisted in the database via the Database.get_mapping and
Database.update_mapping methods. Each mapping is stored as a JSON object
keyed by the report type ("active_listings", "orders", etc.).

The dialog presents a combo box to select the report type and a form where
each internal field can be mapped to one or more CSV column names. Multiple
CSV columns may be provided by separating names with the pipe character ('|')
to allow fallback values.

Usage::

    dlg = ImportMappingDialog(db)
    if dlg.exec():
        # Mappings are saved back to the database when the Save button is clicked
        pass
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QMessageBox,
    QLabel,
    QWidget,
    QHBoxLayout,
)


# Human‑readable names for report types and their internal identifiers
REPORT_TYPES = {
    "Active Listings": "active_listings",
    "Orders": "orders",
}

# Internal fields expected for each report type
FIELDS = {
    "active_listings": [
        "title",
        "sku",
        "condition",
        "listed_price",
        "listed_date",
    ],
    "orders": [
        "title",
        "sku",
        "sold_price",
        "sold_date",
        "quantity",
        "order_number",
    ],
}


class ImportMappingDialog(QDialog):
    """
    A dialog for viewing and editing column mappings for eBay report imports.

    The dialog fetches the current mapping from the database when a report
    type is selected and allows the user to edit the CSV column names used
    for each internal field. Changes are persisted back to the database via
    Database.update_mapping when the Save button is clicked.
    """

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("eBay Import Mapping")
        self.setMinimumWidth(450)
        self.rows = {}

        # Layout setup
        layout = QVBoxLayout(self)

        # Report type selection
        type_row = QHBoxLayout()
        type_label = QLabel("Report Type:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(REPORT_TYPES.keys())
        self.type_combo.currentIndexChanged.connect(self.load_current_mapping)
        type_row.addWidget(type_label)
        type_row.addWidget(self.type_combo)
        layout.addLayout(type_row)

        # Form layout for field mappings
        self.form = QFormLayout()
        form_container = QWidget()
        form_container.setLayout(self.form)
        layout.addWidget(form_container)

        # Save button
        save_btn = QPushButton("Save Mapping")
        save_btn.clicked.connect(self.save_mapping)
        layout.addWidget(save_btn)

        # Populate fields for the initial selection
        self.load_current_mapping()

    def load_current_mapping(self):
        """Load current mapping for the selected report type and populate the form."""
        # Determine selected report type identifier
        human = self.type_combo.currentText()
        rtype = REPORT_TYPES[human]
        mapping = self.db.get_mapping(rtype)
        # Clear any existing rows
        for i in reversed(range(self.form.rowCount())):
            self.form.removeRow(i)
        self.rows.clear()
        # Create a line edit for each field
        for field in FIELDS[rtype]:
            edit = QLineEdit(mapping.get(field, ""))
            edit.setPlaceholderText("CSV column name(s), use A|B for fallbacks")
            self.form.addRow(QLabel(field), edit)
            self.rows[field] = edit

    def save_mapping(self):
        """Collect values from the form and persist the mapping back to the database."""
        human = self.type_combo.currentText()
        rtype = REPORT_TYPES[human]
        new_mapping = {field: self.rows[field].text().strip() for field in FIELDS[rtype]}
        # At least one field must be mapped
        if not any(new_mapping.values()):
            QMessageBox.warning(self, "Empty Mapping", "Please provide at least one mapping value.")
            return
        self.db.update_mapping(rtype, new_mapping)
        QMessageBox.information(self, "Mapping Saved", f"Mapping for {human} saved successfully.")
        self.accept()