from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QFrame, QHeaderView,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

import database
from logic import perform_scan
from utils import to_ist, now_ist_display
from edit_dialog import EditScanDialog

STATUS_COLOR = {
    "success": "#a6e3a1",
    "warning": "#f9e2af",
    "error":   "#f38ba8",
}

RECENT_HEADERS = ["Rack No.", "Model", "Qty", "Inspected By", "Date/Time (IST)", "", ""]


class ScanTab(QWidget):
    def __init__(self):
        super().__init__()
        self._last_scan_id: int | None = None
        self._setup_ui()
        self._start_clock()
        self._refresh_recent()

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 14)

        root.addWidget(self._build_fields_frame())
        root.addLayout(self._build_action_row())
        root.addWidget(self._build_status_label())
        root.addWidget(self._build_recent_section())

    def _build_fields_frame(self) -> QFrame:
        frame = QFrame()
        lay = QVBoxLayout(frame)
        lay.setSpacing(10)
        lay.setContentsMargins(0, 0, 0, 0)

        # Date/Time — read-only auto clock
        self.datetime_display = QLineEdit()
        self.datetime_display.setReadOnly(True)
        self.datetime_display.setFont(QFont("Segoe UI", 13))
        self.datetime_display.setMinimumHeight(40)
        self.datetime_display.setStyleSheet(
            "QLineEdit{background-color:#181825;color:#89b4fa;"
            "border:1px solid #45475a;border-radius:4px;padding:4px 8px;}"
        )
        lay.addLayout(self._field_row("DATE/TIME:", self.datetime_display))

        # Rack Number — primary barcode field
        self.rack_input = QLineEdit()
        self.rack_input.setPlaceholderText("Scan barcode  (PR/### or MR/###)…")
        self.rack_input.setFont(QFont("Segoe UI", 15))
        self.rack_input.setMinimumHeight(50)
        self.rack_input.returnPressed.connect(self._on_scan)
        lay.addLayout(self._field_row("RACK NUMBER:", self.rack_input))

        # Model
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Enter model name…")
        self.model_input.setFont(QFont("Segoe UI", 13))
        self.model_input.setMinimumHeight(40)
        lay.addLayout(self._field_row("MODEL:", self.model_input))

        # Quantity
        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 10_000)
        self.qty_input.setValue(1)
        self.qty_input.setFont(QFont("Segoe UI", 13))
        self.qty_input.setMinimumHeight(40)
        self.qty_input.setFixedWidth(140)
        qty_row = QHBoxLayout()
        qty_row.addLayout(self._field_row("QUANTITY:", self.qty_input, stretch=False))
        qty_row.addStretch()
        lay.addLayout(qty_row)

        # Inspected By
        self.inspector_input = QLineEdit()
        self.inspector_input.setPlaceholderText("Inspector name or ID…")
        self.inspector_input.setFont(QFont("Segoe UI", 13))
        self.inspector_input.setMinimumHeight(40)
        lay.addLayout(self._field_row("INSPECTED BY:", self.inspector_input))

        return frame

    @staticmethod
    def _field_row(label_text: str, widget, stretch: bool = True) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setFixedWidth(130)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        row.addWidget(lbl)
        row.addWidget(widget, 1 if stretch else 0)
        return row

    def _build_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        self.scan_btn = QPushButton("SCAN")
        self.scan_btn.setMinimumHeight(52)
        self.scan_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.scan_btn.setStyleSheet(
            "background-color:#a6e3a1;color:#1e1e2e;border-radius:5px;"
        )
        self.scan_btn.clicked.connect(self._on_scan)

        self.undo_btn = QPushButton("UNDO LAST SCAN")
        self.undo_btn.setMinimumHeight(52)
        self.undo_btn.setFont(QFont("Segoe UI", 12))
        self.undo_btn.setStyleSheet(
            "background-color:#f38ba8;color:#1e1e2e;border-radius:5px;"
        )
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self._on_undo)

        row.addWidget(self.scan_btn, 2)
        row.addWidget(self.undo_btn, 1)
        return row

    def _build_status_label(self) -> QLabel:
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Segoe UI", 12))
        self.status_label.setMinimumHeight(36)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        return self.status_label

    def _build_recent_section(self) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        hdr = QLabel("Recent Scans (last 10)")
        hdr.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lay.addWidget(hdr)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(len(RECENT_HEADERS))
        self.recent_table.setHorizontalHeaderLabels(RECENT_HEADERS)
        hh = self.recent_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col, width in {2: 70, 5: 70, 6: 70}.items():
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.recent_table.setColumnWidth(col, width)
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.setAlternatingRowColors(True)
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.setShowGrid(False)
        lay.addWidget(self.recent_table)
        return container

    # ── clock ────────────────────────────────────────────────────────────────

    def _start_clock(self):
        self._tick()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _tick(self):
        self.datetime_display.setText(now_ist_display())

    # ── scan ─────────────────────────────────────────────────────────────────

    def _on_scan(self):
        rack_number  = self.rack_input.text().strip().upper()
        model        = self.model_input.text().strip().upper()
        quantity     = self.qty_input.value()
        inspected_by = self.inspector_input.text().strip().upper()
        self._attempt_scan(rack_number, model, quantity, inspected_by, override=False)

    def _attempt_scan(
        self,
        rack_number: str,
        model: str,
        quantity: int,
        inspected_by: str,
        override: bool,
    ):
        result = perform_scan(rack_number, model, quantity, inspected_by, override=override)

        if result.status == "confirm_required":
            reply = QMessageBox.question(
                self,
                "Recent Scan Lock",
                result.message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._attempt_scan(rack_number, model, quantity, inspected_by, override=True)
            return

        self._set_status(result.message, result.status)

        if result.success:
            self._last_scan_id = result.scan_id
            self.undo_btn.setEnabled(True)
            self.rack_input.clear()
            self._refresh_recent()

        self.rack_input.setFocus()

    # ── undo ─────────────────────────────────────────────────────────────────

    def _on_undo(self):
        if self._last_scan_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Undo Last Scan",
            "Delete the last scan record? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_scan(self._last_scan_id)
            self._last_scan_id = None
            self.undo_btn.setEnabled(False)
            self._set_status("Last scan undone.", "success")
            self._refresh_recent()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, message: str, status: str):
        color = STATUS_COLOR.get(status, "#cdd6f4")
        self.status_label.setStyleSheet(f"color:{color};font-weight:bold;")
        self.status_label.setText(message)

    def _refresh_recent(self):
        events = database.get_recent_scans(10)
        self.recent_table.setRowCount(len(events))
        for row, ev in enumerate(events):
            values = [
                ev["rack_number"],
                ev["model"],
                str(ev["quantity"]),
                ev["inspected_by"],
                to_ist(ev["created_at"]),
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.recent_table.setItem(row, col, item)

            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet(
                "background-color:#89b4fa;color:#1e1e2e;"
                "border-radius:3px;padding:3px 6px;font-size:11px;"
            )
            edit_btn.clicked.connect(lambda _checked, sid=ev["id"]: self._edit_scan(sid))
            self.recent_table.setCellWidget(row, 5, edit_btn)

            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet(
                "background-color:#f38ba8;color:#1e1e2e;"
                "border-radius:3px;padding:3px 6px;font-size:11px;"
            )
            del_btn.clicked.connect(lambda _checked, sid=ev["id"]: self._delete_scan(sid))
            self.recent_table.setCellWidget(row, 6, del_btn)

    def _edit_scan(self, scan_id: int):
        try:
            dlg = EditScanDialog(scan_id, self)
        except ValueError:
            return
        if dlg.exec():
            self._refresh_recent()

    def _delete_scan(self, scan_id: int):
        ev = database.get_scan_by_id(scan_id)
        if not ev:
            return
        reply = QMessageBox.question(
            self,
            "Delete Scan Record",
            (
                f"Permanently delete this record?\n\n"
                f"  Rack:    {ev['rack_number']}\n"
                f"  Model:   {ev['model']}\n"
                f"  Time:    {to_ist(ev['created_at'])}"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._last_scan_id == scan_id:
                self._last_scan_id = None
                self.undo_btn.setEnabled(False)
            database.delete_scan(scan_id)
            self._refresh_recent()

    def focus_barcode(self):
        self.rack_input.setFocus()
        self.rack_input.selectAll()
