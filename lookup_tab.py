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

HEADERS = ["Sr.No.", "Type", "Rack No.", "Model", "Qty",
           "Inspected By", "Taken By", "PCB Samples", "Date/Time (IST)", "", ""]

TYPE_COLORS = {
    "OK": "#a6e3a1",
    "TH": "#89b4fa",
}


def _ist_date_to_utc_range(d: date) -> tuple[str, str]:
    ist_start = datetime(d.year, d.month, d.day, tzinfo=timezone(IST_OFFSET))
    ist_end   = ist_start + timedelta(days=1) - timedelta(seconds=1)
    return (ist_start.astimezone(timezone.utc).isoformat(),
            ist_end.astimezone(timezone.utc).isoformat())


class LookupTab(QWidget):
    def __init__(self):
        super().__init__()
        self._results: list = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 14)

        root.addWidget(self._build_filter_card())
        root.addWidget(self._build_summary_card())
        root.addWidget(self._build_table_section())
        root.addLayout(self._build_bottom_row())

    # ── filters ───────────────────────────────────────────────────────────────

    def _build_filter_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame{background-color:#f1f3f5;border-radius:8px;border:1px solid #dee2e6;}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        # Rack number (optional)
        rack_row = QHBoxLayout()
        lbl = QLabel("RACK NUMBER:")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setFixedWidth(130)
        rack_row.addWidget(lbl)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Optional — leave blank to show all")
        self.search_input.setFont(QFont("Segoe UI", 13))
        self.search_input.setMinimumHeight(38)
        self.search_input.returnPressed.connect(self._on_search)
        rack_row.addWidget(self.search_input, 1)
        lay.addLayout(rack_row)

        # Date range
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
        all_btn.setStyleSheet("background-color:#e9ecef;color:#212529;border-radius:4px;border:1px solid #ced4da;")
        all_btn.clicked.connect(lambda: (
            self.from_date.setDate(QDate(2000, 1, 1)),
            self.to_date.setDate(QDate.currentDate()),
        ))

        search_btn = QPushButton("SEARCH")
        search_btn.setMinimumHeight(38)
        search_btn.setMinimumWidth(110)
        search_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        search_btn.setStyleSheet("background-color:#1971c2;color:#ffffff;border-radius:5px;")
        search_btn.clicked.connect(self._on_search)

        date_row.addWidget(self.from_date)
        date_row.addWidget(to_lbl)
        date_row.addWidget(self.to_date)
        date_row.addWidget(all_btn)
        date_row.addStretch()
        date_row.addWidget(search_btn)
        lay.addLayout(date_row)
        return card

    def _build_summary_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame{background-color:#ffffff;border-radius:8px;border:1px solid #dee2e6;}")
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

    def _build_table_section(self) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self.table = QTableWidget()
        self.table.setColumnCount(len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col, width in {0: 55, 1: 55, 4: 60, 8: 70, 9: 70}.items():
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        lay.addWidget(self.table)
        return container

    def _build_bottom_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch()
        self.export_btn = QPushButton("Export to Excel")
        self.export_btn.setMinimumHeight(42)
        self.export_btn.setMinimumWidth(160)
        self.export_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.export_btn.setStyleSheet(
            "background-color:#2f9e44;color:#ffffff;border-radius:5px;"
        )
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export)
        row.addWidget(self.export_btn)
        return row

    # ── search ────────────────────────────────────────────────────────────────

    def _on_search(self):
        rack_number = self.search_input.text().strip().upper() or None
        fd = self.from_date.date().toPyDate()
        td = self.to_date.date().toPyDate()
        utc_from, _ = _ist_date_to_utc_range(fd)
        _, utc_to   = _ist_date_to_utc_range(td)

        results = database.search_events(rack_number, utc_from, utc_to)
        self._results = results

        if not results:
            self.summary_title.setText("No records found.")
            self.summary_title.setStyleSheet("color:#c92a2a;")
            self.summary_detail.setText("")
            self.table.setRowCount(0)
            self.export_btn.setEnabled(False)
            return

        self._update_summary(results)
        self._populate_table(results)
        self.export_btn.setEnabled(True)

    def _update_summary(self, results: list):
        ok_count = sum(1 for r in results if r["event_type"] == "OK")
        th_count = sum(1 for r in results if r["event_type"] == "TH")
        total_qty = sum(r["quantity"] for r in results if r["event_type"] == "OK")

        self.summary_title.setText(
            f"{ok_count} OK scan{'s' if ok_count != 1 else ''}  ·  "
            f"{th_count} sent to TH  ·  Total Qty in OK scans: {total_qty}"
        )
        self.summary_title.setStyleSheet("color:#2f9e44;")

        model_qty: dict[str, int] = {}
        for r in results:
            if r["event_type"] == "OK":
                model_qty[r["model"]] = model_qty.get(r["model"], 0) + r["quantity"]
        parts = [f"{m}: {q}" for m, q in sorted(model_qty.items())]
        self.summary_detail.setText("By model (OK) — " + "  |  ".join(parts) if parts else "")

    def _populate_table(self, results: list):
        self.table.setRowCount(len(results))
        for row, ev in enumerate(results):
            # PCB samples only exist for OK scans
            if ev["event_type"] == "OK":
                pcbs = database.get_pcb_samples(ev["id"])
                pcb_text = ", ".join(r["pcb_id"] for r in pcbs) if pcbs else "—"
            else:
                pcb_text = "—"

            values = [
                str(row + 1),
                ev["event_type"],
                ev["rack_number"],
                ev["model"],
                str(ev["quantity"]),
                ev["inspected_by"],
                ev["taken_by"] or "—",
                pcb_text,
                to_ist(ev["created_at"]),
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 1:
                    item.setForeground(
                        __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor(
                            TYPE_COLORS.get(ev["event_type"], "#212529")
                        )
                    )
                self.table.setItem(row, col, item)

            scan_type = ev["event_type"].lower()
            scan_id   = ev["id"]

            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet(
                "background-color:#1971c2;color:#ffffff;"
                "border-radius:3px;padding:3px 6px;font-size:11px;"
            )
            edit_btn.clicked.connect(
                lambda _c, st=scan_type, sid=scan_id: self._edit(st, sid)
            )
            self.table.setCellWidget(row, 9, edit_btn)

            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet(
                "background-color:#c92a2a;color:#ffffff;"
                "border-radius:3px;padding:3px 6px;font-size:11px;"
            )
            del_btn.clicked.connect(
                lambda _c, st=scan_type, sid=scan_id,
                       rack=ev["rack_number"]: self._delete(st, sid, rack)
            )
            self.table.setCellWidget(row, 10, del_btn)

    # ── edit / delete ────────────────────────────────────────────────────────

    def _edit(self, scan_type: str, scan_id: int):
        try:
            dlg = EditScanDialog(scan_type, scan_id, self)
        except ValueError:
            return
        if dlg.exec():
            self._on_search()

    def _delete(self, scan_type: str, scan_id: int, rack_number: str):
        if scan_type == "ok":
            linked = database.get_th_scan_for_ok(scan_id)
            if linked:
                msg = (
                    f"This OK scan for rack {rack_number} also has a linked TH scan.\n"
                    f"Deleting it will also delete the TH scan.\n\nProceed?"
                )
            else:
                msg = f"Delete this OK scan for rack {rack_number}?"
        else:
            msg = (
                f"Delete this TH scan for rack {rack_number}?\n"
                f"The rack will become active in FG again."
            )

        reply = QMessageBox.question(
            self, "Delete Record", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if scan_type == "ok":
            database.delete_ok_scan(scan_id)   # cascades to th_scan
        else:
            database.delete_th_scan(scan_id)

        self._on_search()

    # ── export ───────────────────────────────────────────────────────────────

    def _on_export(self):
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel File",
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

        HEADER_FILL = PatternFill("solid", fgColor="2F5496")
        HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
        OK_FILL     = PatternFill("solid", fgColor="E2EFDA")   # light green for OK rows
        TH_FILL     = PatternFill("solid", fgColor="DDEBF7")   # light blue for TH rows
        WHITE_FILL  = PatternFill("solid", fgColor="FFFFFF")
        CENTER      = Alignment(horizontal="center", vertical="center")
        thin        = Side(style="thin", color="AAAAAA")
        BORDER      = Border(left=thin, right=thin, top=thin, bottom=thin)
        NORMAL_FONT = Font(color="000000", size=11)

        # ── Sheet 1: All Events ──────────────────────────────────────────────
        ws = wb.active
        ws.title = "All Events"

        headers = ["Sr. No.", "Type", "Rack Number", "Model", "Quantity",
                   "Inspected By", "Taken By", "PCB Samples", "Date/Time (IST)"]
        ws.append(headers)
        for col in range(1, len(headers) + 1):
            c = ws.cell(1, col)
            c.fill = HEADER_FILL; c.font = HEADER_FONT
            c.alignment = CENTER; c.border = BORDER
        ws.row_dimensions[1].height = 22

        for i, ev in enumerate(self._results, 1):
            if ev["event_type"] == "OK":
                pcbs = database.get_pcb_samples(ev["id"])
                pcb_text = ", ".join(r["pcb_id"] for r in pcbs) if pcbs else ""
            else:
                pcb_text = ""
            row_data = [
                i,
                ev["event_type"],
                ev["rack_number"],
                ev["model"],
                ev["quantity"],
                ev["inspected_by"],
                ev["taken_by"] or "",
                pcb_text,
                to_ist(ev["created_at"]),
            ]
            ws.append(row_data)
            fill = OK_FILL if ev["event_type"] == "OK" else TH_FILL
            for col in range(1, len(row_data) + 1):
                c = ws.cell(i + 1, col)
                c.fill = fill; c.font = NORMAL_FONT
                c.alignment = CENTER; c.border = BORDER

        for col, w in enumerate([9, 8, 16, 20, 12, 20, 20, 22], 1):
            ws.column_dimensions[get_column_letter(col)].width = w

        # ── Sheet 2: Summary ─────────────────────────────────────────────────
        ws2 = wb.create_sheet("Summary")

        SUBHDR_FILL = PatternFill("solid", fgColor="2F5496")
        SUBHDR_FONT = Font(bold=True, color="FFFFFF", size=11)
        ALT_FILL    = PatternFill("solid", fgColor="DCE6F1")
        SEC_FONT    = Font(bold=True, size=12, color="2F5496")
        TOTAL_FONT  = Font(bold=True, size=11)

        def section(title):
            ws2.append([title])
            ws2.cell(ws2.max_row, 1).font = SEC_FONT

        def table_header(*cols):
            ws2.append(list(cols))
            r = ws2.max_row
            for c in range(1, len(cols) + 1):
                cell = ws2.cell(r, c)
                cell.fill = SUBHDR_FILL; cell.font = SUBHDR_FONT
                cell.alignment = CENTER; cell.border = BORDER
            ws2.row_dimensions[r].height = 20

        def data_row(vals, alt):
            ws2.append(vals)
            f = ALT_FILL if alt else WHITE_FILL
            for c in range(1, len(vals) + 1):
                cell = ws2.cell(ws2.max_row, c)
                cell.fill = f; cell.font = NORMAL_FONT
                cell.alignment = CENTER; cell.border = BORDER

        ok_rows = [r for r in self._results if r["event_type"] == "OK"]
        th_rows = [r for r in self._results if r["event_type"] == "TH"]

        # Totals
        section("OVERALL TOTALS")
        for label, val in [
            ("Total OK Scans",    len(ok_rows)),
            ("Total Sent to TH",  len(th_rows)),
            ("Total Quantity (OK)", sum(r["quantity"] for r in ok_rows)),
        ]:
            ws2.append([label, val])
            for c in [1, 2]:
                cell = ws2.cell(ws2.max_row, c)
                cell.fill = WHITE_FILL; cell.font = TOTAL_FONT
                cell.alignment = CENTER; cell.border = BORDER
        ws2.append([])

        # By model
        section("BY MODEL  (OK scans)")
        table_header("Model", "Scan Count", "Total Quantity")
        model_data: dict[str, list] = {}
        for r in ok_rows:
            if r["model"] not in model_data:
                model_data[r["model"]] = [0, 0]
            model_data[r["model"]][0] += 1
            model_data[r["model"]][1] += r["quantity"]
        for i, (m, (cnt, qty)) in enumerate(sorted(model_data.items()), 1):
            data_row([m, cnt, qty], i % 2 == 0)
        ws2.append([])

        # By rack
        section("BY RACK")
        table_header("Rack Number", "OK Scans", "Sent to TH", "Total Qty")
        rack_data: dict[str, list] = {}
        for r in self._results:
            if r["rack_number"] not in rack_data:
                rack_data[r["rack_number"]] = [0, 0, 0]
            if r["event_type"] == "OK":
                rack_data[r["rack_number"]][0] += 1
                rack_data[r["rack_number"]][2] += r["quantity"]
            else:
                rack_data[r["rack_number"]][1] += 1
        for i, (rack, (ok, th, qty)) in enumerate(sorted(rack_data.items()), 1):
            data_row([rack, ok, th, qty], i % 2 == 0)

        for col, w in enumerate([22, 14, 14, 16], 1):
            ws2.column_dimensions[get_column_letter(col)].width = w

        wb.save(path)
