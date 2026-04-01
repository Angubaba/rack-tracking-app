"""Edit dialog for OK scans and TH scans."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QPushButton, QDialogButtonBox, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import database
from utils import validate_rack_number


class EditScanDialog(QDialog):
    """
    scan_type: 'ok' or 'th'
    For OK scans: edits rack_number, model, quantity, inspected_by.
    For TH scans: edits taken_by only (rest is immutable record).
    """

    def __init__(self, scan_type: str, scan_id: int, parent=None):
        super().__init__(parent)
        self._type = scan_type
        self._scan_id = scan_id
        if scan_type == "ok":
            self._original = database.get_ok_scan_by_id(scan_id)
        else:
            self._original = database.get_th_scan_by_id(scan_id)

        if not self._original:
            raise ValueError(f"Scan id {scan_id} not found in {scan_type}")

        self.setWindowTitle("Edit Scan Record")
        self.setMinimumWidth(440)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(18, 14, 18, 14)

        if self._type == "ok":
            self._rack_input = QLineEdit(self._original["rack_number"])
            self._rack_input.setFont(QFont("Segoe UI", 12))
            self._rack_input.setMinimumHeight(36)
            root.addWidget(self._field_row("RACK NUMBER:", self._rack_input))

            self._model_input = QLineEdit(self._original["model"])
            self._model_input.setFont(QFont("Segoe UI", 12))
            self._model_input.setMinimumHeight(36)
            root.addWidget(self._field_row("MODEL:", self._model_input))

            self._qty_input = QSpinBox()
            self._qty_input.setRange(1, 10_000)
            self._qty_input.setValue(self._original["quantity"])
            self._qty_input.setFont(QFont("Segoe UI", 12))
            self._qty_input.setMinimumHeight(36)
            root.addWidget(self._field_row("QUANTITY:", self._qty_input))

            self._inspector_input = QLineEdit(self._original["inspected_by"])
            self._inspector_input.setFont(QFont("Segoe UI", 12))
            self._inspector_input.setMinimumHeight(36)
            root.addWidget(self._field_row("INSPECTED BY:", self._inspector_input))

        else:  # TH — only taken_by is editable
            # Show read-only info
            for label, key in [
                ("Rack Number", "rack_number"), ("Model", "model"),
                ("Qty", "quantity"), ("Inspected By", "inspected_by"),
            ]:
                ro = QLineEdit(str(self._original[key]))
                ro.setReadOnly(True)
                ro.setFont(QFont("Segoe UI", 12))
                ro.setMinimumHeight(36)
                ro.setStyleSheet(
                    "QLineEdit{background-color:#181825;color:#6c7086;"
                    "border:1px solid #313244;border-radius:4px;padding:4px 8px;}"
                )
                root.addWidget(self._field_row(f"{label}:", ro))

            self._taken_input = QLineEdit(self._original["taken_by"])
            self._taken_input.setFont(QFont("Segoe UI", 12))
            self._taken_input.setMinimumHeight(36)
            root.addWidget(self._field_row("TAKEN BY:", self._taken_input))

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color:#f38ba8;")
        self._error_label.setWordWrap(True)
        root.addWidget(self._error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Save).setStyleSheet(
            "background-color:#a6e3a1;color:#1e1e2e;font-weight:bold;"
            "border-radius:4px;padding:6px 18px;"
        )
        root.addWidget(buttons)

    def _field_row(self, label: str, widget) -> QWidget:
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFixedWidth(130)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lay.addWidget(lbl)
        lay.addWidget(widget, 1)
        return container

    def _on_save(self):
        if self._type == "ok":
            rack_number  = self._rack_input.text().strip().upper()
            model        = self._model_input.text().strip().upper()
            quantity     = self._qty_input.value()
            inspected_by = self._inspector_input.text().strip().upper()

            if not rack_number:
                self._error_label.setText("Rack Number is required.")
                return
            if not validate_rack_number(rack_number):
                self._error_label.setText("Expected PR/### or MR/###.")
                return
            if not model:
                self._error_label.setText("Model is required.")
                return
            if not inspected_by:
                self._error_label.setText("Inspected By is required.")
                return

            with database._connect() as conn:
                conn.execute(
                    "UPDATE ok_scans SET rack_number=?, model=?, quantity=?, inspected_by=?"
                    " WHERE id=?",
                    (rack_number, model, quantity, inspected_by, self._scan_id),
                )
                # Mirror the same fields into the linked TH scan if one exists
                conn.execute(
                    "UPDATE th_scans SET rack_number=?, model=?, quantity=?, inspected_by=?"
                    " WHERE ok_scan_id=?",
                    (rack_number, model, quantity, inspected_by, self._scan_id),
                )
                conn.commit()

        else:
            taken_by = self._taken_input.text().strip().upper()
            if not taken_by:
                self._error_label.setText("Taken By is required.")
                return
            with database._connect() as conn:
                conn.execute(
                    "UPDATE th_scans SET taken_by=? WHERE id=?",
                    (taken_by, self._scan_id),
                )
                conn.commit()

        self.accept()
