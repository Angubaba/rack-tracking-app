from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import database
from utils import to_ist

HEADERS = ["Rack No.", "Model", "Qty", "Inspected By", "Inspected PCBs", "In FG Since (IST)"]

# PCB count col index
_PCB_COL = 4


class ActiveRacksWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        hdr = QLabel("Active Racks in FG")
        hdr.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lay.addWidget(hdr)

        self._table = QTableWidget()
        self._table.setColumnCount(len(HEADERS))
        self._table.setHorizontalHeaderLabels(HEADERS)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        for col, width in {2: 60, _PCB_COL: 110}.items():
            hh.setSectionResizeMode(col, QHeaderView.Fixed)
            self._table.setColumnWidth(col, width)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        lay.addWidget(self._table)

    def refresh(self):
        racks = database.get_active_racks()
        self._table.setRowCount(len(racks))
        for row, r in enumerate(racks):
            pcb_rows = database.get_pcb_samples(r["id"])
            pcb_ids  = [p["pcb_id"] for p in pcb_rows]
            pcb_text = f"{len(pcb_ids)} sampled" if pcb_ids else "0 sampled"

            values = [
                r["rack_number"],
                r["model"],
                str(r["quantity"]),
                r["inspected_by"],
                pcb_text,
                to_ist(r["created_at"]),
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if col == _PCB_COL:
                    item.setData(Qt.UserRole, pcb_ids)
                    if pcb_ids:
                        item.setToolTip("Double-click to view PCB IDs")
                self._table.setItem(row, col, item)

    def _on_double_click(self, row: int, col: int):
        if col != _PCB_COL:
            return
        item = self._table.item(row, col)
        if not item:
            return
        pcb_ids = item.data(Qt.UserRole) or []
        if not pcb_ids:
            return
        # Import here to avoid circular imports
        from lookup_tab import _show_pcb_popup
        _show_pcb_popup(pcb_ids, self)
