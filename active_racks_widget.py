from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import database
from utils import to_ist

HEADERS = ["Rack No.", "Model", "Qty", "Inspected By", "In FG Since (IST)"]


class ActiveRacksWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        hdr = QLabel("Active Racks in FG")
        hdr.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lay.addWidget(hdr)

        self._table = QTableWidget()
        self._table.setColumnCount(len(HEADERS))
        self._table.setHorizontalHeaderLabels(HEADERS)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 70)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        lay.addWidget(self._table)

    def refresh(self):
        racks = database.get_active_racks()
        self._table.setRowCount(len(racks))
        for row, r in enumerate(racks):
            values = [
                r["rack_number"],
                r["model"],
                str(r["quantity"]),
                r["inspected_by"],
                to_ist(r["created_at"]),
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)
