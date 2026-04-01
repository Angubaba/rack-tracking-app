from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import settings


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 20, 24, 20)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Lock Settings")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        root.addWidget(title)

        root.addWidget(self._build_card(
            "Duplicate Block Window",
            "Blocks re-scanning the same Rack Number + Model combination "
            "within this window.\nThis is a hard block — cannot be overridden.",
            "minutes",
            1, 1440,
            lambda sb: setattr(self, "_dup_spin", sb),
            lambda: self._dup_spin,
        ))

        root.addWidget(self._build_card(
            "Completion Lock Window",
            "After any scan, the rack is soft-locked for this duration.\n"
            "A confirmation dialog is shown — operator can still override.",
            "minutes",
            1, 1440,
            lambda sb: setattr(self, "_lock_spin", sb),
            lambda: self._lock_spin,
        ))

        save_btn = QPushButton("Save Settings")
        save_btn.setMinimumHeight(46)
        save_btn.setMinimumWidth(160)
        save_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        save_btn.setStyleSheet(
            "background-color:#a6e3a1;color:#1e1e2e;border-radius:5px;"
        )
        save_btn.clicked.connect(self._on_save)

        self._status_label = QLabel("")
        self._status_label.setFont(QFont("Segoe UI", 11))

        btn_row = QHBoxLayout()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(self._status_label)
        btn_row.addStretch()
        root.addLayout(btn_row)

    def _build_card(
        self,
        title: str,
        description: str,
        unit: str,
        min_val: int,
        max_val: int,
        setter,
        getter,
    ) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame{background-color:#313244;border-radius:8px;}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 14)
        lay.setSpacing(6)

        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        desc = QLabel(description)
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet("color:#a6adc8;")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        spin_row = QHBoxLayout()
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSuffix(f"  {unit}")
        spin.setFont(QFont("Segoe UI", 13))
        spin.setMinimumHeight(40)
        spin.setFixedWidth(160)
        setter(spin)
        spin_row.addWidget(spin)
        spin_row.addStretch()
        lay.addLayout(spin_row)

        return card

    def _load(self):
        data = settings.load()
        self._dup_spin.setValue(data["duplicate_lock_minutes"])
        self._lock_spin.setValue(data["completion_lock_minutes"])

    def _on_save(self):
        settings.save({
            "duplicate_lock_minutes":  self._dup_spin.value(),
            "completion_lock_minutes": self._lock_spin.value(),
        })
        self._status_label.setText("Saved.")
        self._status_label.setStyleSheet("color:#a6e3a1;font-weight:bold;")
