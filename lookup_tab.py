from datetime import datetime, timezone, timedelta, date
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QFrame, QHeaderView, QDateEdit, QFileDialog,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

import database
from utils import to_ist
from edit_dialog import EditScanDialog

IST_OFFSET = timedelta(hours=5, minutes=30)

HISTORY_HEADERS = ["#", "Rack No.", "Model", "Qty", "Inspected By", "Date/Time (IST)", "", ""]


def _ist_date_to_utc_range(d: date) -> tuple[str, str]:
    """Convert an IST calendar date to a UTC ISO range [start, end]."""
    # IST midnight = UTC 18:30 previous day
    ist_start = datetime(d.year, d.month, d.day, tzinfo=timezone(IST_OFFSET))
    ist_end   = ist_start + timedelta(days=1) - timedelta(seconds=1)
    return ist_start.astimezone(timezone.utc).isoformat(), \
           ist_end.astimezone(timezone.utc).isoformat()


class LookupTab(QWidget):
    def __init__(self):
        super().__init__()
        self._current_results: list = []
        self._setup_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 14)

        root.addWidget(self._build_filter_card())
        root.addWidget(self._build_summary_card())
        root.addWidget(self._build_history_section())
        root.addLayout(self._build_bottom_row())

    def _build_filter_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame{background-color:#313244;border-radius:8px;}")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        # Row 1 — Rack Number (optional)
        rack_row = QHBoxLayout()
        lbl = QLabel("RACK NUMBER:")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setFixedWidth(130)
        rack_row.addWidget(lbl)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Optional — leave blank to search all racks")
        self.search_input.setFont(QFont("Segoe UI", 13))
        self.search_input.setMinimumHeight(38)
        self.search_input.returnPressed.connect(self._on_search)
        rack_row.addWidget(self.search_input, 1)
        outer.addLayout(rack_row)

        # Row 2 — Date range
        date_row = QHBoxLayout()
        date_row.setSpacing(10)

        date_lbl = QLabel("DATE RANGE:")
        date_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        date_lbl.setFixedWidth(130)
        date_row.addWidget(date_lbl)

        today = QDate.currentDate()

        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(today)
        self.from_date.setDisplayFormat("dd/MM/yyyy")
        self.from_date.setFont(QFont("Segoe UI", 12))
        self.from_date.setMinimumHeight(38)

        to_lbl = QLabel("to")
        to_lbl.setFont(QFont("Segoe UI", 11))
        to_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(today)
        self.to_date.setDisplayFormat("dd/MM/yyyy")
        self.to_date.setFont(QFont("Segoe UI", 12))
        self.to_date.setMinimumHeight(38)

        all_btn = QPushButton("All Time")
        all_btn.setMinimumHeight(38)
        all_btn.setFont(QFont("Segoe UI", 11))
        all_btn.setStyleSheet("background-color:#45475a;color:#cdd6f4;border-radius:4px;")
        all_btn.clicked.connect(self._set_all_time)

        search_btn = QPushButton("SEARCH")
        search_btn.setMinimumHeight(38)
        search_btn.setMinimumWidth(110)
        search_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        search_btn.setStyleSheet("background-color:#89b4fa;color:#1e1e2e;border-radius:5px;")
        search_btn.clicked.connect(self._on_search)

        date_row.addWidget(self.from_date)
        date_row.addWidget(to_lbl)
        date_row.addWidget(self.to_date)
        date_row.addWidget(all_btn)
        date_row.addStretch()
        date_row.addWidget(search_btn)
        outer.addLayout(date_row)

        return card

    def _build_summary_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame{background-color:#181825;border-radius:8px;padding:4px;}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(3)

        self.summary_title = QLabel("No search run yet.")
        self.summary_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))

        self.summary_detail = QLabel("")
        self.summary_detail.setFont(QFont("Segoe UI", 11))
        self.summary_detail.setWordWrap(True)

        lay.addWidget(self.summary_title)
        lay.addWidget(self.summary_detail)
        return card

    def _build_history_section(self) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        hdr = QLabel("Results")
        hdr.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lay.addWidget(hdr)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(len(HISTORY_HEADERS))
        self.history_table.setHorizontalHeaderLabels(HISTORY_HEADERS)
        hh = self.history_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col, width in {0: 50, 3: 70, 6: 70, 7: 70}.items():
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.history_table.setColumnWidth(col, width)

        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setShowGrid(False)
        lay.addWidget(self.history_table)
        return container

    def _build_bottom_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch()
        self.export_btn = QPushButton("Export to Excel")
        self.export_btn.setMinimumHeight(42)
        self.export_btn.setMinimumWidth(160)
        self.export_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.export_btn.setStyleSheet(
            "background-color:#a6e3a1;color:#1e1e2e;border-radius:5px;"
        )
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export)
        row.addWidget(self.export_btn)
        return row

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_all_time(self):
        """Reset date range to cover all records."""
        self.from_date.setDate(QDate(2000, 1, 1))
        self.to_date.setDate(QDate.currentDate())

    def _get_utc_range(self) -> tuple[str, str]:
        fd = self.from_date.date().toPyDate()
        td = self.to_date.date().toPyDate()
        utc_from, _ = _ist_date_to_utc_range(fd)
        _, utc_to   = _ist_date_to_utc_range(td)
        return utc_from, utc_to

    # ── search ───────────────────────────────────────────────────────────────

    def _on_search(self):
        rack_number = self.search_input.text().strip().upper() or None
        utc_from, utc_to = self._get_utc_range()

        scans = database.search_scans(rack_number, utc_from, utc_to)
        self._current_results = scans

        if not scans:
            self.summary_title.setText("No records found.")
            self.summary_title.setStyleSheet("color:#f38ba8;")
            self.summary_detail.setText("")
            self.history_table.setRowCount(0)
            self.export_btn.setEnabled(False)
            return

        self._update_summary(scans, rack_number)
        self._populate_table(scans)
        self.export_btn.setEnabled(True)

    def _update_summary(self, scans: list, rack_number: str | None):
        total_scans = len(scans)
        total_qty   = sum(s["quantity"] for s in scans)

        # counts per model
        model_counts: dict[str, int] = {}
        for s in scans:
            model_counts[s["model"]] = model_counts.get(s["model"], 0) + s["quantity"]

        title = (
            f"{rack_number or 'All Racks'}  ·  "
            f"{total_scans} scan{'s' if total_scans != 1 else ''}  ·  "
            f"Total Qty: {total_qty}"
        )
        self.summary_title.setText(title)
        self.summary_title.setStyleSheet("color:#a6e3a1;")

        detail_parts = [f"{m}: {q}" for m, q in sorted(model_counts.items())]
        self.summary_detail.setText("By model — " + "  |  ".join(detail_parts))

    def _populate_table(self, scans: list):
        self.history_table.setRowCount(len(scans))
        for row, ev in enumerate(scans):
            values = [
                str(ev["id"]),
                ev["rack_number"],
                ev["model"],
                str(ev["quantity"]),
                ev["inspected_by"],
                to_ist(ev["created_at"]),
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.history_table.setItem(row, col, item)

            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet(
                "background-color:#89b4fa;color:#1e1e2e;"
                "border-radius:3px;padding:3px 8px;font-size:11px;"
            )
            edit_btn.clicked.connect(lambda _checked, sid=ev["id"]: self._edit_scan(sid))
            self.history_table.setCellWidget(row, 6, edit_btn)

            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet(
                "background-color:#f38ba8;color:#1e1e2e;"
                "border-radius:3px;padding:3px 8px;font-size:11px;"
            )
            del_btn.clicked.connect(lambda _checked, sid=ev["id"]: self._delete_scan(sid))
            self.history_table.setCellWidget(row, 7, del_btn)

    def _edit_scan(self, scan_id: int):
        try:
            dlg = EditScanDialog(scan_id, self)
        except ValueError:
            return
        if dlg.exec():
            self._on_search()

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
            database.delete_scan(scan_id)
            self._on_search()

    # ── export ───────────────────────────────────────────────────────────────

    def _on_export(self):
        if not self._current_results:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Excel File",
            str(Path.home() / "rack_export.xlsx"),
            "Excel Files (*.xlsx)",
        )
        if not path:
            return

        try:
            self._write_excel(path)
            QMessageBox.information(self, "Export Complete", f"Saved to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def _write_excel(self, path: str):
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()

        # ── shared styles (white/light theme) ───────────────────────────────
        HEADER_FILL  = PatternFill("solid", fgColor="2F5496")   # dark blue header
        HEADER_FONT  = Font(bold=True, color="FFFFFF", size=11)
        ALT_FILL     = PatternFill("solid", fgColor="DCE6F1")   # light blue alternate rows
        WHITE_FILL   = PatternFill("solid", fgColor="FFFFFF")
        CENTER       = Alignment(horizontal="center", vertical="center")
        thin         = Side(style="thin", color="AAAAAA")
        BORDER       = Border(left=thin, right=thin, top=thin, bottom=thin)
        NORMAL_FONT  = Font(color="000000", size=11)

        # ── Sheet 1: Scan Records ────────────────────────────────────────────
        ws = wb.active
        ws.title = "Scan Records"

        headers = ["Sr. No.", "Rack Number", "Model", "Quantity", "Inspected By", "Date/Time (IST)"]
        ws.append(headers)
        for col in range(1, len(headers) + 1):
            cell = ws.cell(1, col)
            cell.fill      = HEADER_FILL
            cell.font      = HEADER_FONT
            cell.alignment = CENTER
            cell.border    = BORDER
        ws.row_dimensions[1].height = 22

        for i, ev in enumerate(self._current_results, 1):
            row_data = [
                i,                          # Sr. No. — sequential, not DB id
                ev["rack_number"],
                ev["model"],
                ev["quantity"],
                ev["inspected_by"],
                to_ist(ev["created_at"]),
            ]
            ws.append(row_data)
            fill = ALT_FILL if i % 2 == 0 else WHITE_FILL
            for col in range(1, len(row_data) + 1):
                cell = ws.cell(i + 1, col)
                cell.fill      = fill
                cell.font      = NORMAL_FONT
                cell.alignment = CENTER
                cell.border    = BORDER

        for col, width in enumerate([9, 16, 20, 12, 20, 22], 1):
            ws.column_dimensions[get_column_letter(col)].width = width

        # ── Sheet 2: Summary ─────────────────────────────────────────────────
        ws2 = wb.create_sheet("Summary")

        SECTION_FONT  = Font(bold=True, size=12, color="2F5496")
        TOTAL_FONT    = Font(bold=True, size=11, color="000000")
        SUBHDR_FILL   = PatternFill("solid", fgColor="2F5496")
        SUBHDR_FONT   = Font(bold=True, color="FFFFFF", size=11)

        def _add_section_header(label: str):
            ws2.append([label])
            ws2.cell(ws2.max_row, 1).font = SECTION_FONT

        def _add_table_header(*cols):
            ws2.append(list(cols))
            r = ws2.max_row
            for c in range(1, len(cols) + 1):
                cell = ws2.cell(r, c)
                cell.fill      = SUBHDR_FILL
                cell.font      = SUBHDR_FONT
                cell.alignment = CENTER
                cell.border    = BORDER
            ws2.row_dimensions[r].height = 20

        # --- Overall totals ---
        _add_section_header("OVERALL TOTALS")
        total_scans = len(self._current_results)
        total_qty   = sum(s["quantity"] for s in self._current_results)

        for label, value in [("Total Scans", total_scans), ("Total Quantity", total_qty)]:
            ws2.append([label, value])
            r = ws2.max_row
            for c in [1, 2]:
                cell = ws2.cell(r, c)
                cell.fill      = WHITE_FILL
                cell.font      = TOTAL_FONT
                cell.alignment = CENTER
                cell.border    = BORDER

        ws2.append([])

        # --- By Model ---
        _add_section_header("BY MODEL")
        _add_table_header("Model", "Scan Count", "Total Quantity")

        model_data: dict[str, list] = {}
        for s in self._current_results:
            if s["model"] not in model_data:
                model_data[s["model"]] = [0, 0]
            model_data[s["model"]][0] += 1
            model_data[s["model"]][1] += s["quantity"]

        for i, (model, (count, qty)) in enumerate(sorted(model_data.items()), 1):
            ws2.append([model, count, qty])
            fill = ALT_FILL if i % 2 == 0 else WHITE_FILL
            for col in range(1, 4):
                cell = ws2.cell(ws2.max_row, col)
                cell.fill      = fill
                cell.font      = NORMAL_FONT
                cell.alignment = CENTER
                cell.border    = BORDER

        ws2.append([])

        # --- By Rack ---
        _add_section_header("BY RACK")
        _add_table_header("Rack Number", "Scan Count", "Total Quantity")

        rack_data: dict[str, list] = {}
        for s in self._current_results:
            if s["rack_number"] not in rack_data:
                rack_data[s["rack_number"]] = [0, 0]
            rack_data[s["rack_number"]][0] += 1
            rack_data[s["rack_number"]][1] += s["quantity"]

        for i, (rack, (count, qty)) in enumerate(sorted(rack_data.items()), 1):
            ws2.append([rack, count, qty])
            fill = ALT_FILL if i % 2 == 0 else WHITE_FILL
            for col in range(1, 4):
                cell = ws2.cell(ws2.max_row, col)
                cell.fill      = fill
                cell.font      = NORMAL_FONT
                cell.alignment = CENTER
                cell.border    = BORDER

        for col, width in enumerate([22, 14, 16], 1):
            ws2.column_dimensions[get_column_letter(col)].width = width

        wb.save(path)
