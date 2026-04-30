"""Trolley/Tray tab — direct TH dispatch without a QC rack scan."""
import re
import tkinter as tk
from tkinter import ttk

import database
import settings
from utils import now_ist_display
from ui_helpers import (
    BG, colored_btn, form_label, text_entry, readonly_entry,
    status_label, STATUS_FG, attach_rack_blocker, scanner_guard,
)

TROLLEY_PATTERN = re.compile(r'^T\d+$', re.IGNORECASE)


class TrolleyTab:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=14)
        self.frame.columnconfigure(1, weight=1)
        self._last_scan_id = None
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

        # Type selection
        form_label(f, 'TYPE:', row)
        type_frame = ttk.Frame(f)
        type_frame.grid(row=row, column=1, sticky='w', pady=3)
        self._type_var = tk.StringVar(value='TROLLEY')
        ttk.Radiobutton(type_frame, text='Trolley', variable=self._type_var,
                        value='TROLLEY', command=self._on_type_change).pack(side='left', padx=(0, 24))
        ttk.Radiobutton(type_frame, text='Tray', variable=self._type_var,
                        value='TRAY', command=self._on_type_change).pack(side='left')
        row += 1

        # Trolley Number (hidden when Tray is selected)
        self._trolley_lbl = form_label(f, 'TROLLEY NO.:', row)
        self._trolley_var = tk.StringVar()
        self._trolley_entry = text_entry(f, self._trolley_var, row, font_size=14, ipady=6)
        self._trolley_entry.bind('<Return>', self._on_trolley_scanned)
        row += 1

        # Model (with autocomplete)
        form_label(f, 'MODEL:', row)
        self._model_var = tk.StringVar()
        attach_rack_blocker(self._model_var,
            lambda: self._set_status(
                'Rack barcode scanned into wrong field — use RACK NUMBER on another tab.', 'error'))
        self._model_entry = text_entry(f, self._model_var, row)
        self._model_entry.bind('<Return>', lambda e: self._qty_entry.focus())
        self._model_entry.bind('<KeyRelease>', self._on_model_key)
        self._model_entry.bind('<FocusOut>', self._hide_autocomplete)
        self._model_entry.bind('<Down>', self._ac_focus_list)
        self._ac_row = row

        # Autocomplete listbox
        self._ac_lb = tk.Listbox(f, font=('Segoe UI', 11), height=5,
                                  relief='solid', bd=1, selectmode='browse',
                                  activestyle='none', bg='white', fg='#212529',
                                  selectbackground='#1971c2', selectforeground='white')
        self._ac_lb.bind('<ButtonRelease-1>', self._on_ac_select)
        self._ac_lb.bind('<Return>', self._on_ac_select)
        self._ac_lb.bind('<Escape>', self._hide_autocomplete)
        self._ac_lb.bind('<FocusOut>', self._hide_autocomplete)
        row += 1

        # Panels
        form_label(f, 'PANELS:', row)
        self._qty_var = tk.StringVar()
        self._qty_var.trace_add('write', self._on_qty_change)
        self._model_var.trace_add('write', self._on_qty_change)
        qty_frame = ttk.Frame(f)
        qty_frame.grid(row=row, column=1, sticky='w', pady=3)
        self._qty_entry = ttk.Entry(qty_frame, textvariable=self._qty_var,
                                    font=('Segoe UI', 12), width=10)
        self._qty_entry.pack(side='left', ipady=4)
        self._qty_entry.bind('<Return>', lambda e: self._taken_entry.focus())
        row += 1

        # Cards (computed, readonly)
        form_label(f, 'CARDS:', row)
        self._cards_var = tk.StringVar(value='—')
        tk.Entry(f, textvariable=self._cards_var, state='readonly',
                 font=('Segoe UI', 11), bg='#e7f5ff', fg='#1864ab',
                 readonlybackground='#e7f5ff', relief='solid', bd=1,
                 width=14).grid(row=row, column=1, sticky='w', pady=3, ipady=4)
        row += 1

        # Taken By
        form_label(f, 'TAKEN BY:', row)
        self._taken_var = tk.StringVar()
        attach_rack_blocker(self._taken_var,
            lambda: self._set_status(
                'Rack barcode scanned into wrong field.', 'error'))
        self._taken_entry = text_entry(f, self._taken_var, row)
        self._taken_entry.bind('<Return>', self._on_submit)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(8, 2))
        btn_frame.columnconfigure(0, weight=2)
        btn_frame.columnconfigure(1, weight=1)

        self._submit_btn = colored_btn(btn_frame, 'SEND TO TH', 'primary',
                                       self._on_submit, font_size=12, pady=8)
        self._submit_btn.grid(row=0, column=0, sticky='ew', padx=(0, 6))

        self._undo_btn = colored_btn(btn_frame, 'Undo Last', 'secondary',
                                     self._on_undo, bold=False, pady=8,
                                     state='disabled')
        self._undo_btn.grid(row=0, column=1, sticky='ew')
        row += 1

        # Status
        self._sv, self._sl = status_label(f, row)

    # ── Type radio ────────────────────────────────────────────────────────────

    def _on_type_change(self):
        if self._type_var.get() == 'TRAY':
            self._trolley_lbl.grid_remove()
            self._trolley_entry.grid_remove()
            self._model_entry.focus()
        else:
            self._trolley_lbl.grid()
            self._trolley_entry.grid()
            self._trolley_entry.focus()

    # ── Scanner guard on trolley number field ─────────────────────────────────

    def _on_trolley_scanned(self, _=None):
        scanner_guard(self._trolley_entry, [
            self._model_entry, self._qty_entry, self._taken_entry,
        ])
        self._model_entry.focus()

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
        self._ac_lb.grid(row=self._ac_row + 1, column=1, sticky='ew', pady=(0, 2))
        self._ac_lb.lift()

    def _hide_autocomplete(self, event=None):
        def _check():
            try:
                focus = self.frame.winfo_toplevel().focus_get()
            except Exception:
                focus = None
            if focus is not self._ac_lb:
                self._ac_lb.grid_remove()
        self.frame.after(150, _check)

    def _ac_focus_list(self, event=None):
        if self._ac_lb.winfo_ismapped():
            self._ac_lb.focus_set()
            if self._ac_lb.size() > 0:
                self._ac_lb.activate(0)
                self._ac_lb.see(0)

    def _on_ac_select(self, event=None):
        sel = self._ac_lb.curselection()
        active = self._ac_lb.index('active')
        idx = sel[0] if sel else (active if active >= 0 else None)
        if idx is None:
            return
        self._model_var.set(self._ac_lb.get(idx))
        self._ac_lb.grid_remove()
        self._qty_entry.focus()

    # ── Cards ─────────────────────────────────────────────────────────────────

    def _on_qty_change(self, *_):
        model = self._model_var.get().strip().upper()
        try:
            qty = int(self._qty_var.get().strip())
            if qty >= 1 and model:
                self._cards_var.set(str(qty * settings.get_cards_per_panel(model)))
                return
        except ValueError:
            pass
        self._cards_var.set('—')

    def _tick(self):
        self._dt_var.set(now_ist_display())
        self.frame.after(1000, self._tick)

    # ── Submit ────────────────────────────────────────────────────────────────

    def _on_submit(self, _=None):
        type_ = self._type_var.get()

        if type_ == 'TROLLEY':
            identifier = self._trolley_var.get().strip().upper()
            if not identifier:
                self._set_status('Trolley number is required.', 'error')
                self._trolley_entry.focus()
                return
            if not TROLLEY_PATTERN.match(identifier):
                self._set_status(
                    f"Invalid trolley number '{identifier}'. Expected format: T01, T02, etc.", 'error')
                self._trolley_entry.focus()
                return
        else:
            identifier = 'TRAY'

        model = self._model_var.get().strip().upper()
        if not model:
            self._set_status('Model is required.', 'error')
            self._model_entry.focus()
            return
        valid_models = settings.get_models()
        if valid_models and model not in [m.upper() for m in valid_models]:
            self._set_status(f"'{model}' is not a valid model.", 'error')
            self._model_entry.focus()
            return

        qty_raw = self._qty_var.get().strip()
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

        taken_by = self._taken_var.get().strip().upper()
        if not taken_by:
            self._set_status('Taken By is required.', 'error')
            self._taken_entry.focus()
            return

        cards = qty * settings.get_cards_per_panel(model)
        scan_id = database.insert_trolley_scan(type_, identifier, model, qty, taken_by, cards)
        self._last_scan_id = scan_id
        self._undo_btn.config(state='normal')
        label = identifier if type_ == 'TROLLEY' else 'Tray'
        self._set_status(
            f"{label} sent to TH — {model}, {qty} panels / {cards} cards.", 'success')
        self._clear_form()

    def _on_undo(self):
        if self._last_scan_id is None:
            return
        from ui_helpers import ask_yes_no
        if ask_yes_no('Undo Last', 'Remove the last trolley/tray record?'):
            database.delete_trolley_scan(self._last_scan_id)
            self._last_scan_id = None
            self._undo_btn.config(state='disabled')
            self._set_status('Last record undone.', 'warning')

    def _clear_form(self):
        self._trolley_var.set('')
        self._model_var.set('')
        self._qty_var.set('')
        self._cards_var.set('—')
        self._taken_var.set('')
        if self._type_var.get() == 'TROLLEY':
            self._trolley_entry.focus()
        else:
            self._model_entry.focus()

    def _set_status(self, msg, status):
        self._sl.config(fg=STATUS_FG.get(status, '#212529'))
        self._sv.set(msg)

    def on_activate(self):
        self._refresh_model_list()
        if self._type_var.get() == 'TROLLEY':
            self._trolley_entry.focus()
        else:
            self._model_entry.focus()
