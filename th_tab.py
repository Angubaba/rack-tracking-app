"""GOING TO TH tab — sends a rack from FG to Through-Hole."""
import tkinter as tk
from tkinter import ttk

import database
from logic import check_th_completion_lock
from utils import now_ist_display, normalise_rack_number
from active_racks_widget import ActiveRacksWidget
from ui_helpers import (
    BG, colored_btn, form_label, readonly_entry, text_entry,
    status_label, make_upper, STATUS_FG, ask_yes_no, scanner_guard,
    attach_rack_cleaner,
)


class THTab:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=14)
        self.frame.columnconfigure(1, weight=1)
        self._last_th_scan_id = None
        self._build()
        self._tick()

    def _build(self):
        f = self.frame
        row = 0

        # Date/Time
        form_label(f, 'DATE/TIME:', row)
        self._dt_var = tk.StringVar()
        readonly_entry(f, self._dt_var, row)
        row += 1

        # Rack Number
        form_label(f, 'RACK NUMBER:', row)
        self._rack_var = tk.StringVar()
        attach_rack_cleaner(self._rack_var)
        self._rack_entry = text_entry(f, self._rack_var, row, font_size=14, ipady=6)
        self._rack_entry.bind('<Return>', self._on_rack_scanned)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(8, 2))
        btn_frame.columnconfigure(0, weight=2)
        btn_frame.columnconfigure(1, weight=1)

        colored_btn(btn_frame, 'SEND TO TH', 'primary',
                    self._on_scan, font_size=12, pady=8).grid(
            row=0, column=0, sticky='ew', padx=(0, 6))

        self._undo_btn = colored_btn(btn_frame, 'Undo Last Scan', 'secondary',
                                     self._on_undo, bold=False, pady=8,
                                     state='disabled')
        self._undo_btn.grid(row=0, column=1, sticky='ew')
        row += 1

        # Status
        self._sv, self._sl = status_label(f, row)
        row += 1

        # Active racks widget
        self._active = ActiveRacksWidget(f)
        self._active.frame.grid(row=row, column=0, columnspan=2,
                                 sticky='nsew', pady=(6, 0))
        f.rowconfigure(row, weight=1)

    def _tick(self):
        self._dt_var.set(now_ist_display())
        self.frame.after(1000, self._tick)

    def _on_rack_scanned(self, _=None):
        scanner_guard(self.frame, [])
        self._on_scan()

    def _on_scan(self, _=None):
        rack = normalise_rack_number(self._rack_var.get())
        if not rack:
            self._set_status('Rack Number is required.', 'error')
            return

        ok_scan = database.get_active_rack(rack)
        if not ok_scan:
            self._set_status(
                f"Rack {rack} is not in FG. Scan it as OK first.", 'error')
            self._rack_entry.focus()
            return

        lock = check_th_completion_lock(rack)
        if lock:
            if not ask_yes_no('Recent TH Lock', lock.message):
                self._rack_entry.focus()
                return

        from th_verify_dialog import show_th_verify_dialog
        taken_by = show_th_verify_dialog(ok_scan, self.frame.winfo_toplevel())
        if not taken_by:
            self._rack_entry.focus()
            return

        th_id = database.insert_th_scan(
            ok_scan_id=ok_scan['id'],
            rack_number=ok_scan['rack_number'],
            model=ok_scan['model'],
            quantity=ok_scan['quantity'],
            inspected_by=ok_scan['inspected_by'],
            taken_by=taken_by,
        )
        self._last_th_scan_id = th_id
        self._undo_btn.config(state='normal')
        self._set_status(
            f"Rack {rack} sent to TH. Taken by: {taken_by}", 'success')
        self._rack_var.set('')
        self._active.refresh()
        self._rack_entry.focus()

    def _on_undo(self):
        if self._last_th_scan_id is None:
            return
        if ask_yes_no('Undo Last Scan',
                      'Remove the last TH scan? The rack will return to active racks.'):
            database.delete_th_scan(self._last_th_scan_id)
            self._last_th_scan_id = None
            self._undo_btn.config(state='disabled')
            self._set_status('Last TH scan undone. Rack is active again.', 'warning')
            self._active.refresh()

    def _set_status(self, msg, status):
        self._sl.config(fg=STATUS_FG.get(status, '#212529'))
        self._sv.set(msg)

    def on_activate(self):
        self._active.refresh()
        self._rack_entry.focus()
