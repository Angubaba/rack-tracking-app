from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

import database
from logic import check_th_completion_lock
from utils import now_ist_display
from active_racks_widget import ActiveRacksWidget
from th_verify_dialog import THVerifyDialog

STATUS_COLOR = {
    "success": "#2f9e44",
    "warning": "#e67700",
    "error":   "#c92a2a",
}


class THTab(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._start_clock()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 14)

        root.addWidget(self._build_form())
        root.addWidget(self._build_status_label())

        self._active = ActiveRacksWidget()
        root.addWidget(self._active)

    def _build_form(self) -> QFrame:
        frame = QFrame()
        lay = QVBoxLayout(frame)
        lay.setSpacing(10)
        lay.setContentsMargins(0, 0, 0, 0)

        # Date/Time (read-only clock)
        self.datetime_display = QLineEdit()
        self.datetime_display.setReadOnly(True)
        self.datetime_display.setFont(QFont("Segoe UI", 13))
        self.datetime_display.setMinimumHeight(40)
        self.datetime_display.setStyleSheet(
            "QLineEdit{background-color:#e7f5ff;color:#1864ab;"
            "border:1px solid #a5d8ff;border-radius:4px;padding:4px 8px;}"
        )
        lay.addLayout(self._row("DATE/TIME:", self.datetime_display))

        # Rack Number
        self.rack_input = QLineEdit()
        self.rack_input.setPlaceholderText("Scan barcode of rack going to TH…")
        self.rack_input.setFont(QFont("Segoe UI", 15))
        self.rack_input.setMinimumHeight(50)
        self.rack_input.returnPressed.connect(self._on_scan)
        self.rack_input.textChanged.connect(self._force_upper)
        lay.addLayout(self._row("RACK NUMBER:", self.rack_input))

        send_btn = QPushButton("SEND TO TH")
        send_btn.setMinimumHeight(52)
        send_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        send_btn.setStyleSheet(
            "background-color:#1971c2;color:#ffffff;border-radius:5px;"
        )
        send_btn.clicked.connect(self._on_scan)
        lay.addWidget(send_btn)

        return frame

    @staticmethod
    def _row(label_text: str, widget, stretch: bool = True) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setFixedWidth(130)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        row.addWidget(lbl)
        row.addWidget(widget, 1 if stretch else 0)
        return row

    def _build_status_label(self) -> QLabel:
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Segoe UI", 12))
        self.status_label.setMinimumHeight(32)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        return self.status_label

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
        rack_number = self.rack_input.text().strip().upper()
        if not rack_number:
            self._set_status("Rack Number is required.", "error")
            return

        ok_scan = database.get_active_rack(rack_number)
        if not ok_scan:
            self._set_status(
                f"Rack {rack_number} is not in FG. Scan it as OK first.",
                "error",
            )
            self.rack_input.setFocus()
            return

        # ── completion lock (TH tab only, independent of OK duplicate lock) ──
        lock = check_th_completion_lock(rack_number)
        if lock:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "Recent TH Lock", lock.message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.rack_input.setFocus()
                return

        # Show verification dialog
        dlg = THVerifyDialog(ok_scan, self)
        if dlg.exec():
            database.insert_th_scan(
                ok_scan_id   = ok_scan["id"],
                rack_number  = ok_scan["rack_number"],
                model        = ok_scan["model"],
                quantity     = ok_scan["quantity"],
                inspected_by = ok_scan["inspected_by"],
                taken_by     = dlg.taken_by,
            )
            self._set_status(
                f"Rack {rack_number} sent to TH. Taken by: {dlg.taken_by}",
                "success",
            )
            self.rack_input.clear()
            self._active.refresh()

        self.rack_input.setFocus()

    def _set_status(self, message: str, status: str):
        color = STATUS_COLOR.get(status, "#cdd6f4")
        self.status_label.setStyleSheet(f"color:{color};font-weight:bold;")
        self.status_label.setText(message)

    # ── called by MainWindow on tab switch ───────────────────────────────────

    def _force_upper(self, text: str):
        uppered = text.upper()
        if uppered != text:
            cursor = self.rack_input.cursorPosition()
            self.rack_input.blockSignals(True)
            self.rack_input.setText(uppered)
            self.rack_input.setCursorPosition(cursor)
            self.rack_input.blockSignals(False)

    def on_activate(self):
        self._active.refresh()
        self.rack_input.setFocus()
        self.rack_input.selectAll()
