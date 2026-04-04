from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QPushButton, QFrame,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

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
        root.setAlignment(Qt.AlignTop)

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        root.addWidget(title)

        root.addWidget(self._build_card(
            "Duplicate Block Window",
            "OK RACKS tab only",
            "Prevents the same rack from being scanned as OK more than once within this window.\n"
            "Hard block — operator cannot override.",
            "_dup_spin",
        ))

        root.addWidget(self._build_card(
            "Completion Lock Window",
            "GOING TO TH tab only",
            "If a rack was already sent to TH within this window, a confirmation dialog appears.\n"
            "Soft block — operator can override. Completely separate from the duplicate block.",
            "_lock_spin",
        ))

        save_btn = QPushButton("Save Settings")
        save_btn.setMinimumHeight(46)
        save_btn.setMinimumWidth(160)
        save_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        save_btn.setStyleSheet(
            "background-color:#2f9e44;color:#ffffff;border-radius:5px;"
        )
        save_btn.clicked.connect(self._on_save)

        self._status = QLabel("")
        self._status.setFont(QFont("Segoe UI", 11))

        btn_row = QHBoxLayout()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(self._status)
        btn_row.addStretch()
        root.addLayout(btn_row)

    def _build_card(self, title: str, tag: str, description: str, attr: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame{background-color:#f1f3f5;border-radius:8px;border:1px solid #dee2e6;}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 14)
        lay.setSpacing(4)

        hdr_row = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        tag_lbl = QLabel(f"  [{tag}]")
        tag_lbl.setFont(QFont("Segoe UI", 10))
        tag_lbl.setStyleSheet("color:#1971c2;")
        hdr_row.addWidget(lbl)
        hdr_row.addWidget(tag_lbl)
        hdr_row.addStretch()
        lay.addLayout(hdr_row)

        desc = QLabel(description)
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet("color:#6c757d;")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        spin_row = QHBoxLayout()
        spin = QSpinBox()
        spin.setRange(1, 1440)
        spin.setSuffix("  minutes")
        spin.setFont(QFont("Segoe UI", 13))
        spin.setMinimumHeight(40)
        spin.setFixedWidth(180)
        setattr(self, attr, spin)
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
        self._status.setText("Saved.")
        self._status.setStyleSheet("color:#2f9e44;font-weight:bold;")
