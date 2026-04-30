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
    status_label, make_upper, STATUS_FG, scanner_guard, attach_rack_cleaner,
    attach_rack_blocker, ask_yes_no,
)


class SMTTab:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=14)
        self.frame.columnconfigure(1, weight=1)
        self._last_smt_id = None
        self._cards_override = None
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
        attach_rack_cleaner(self._rack_var)
        self._rack_entry = text_entry(f, self._rack_var, row, font_size=14, ipady=6)
        self._rack_entry.bind('<Return>', self._on_rack_scanned)
        row += 1

        # Line
        form_label(f, 'LINE:', row)
        self._line_var = tk.StringVar()
        attach_rack_blocker(self._line_var,
            lambda: self._set_status(
                'Rack barcode scanned into wrong field — use RACK NUMBER.', 'error'))
        self._line_entry = text_entry(f, self._line_var, row)
        self._line_entry.bind('<Return>', lambda e: self._model_entry.focus())
        row += 1

        # Model (with autocomplete)
        form_label(f, 'MODEL:', row)
        self._model_var = tk.StringVar()
        attach_rack_blocker(self._model_var,
            lambda: self._set_status(
                'Rack barcode scanned into wrong field — use RACK NUMBER.', 'error'))
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
        self._ac_lb.bind('<ButtonRelease-1>', self._on_ac_select)
        self._ac_lb.bind('<Return>', self._on_ac_select)
        self._ac_lb.bind('<Escape>', self._hide_autocomplete)
        self._ac_lb.bind('<FocusOut>', self._hide_autocomplete)
        # Not gridded yet — shown dynamically at row for MODEL
        self._ac_row = row - 1   # will overlay below model row

        # Panels (quantity)
        form_label(f, 'PANELS:', row)
        self._qty_var = tk.StringVar()
        self._qty_var.trace_add('write', self._on_qty_change)
        self._model_var.trace_add('write', self._on_qty_change)
        qty_frame = ttk.Frame(f)
        qty_frame.grid(row=row, column=1, sticky='w', pady=3)
        self._qty_entry = ttk.Entry(qty_frame, textvariable=self._qty_var,
                                    font=('Segoe UI', 12), width=10)
        self._qty_entry.pack(side='left', ipady=4)
        self._qty_entry.bind('<Return>', lambda e: self._op_entry.focus())
        row += 1

        # Cards (computed, readonly — with manual override button)
        form_label(f, 'CARDS:', row)
        self._cards_var = tk.StringVar(value='—')
        cards_frame = ttk.Frame(f)
        cards_frame.grid(row=row, column=1, sticky='w', pady=3)
        self._cards_entry = tk.Entry(
            cards_frame, textvariable=self._cards_var, state='readonly',
            font=('Segoe UI', 11), bg='#e7f5ff', fg='#1864ab',
            readonlybackground='#e7f5ff', relief='solid', bd=1, width=14)
        self._cards_entry.pack(side='left', ipady=4)
        self._edit_cards_btn = colored_btn(
            cards_frame, 'Edit', 'secondary',
            self._on_edit_cards, bold=False, pady=4)
        self._edit_cards_btn.pack(side='left', padx=(6, 0))
        row += 1

        # SMT Operator
        form_label(f, 'SMT OPERATOR:', row)
        self._op_var = tk.StringVar()
        attach_rack_blocker(self._op_var,
            lambda: self._set_status(
                'Rack barcode scanned into wrong field — use RACK NUMBER.', 'error'))
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

    def _on_rack_scanned(self, _=None):
        scanner_guard(self._rack_entry, [
            self._line_entry, self._model_entry,
            self._qty_entry, self._op_entry,
        ])
        self._line_entry.focus()

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
        value = self._ac_lb.get(idx)
        self._model_var.set(value)
        self._ac_lb.grid_remove()
        self._qty_entry.focus()

    # ── Cards computation ─────────────────────────────────────────────────────

    def _on_qty_change(self, *_):
        if not hasattr(self, '_cards_var'):
            return
        # Clear any manual override when qty or model changes
        self._cards_override = None
        if hasattr(self, '_cards_entry'):
            self._cards_entry.config(readonlybackground='#e7f5ff', bg='#e7f5ff')
        if hasattr(self, '_edit_cards_btn'):
            self._edit_cards_btn.config(text='Edit')
        model = self._model_var.get().strip().upper()
        qty_raw = self._qty_var.get().strip()
        try:
            qty = int(qty_raw)
            if qty >= 1 and model:
                cpp = settings.get_cards_per_panel(model)
                self._cards_var.set(str(qty * cpp))
            else:
                self._cards_var.set('—')
        except ValueError:
            self._cards_var.set('—')

    # ── Manual cards override ─────────────────────────────────────────────────

    def _on_edit_cards(self):
        current = self._cards_var.get()
        label = 'manually set' if self._cards_override is not None else 'auto-calculated'
        if not ask_yes_no(
            'Override Card Count',
            f'Cards are currently {label} as {current}.\n\n'
            'Some cards may be crossed out. Override with a manual count?'
        ):
            return

        dlg = tk.Toplevel(self.frame.winfo_toplevel())
        dlg.title('Enter Card Count')
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self.frame.winfo_toplevel())

        frm = ttk.Frame(dlg, padding=20)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text='Enter actual card count:',
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w')

        cards_var = tk.StringVar(value=current if current != '—' else '')
        entry = ttk.Entry(frm, textvariable=cards_var,
                          font=('Segoe UI', 14), width=12)
        entry.pack(fill='x', pady=(8, 4), ipady=6)

        err_var = tk.StringVar()
        tk.Label(frm, textvariable=err_var, font=('Segoe UI', 10),
                 fg='#c92a2a', bg=BG).pack(anchor='w', pady=(0, 8))

        result = [None]

        def _confirm(_=None):
            try:
                n = int(cards_var.get().strip())
                if n < 0:
                    raise ValueError
                result[0] = n
                dlg.destroy()
            except ValueError:
                err_var.set('Enter a valid whole number ≥ 0.')

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill='x')
        colored_btn(btn_row, 'Cancel', 'secondary',
                    dlg.destroy, bold=False, pady=5).pack(side='left', padx=(0, 8))
        colored_btn(btn_row, 'Set Cards', 'warning',
                    _confirm, pady=5).pack(side='left')

        entry.bind('<Return>', _confirm)
        entry.focus()
        entry.select_range(0, 'end')
        dlg.wait_window()

        if result[0] is not None:
            self._cards_override = result[0]
            self._cards_var.set(str(result[0]))
            self._cards_entry.config(readonlybackground='#fff3bf', bg='#fff3bf')
            self._edit_cards_btn.config(text='Edit (manual)')

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

        result = perform_smt_handover(rack, model, qty, operator, line,
                                      cards=self._cards_override)
        self._set_status(result.message, result.status)

        if result.success:
            self._last_smt_id = result.scan_id
            self._undo_btn.config(state='normal')
            for v in (self._rack_var, self._line_var, self._model_var, self._op_var):
                v.set('')
            self._qty_var.set('')
            self._cards_var.set('—')
            self._cards_override = None
            self._cards_entry.config(readonlybackground='#e7f5ff', bg='#e7f5ff')
            self._edit_cards_btn.config(text='Edit')
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
