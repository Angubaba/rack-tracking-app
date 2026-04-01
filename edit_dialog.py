"""Shared dialog for editing an existing scan record."""
import sqlite3

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QPushButton, QDialogButtonBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import database
from utils import validate_rack_number


class EditScanDialog(QDialog):
    def __init__(self, scan_id: int, parent=None):
        super().__init__(parent)
        self._scan_id = scan_id
        self._original = database.get_scan_by_id(scan_id)
        if not self._original:
            raise ValueError(f"Scan id {scan_id} not found")

        self.setWindowTitle("Edit Scan Record")
        self.setMinimumWidth(440)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(18, 14, 18, 14)

        root.addWidget(self._row("RACK NUMBER:", self._make_rack_input()))
        root.addWidget(self._row("MODEL:", self._make_model_input()))
        root.addWidget(self._row("QUANTITY:", self._make_qty_input()))
        root.addWidget(self._row("INSPECTED BY:", self._make_inspector_input()))

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
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setStyleSheet(
            "background-color:#a6e3a1;color:#1e1e2e;font-weight:bold;"
            "border-radius:4px;padding:6px 18px;"
        )
        root.addWidget(buttons)

    def _row(self, label: str, widget) -> QWidget:
        from PyQt6.QtWidgets import QWidget
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFixedWidth(130)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lay.addWidget(lbl)
        lay.addWidget(widget, 1)
        return container

    def _make_rack_input(self) -> QLineEdit:
        self.rack_input = QLineEdit(self._original["rack_number"])
        self.rack_input.setFont(QFont("Segoe UI", 12))
        self.rack_input.setMinimumHeight(36)
        return self.rack_input

    def _make_model_input(self) -> QLineEdit:
        self.model_input = QLineEdit(self._original["model"])
        self.model_input.setFont(QFont("Segoe UI", 12))
        self.model_input.setMinimumHeight(36)
        return self.model_input

    def _make_qty_input(self) -> QSpinBox:
        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 10_000)
        self.qty_input.setValue(self._original["quantity"])
        self.qty_input.setFont(QFont("Segoe UI", 12))
        self.qty_input.setMinimumHeight(36)
        return self.qty_input

    def _make_inspector_input(self) -> QLineEdit:
        self.inspector_input = QLineEdit(self._original["inspected_by"])
        self.inspector_input.setFont(QFont("Segoe UI", 12))
        self.inspector_input.setMinimumHeight(36)
        return self.inspector_input

    def _on_save(self):
        rack_number  = self.rack_input.text().strip().upper()
        model        = self.model_input.text().strip().upper()
        quantity     = self.qty_input.value()
        inspected_by = self.inspector_input.text().strip().upper()

        if not rack_number:
            self._error_label.setText("Rack Number is required.")
            return
        if not validate_rack_number(rack_number):
            self._error_label.setText(
                "Invalid format. Expected PR/### or MR/### (e.g. PR/042)."
            )
            return
        if not model:
            self._error_label.setText("Model is required.")
            return
        if not inspected_by:
            self._error_label.setText("Inspected By is required.")
            return

        with database._connect() as conn:
            conn.execute(
                """UPDATE rack_scans
                   SET rack_number=?, model=?, quantity=?, inspected_by=?
                   WHERE id=?""",
                (rack_number, model, quantity, inspected_by, self._scan_id),
            )
            conn.commit()

        self.accept()
