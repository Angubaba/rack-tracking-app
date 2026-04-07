"""Dialog for scanning PCB sample IDs before adding a rack to FG."""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QFrame, QAbstractItemView,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import database


class PCBSamplingDialog(QDialog):
    """
    Shown after OK scan validation passes.
    Inspector scans PCB IDs one at a time (barcode scanner friendly).
    Blocks PCB IDs already recorded for this rack in any prior OK scan.
    After accept(), read self.pcb_ids (may be empty if skipped).
    """

    def __init__(self, rack_number: str, parent=None):
        super().__init__(parent)
        self._rack_number = rack_number
        self.pcb_ids = []
        # Pre-load all PCBs ever recorded for this rack
        self._historic: set[str] = database.get_all_pcb_ids_for_rack(rack_number)
        self.setWindowTitle("Sample PCB IDs")
        self.setMinimumWidth(480)
        self.setMinimumHeight(420)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(20, 16, 20, 16)

        # Header
        title = QLabel("Enter PCB Sample IDs")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        root.addWidget(title)

        rack_lbl = QLabel(f"Rack: {self._rack_number}")
        rack_lbl.setFont(QFont("Segoe UI", 11))
        rack_lbl.setStyleSheet("color:#1971c2;font-weight:bold;")
        root.addWidget(rack_lbl)

        # Scan input row
        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Scan or type PCB ID, press Enter to add…")
        self._input.setFont(QFont("Segoe UI", 13))
        self._input.setMinimumHeight(42)
        self._input.returnPressed.connect(self._add)

        add_btn = QPushButton("Add")
        add_btn.setMinimumHeight(42)
        add_btn.setMinimumWidth(70)
        add_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        add_btn.setStyleSheet(
            "background-color:#1971c2;color:#ffffff;border-radius:4px;"
        )
        add_btn.clicked.connect(self._add)

        input_row.addWidget(self._input, 1)
        input_row.addWidget(add_btn)
        root.addLayout(input_row)

        self._dup_label = QLabel("")
        self._dup_label.setStyleSheet("color:#c92a2a;font-size:11px;")
        root.addWidget(self._dup_label)

        # List of scanned IDs
        self._count_label = QLabel("0 PCBs sampled")
        self._count_label.setFont(QFont("Segoe UI", 10))
        self._count_label.setStyleSheet("color:#6c757d;")
        root.addWidget(self._count_label)

        self._list = QListWidget()
        self._list.setFont(QFont("Segoe UI", 12))
        self._list.setAlternatingRowColors(True)
        self._list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        root.addWidget(self._list)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.setFont(QFont("Segoe UI", 10))
        remove_btn.setStyleSheet(
            "background-color:#c92a2a;color:#ffffff;border-radius:4px;padding:4px 12px;"
        )
        remove_btn.clicked.connect(self._remove_selected)
        root.addWidget(remove_btn)

        # Bottom buttons
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color:#c92a2a;font-size:11px;")
        root.addWidget(self._error_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        confirm_btn = QPushButton("Confirm & Add to FG")
        confirm_btn.setMinimumHeight(42)
        confirm_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        confirm_btn.setStyleSheet(
            "background-color:#2f9e44;color:#ffffff;border-radius:5px;padding:0 16px;"
        )
        confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(confirm_btn)
        root.addLayout(btn_row)

        self._input.setFocus()

    # ── actions ───────────────────────────────────────────────────────────────

    def _add(self):
        pcb_id = self._input.text().strip().upper()
        if not pcb_id:
            return
        if pcb_id in self.pcb_ids:
            self._dup_label.setText(f"{pcb_id} already added in this session.")
            self._input.selectAll()
            return
        if pcb_id in self._historic:
            self._dup_label.setText(
                f"{pcb_id} was already sampled for rack {self._rack_number} in a previous scan."
            )
            self._input.selectAll()
            return
        self._dup_label.setText("")
        self.pcb_ids.append(pcb_id)
        self._list.addItem(QListWidgetItem(pcb_id))
        self._input.clear()
        self._count_label.setText(f"{len(self.pcb_ids)} PCB(s) sampled")

    def _remove_selected(self):
        for item in self._list.selectedItems():
            pcb_id = item.text()
            self.pcb_ids.remove(pcb_id)
            self._list.takeItem(self._list.row(item))
        self._count_label.setText(f"{len(self.pcb_ids)} PCB(s) sampled")

    def _on_confirm(self):
        if not self.pcb_ids:
            self._error_label.setText("At least one PCB ID must be sampled.")
            return
        self.accept()
