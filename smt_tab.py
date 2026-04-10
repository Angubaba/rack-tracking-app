"""SMT Handover tab — SMT operator hands over a rack to QC."""
import tkinter as tk
from tkinter import ttk

import database
import settings
from logic import perform_smt_handover
from utils import now_ist_display, normalise_rack_number
from pending_qc_widget import PendingQCWidget
from ui_helpers import (
    BG, colored_btn, form_label, readonly_entry, text_entry,
    status_label, make_upper, STATUS_FG,
)


class SMTTab:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=14)
        self.frame.columnconfigure(1, weight=1)
        self._last_smt_id = None
        self._autocomplete_models = []
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
        self._rack_entry = text_entry(f, self._rack_var, row, font_size=14, ipady=6)
        self._rack_entry.bind('<Return>', lambda e: self._line_entry.focus())
        row += 1

        # Line
        form_label(f, 'LINE:', row)
        self._line_var = tk.StringVar()
        self._line_entry = text_entry(f, self._line_var, row)
        self._line_entry.bind('<Return>', lambda e: self._model_entry.focus())
        row += 1

        # Model (with autocomplete)
        form_label(f, 'MODEL:', row)
        self._model_var = tk.StringVar()
        self._model_entry = text_entry(f, self._model_var, row)
        self._model_entry.bind('<Return>', lambda e: self._qty_entry.focus())
        self._model_entry.bind('<KeyRelease>', self._on_model_key)
        self._model_entry.bind('<FocusOut>', self._hide_autocomplete)
        self._model_entry.bind('<Down>', self._ac_focus_list)
        row += 1

        # Autocomplete dropdown (hidden by default)
        self._ac_var = tk.StringVar()
        self._ac_lb = tk.Listbox(f, font=('Segoe UI', 11), height=5,
                                  relief='solid', bd=1,
                                  selectmode='browse', activestyle='none',
                                  bg='white', fg='#212529',
                                  selectbackground='#1971c2', selectforeground='white')
        self._ac_lb.bind('<<ListboxSelect>>', self._on_ac_select)
        self._ac_lb.bind('<Return>', self._on_ac_select)
        self._ac_lb.bind('<Escape>', self._hide_autocomplete)
        self._ac_lb.bind('<FocusOut>', self._hide_autocomplete)
        # Not gridded yet — shown dynamically at row for MODEL
        self._ac_row = row - 1   # will overlay below model row

        # Quantity (plain entry, starts blank)
        form_label(f, 'QUANTITY:', row)
        self._qty_var = tk.StringVar()
        qty_frame = ttk.Frame(f)
        qty_frame.grid(row=row, column=1, sticky='w', pady=3)
        self._qty_entry = ttk.Entry(qty_frame, textvariable=self._qty_var,
                                    font=('Segoe UI', 12), width=10)
        self._qty_entry.pack(side='left', ipady=4)
        self._qty_entry.bind('<Return>', lambda e: self._op_entry.focus())
        row += 1

        # SMT Operator
        form_label(f, 'SMT OPERATOR:', row)
        self._op_var = tk.StringVar()
        self._op_entry = text_entry(f, self._op_var, row)
        self._op_entry.bind('<Return>', self._on_handover)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(8, 2))
        btn_frame.columnconfigure(0, weight=2)
        btn_frame.columnconfigure(1, weight=1)

        self._ho_btn = colored_btn(btn_frame, 'HAND OVER TO QC', 'warning',
                                   self._on_handover, font_size=12, pady=8)
        self._ho_btn.grid(row=0, column=0, sticky='ew', padx=(0, 6))

        self._undo_btn = colored_btn(btn_frame, 'Undo Last', 'secondary',
                                     self._on_undo, bold=False, pady=8,
                                     state='disabled')
        self._undo_btn.grid(row=0, column=1, sticky='ew')
        row += 1

        # Status
        self._sv, self._sl = status_label(f, row)
        row += 1

        # Pending widget
        self._pending = PendingQCWidget(f)
        self._pending.frame.grid(row=row, column=0, columnspan=2,
                                  sticky='nsew', pady=(6, 0))
        f.rowconfigure(row, weight=1)

    # ── Autocomplete ──────────────────────────────────────────────────────────

    def _refresh_model_list(self):
        self._autocomplete_models = [m.upper() for m in settings.get_models()]

    def _on_model_key(self, event=None):
        typed = self._model_var.get().strip().upper()
        if not typed:
            self._hide_autocomplete()
            return

        matches = [m for m in self._autocomplete_models if m.startswith(typed)]
        if not matches:
            self._hide_autocomplete()
            return

        self._ac_lb.delete(0, 'end')
        for m in matches:
            self._ac_lb.insert('end', m)

        # Position listbox below MODEL entry
        self._ac_lb.grid(row=self._ac_row + 1, column=1, sticky='ew', pady=(0, 2))
        self._ac_lb.lift()

    def _hide_autocomplete(self, event=None):
        # Delay slightly so a click on the listbox registers first
        self.frame.after(100, self._ac_lb.grid_remove)

    def _ac_focus_list(self, event=None):
        if self._ac_lb.winfo_ismapped():
            self._ac_lb.focus_set()
            if self._ac_lb.size() > 0:
                self._ac_lb.selection_set(0)
                self._ac_lb.activate(0)

    def _on_ac_select(self, event=None):
        sel = self._ac_lb.curselection()
        if not sel:
            return
        value = self._ac_lb.get(sel[0])
        self._model_var.set(value)
        self._ac_lb.grid_remove()
        self._qty_entry.focus()

    # ── Tick ─────────────────────────────────────────────────────────────────

    def _tick(self):
        self._dt_var.set(now_ist_display())
        self.frame.after(1000, self._tick)

    # ── Handover ─────────────────────────────────────────────────────────────

    def _on_handover(self, _=None):
        rack     = normalise_rack_number(self._rack_var.get())
        line     = self._line_var.get().strip().upper()
        model    = self._model_var.get().strip().upper()
        operator = self._op_var.get().strip().upper()
        qty_raw  = self._qty_var.get().strip()

        if not qty_raw:
            self._set_status('Quantity is required.', 'error')
            self._qty_entry.focus()
            return
        try:
            qty = int(qty_raw)
            if qty < 1:
                raise ValueError
        except ValueError:
            self._set_status('Quantity must be a whole number ≥ 1.', 'error')
            self._qty_entry.focus()
            return

        valid_models = settings.get_models()
        if valid_models and model not in [m.upper() for m in valid_models]:
            self._set_status(
                f"'{model}' is not a valid model. Check Settings to add it.", 'error')
            self._model_entry.focus()
            return

        result = perform_smt_handover(rack, model, qty, operator, line)
        self._set_status(result.message, result.status)

        if result.success:
            self._last_smt_id = result.scan_id
            self._undo_btn.config(state='normal')
            for v in (self._rack_var, self._line_var, self._model_var, self._op_var):
                v.set('')
            self._qty_var.set('')
            self._pending.refresh()

        self._rack_entry.focus()

    def _on_undo(self):
        if self._last_smt_id is None:
            return
        smt = database.get_smt_handover_by_id(self._last_smt_id)
        if smt and smt['status'] != 'PENDING':
            from ui_helpers import show_warning
            show_warning('Cannot Undo',
                'This handover has already been processed by QC.')
            return
        from ui_helpers import ask_yes_no
        if ask_yes_no('Undo Last Handover',
                      'Remove the last SMT handover from Pending for QC?'):
            database.delete_smt_handover(self._last_smt_id)
            self._last_smt_id = None
            self._undo_btn.config(state='disabled')
            self._set_status('Last handover undone.', 'warning')
            self._pending.refresh()

    def _set_status(self, msg, status):
        self._sl.config(fg=STATUS_FG.get(status, '#212529'))
        self._sv.set(msg)

    def on_activate(self):
        self._refresh_model_list()
        self._pending.refresh()
        self._rack_entry.focus()
