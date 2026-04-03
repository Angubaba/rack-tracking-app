"""Verification popup shown before recording a TH scan."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from utils import to_ist


class THVerifyDialog(QDialog):
    """
    Shows the OK scan details for the scanned rack and collects 'Taken By'.
    After accept(), read self.taken_by.
    """

    def __init__(self, ok_scan, parent=None):
        super().__init__(parent)
        self._ok_scan = ok_scan
        self.taken_by = ""
        self.setWindowTitle("Verify  —  Send Rack to TH")
        self.setMinimumWidth(460)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 16, 20, 16)

        # Title
        title = QLabel("Confirm Rack Details")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        root.addWidget(title)

        # Details card
        card = QFrame()
        card.setStyleSheet("QFrame{background-color:#f1f3f5;border-radius:8px;border:1px solid #dee2e6;}")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(14, 10, 14, 10)
        card_lay.setSpacing(6)

        fields = [
            ("Rack Number",  self._ok_scan["rack_number"]),
            ("Model",        self._ok_scan["model"]),
            ("Quantity",     str(self._ok_scan["quantity"])),
            ("Inspected By", self._ok_scan["inspected_by"]),
            ("In FG Since",  to_ist(self._ok_scan["created_at"])),
        ]
        for label, value in fields:
            row = QHBoxLayout()
            lbl = QLabel(f"{label}:")
            lbl.setFixedWidth(120)
            lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            val = QLabel(value)
            val.setFont(QFont("Segoe UI", 11))
            val.setStyleSheet("color:#212529;")
            row.addWidget(lbl)
            row.addWidget(val)
            row.addStretch()
            card_lay.addLayout(row)

        root.addWidget(card)

        # Taken By input
        taken_row = QHBoxLayout()
        taken_lbl = QLabel("TAKEN BY:")
        taken_lbl.setFixedWidth(120)
        taken_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.taken_input = QLineEdit()
        self.taken_input.setPlaceholderText("Name of person taking the rack…")
        self.taken_input.setFont(QFont("Segoe UI", 13))
        self.taken_input.setMinimumHeight(40)
        self.taken_input.returnPressed.connect(self._on_confirm)
        taken_row.addWidget(taken_lbl)
        taken_row.addWidget(self.taken_input, 1)
        root.addLayout(taken_row)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color:#c92a2a;")
        root.addWidget(self._error_label)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(42)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setFont(QFont("Segoe UI", 11))
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("Confirm — Send to TH")
        confirm_btn.setMinimumHeight(42)
        confirm_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        confirm_btn.setStyleSheet(
            "background-color:#1971c2;color:#ffffff;border-radius:5px;padding:0 16px;"
        )
        confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(confirm_btn)
        root.addLayout(btn_row)

        self.taken_input.setFocus()

    def _on_confirm(self):
        taken_by = self.taken_input.text().strip().upper()
        if not taken_by:
            self._error_label.setText("Taken By is required.")
            return
        self.taken_by = taken_by
        self.accept()
