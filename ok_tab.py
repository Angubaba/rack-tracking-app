from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QFrame,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from logic import perform_ok_scan
from utils import now_ist_display
from active_racks_widget import ActiveRacksWidget

STATUS_COLOR = {
    "success": "#a6e3a1",
    "warning": "#f9e2af",
    "error":   "#f38ba8",
}


class OKTab(QWidget):
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
        root.addLayout(self._build_action_row())
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
            "QLineEdit{background-color:#181825;color:#89b4fa;"
            "border:1px solid #45475a;border-radius:4px;padding:4px 8px;}"
        )
        lay.addLayout(self._row("DATE/TIME:", self.datetime_display))

        # Rack Number
        self.rack_input = QLineEdit()
        self.rack_input.setPlaceholderText("Scan barcode  (PR/### or MR/###)…")
        self.rack_input.setFont(QFont("Segoe UI", 15))
        self.rack_input.setMinimumHeight(50)
        self.rack_input.returnPressed.connect(self._on_scan)
        lay.addLayout(self._row("RACK NUMBER:", self.rack_input))

        # Model
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Enter model name…")
        self.model_input.setFont(QFont("Segoe UI", 13))
        self.model_input.setMinimumHeight(40)
        lay.addLayout(self._row("MODEL:", self.model_input))

        # Quantity
        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 10_000)
        self.qty_input.setValue(1)
        self.qty_input.setFont(QFont("Segoe UI", 13))
        self.qty_input.setMinimumHeight(40)
        self.qty_input.setFixedWidth(140)
        qty_row = QHBoxLayout()
        qty_row.addLayout(self._row("QUANTITY:", self.qty_input, stretch=False))
        qty_row.addStretch()
        lay.addLayout(qty_row)

        # Inspected By
        self.inspector_input = QLineEdit()
        self.inspector_input.setPlaceholderText("Inspector name or ID…")
        self.inspector_input.setFont(QFont("Segoe UI", 13))
        self.inspector_input.setMinimumHeight(40)
        lay.addLayout(self._row("INSPECTED BY:", self.inspector_input))

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

    def _build_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.scan_btn = QPushButton("MARK OK  →  ADD TO FG")
        self.scan_btn.setMinimumHeight(52)
        self.scan_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.scan_btn.setStyleSheet(
            "background-color:#a6e3a1;color:#1e1e2e;border-radius:5px;"
        )
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)
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
        rack_number  = self.rack_input.text().strip().upper()
        model        = self.model_input.text().strip().upper()
        quantity     = self.qty_input.value()
        inspected_by = self.inspector_input.text().strip().upper()

        result = perform_ok_scan(rack_number, model, quantity, inspected_by)
        color = STATUS_COLOR.get(result.status, "#cdd6f4")
        self.status_label.setStyleSheet(f"color:{color};font-weight:bold;")
        self.status_label.setText(result.message)

        if result.success:
            self.rack_input.clear()
            self._active.refresh()

        self.rack_input.setFocus()

    # ── called by MainWindow on tab switch ───────────────────────────────────

    def on_activate(self):
        self._active.refresh()
        self.rack_input.setFocus()
        self.rack_input.selectAll()
