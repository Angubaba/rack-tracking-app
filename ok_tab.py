"""QC tab — processes racks from Pending for QC, marks OK or NOT OK."""
import tkinter as tk
from tkinter import ttk, simpledialog

import database
from utils import now_ist_display, normalise_rack_number
from pending_qc_widget import PendingQCWidget
from ui_helpers import (
    BG, colored_btn, form_label, readonly_entry, text_entry,
    status_label, make_upper, STATUS_FG, ask_yes_no, show_warning, scanner_guard,
    attach_rack_cleaner,
)


class OKTab:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=14)
        self.frame.columnconfigure(1, weight=1)
        self._last_action = None
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

        # Model (auto-filled, readonly)
        form_label(f, 'MODEL:', row)
        self._model_var = tk.StringVar()
        model_entry = tk.Entry(f, textvariable=self._model_var, state='readonly',
                               font=('Segoe UI', 11), bg='#e7f5ff', fg='#1864ab',
                               readonlybackground='#e7f5ff', relief='solid', bd=1)
        model_entry.grid(row=row, column=1, sticky='ew', pady=3, ipady=4)
        row += 1

        # Quantity (auto-filled, readonly)
        form_label(f, 'QUANTITY:', row)
        self._qty_var = tk.StringVar()
        qty_frame = ttk.Frame(f)
        qty_frame.grid(row=row, column=1, sticky='w', pady=3)
        qty_entry = tk.Entry(qty_frame, textvariable=self._qty_var, state='readonly',
                             font=('Segoe UI', 11), width=12, bg='#e7f5ff', fg='#1864ab',
                             readonlybackground='#e7f5ff', relief='solid', bd=1)
        qty_entry.pack(side='left', ipady=4)
        row += 1

        # Inspected By
        form_label(f, 'INSPECTED BY:', row)
        self._inspector_var = tk.StringVar()
        make_upper(self._inspector_var)
        self._inspector_entry = text_entry(f, self._inspector_var, row)
        self._inspector_entry.bind('<Return>', self._on_mark_ok)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(8, 2))
        btn_frame.columnconfigure(0, weight=2)
        btn_frame.columnconfigure(1, weight=2)
        btn_frame.columnconfigure(2, weight=1)

        colored_btn(btn_frame, 'MARK OK', 'success',
                    self._on_mark_ok, font_size=12, pady=8).grid(
            row=0, column=0, sticky='ew', padx=(0, 6))

        colored_btn(btn_frame, 'MARK NOT OK', 'danger',
                    self._on_mark_not_ok, font_size=12, pady=8).grid(
            row=0, column=1, sticky='ew', padx=(0, 6))

        self._undo_btn = colored_btn(btn_frame, 'Undo Last', 'secondary',
                                     self._on_undo, bold=False, pady=8,
                                     state='disabled')
        self._undo_btn.grid(row=0, column=2, sticky='ew')
        row += 1

        # Status
        self._sv, self._sl = status_label(f, row)
        row += 1

        # Pending widget
        self._pending = PendingQCWidget(f)
        self._pending.frame.grid(row=row, column=0, columnspan=2,
                                  sticky='nsew', pady=(6, 0))
        f.rowconfigure(row, weight=1)

    def _tick(self):
        self._dt_var.set(now_ist_display())
        self.frame.after(1000, self._tick)

    def _on_rack_scanned(self, _=None):
        scanner_guard(self.frame, [self._inspector_entry])
        self._on_rack_entered()

    def _on_rack_entered(self, _=None):
        rack = normalise_rack_number(self._rack_var.get())
        if not rack:
            return
        pending = database.get_pending_rack(rack)
        if pending:
            self._model_var.set(pending['model'])
            self._qty_var.set(str(pending['quantity']))
            self._set_status(
                f"Rack {rack} found — {pending['model']}, qty {pending['quantity']}.",
                'success')
            self._inspector_entry.focus()
        else:
            self._model_var.set('')
            self._qty_var.set('')
            self._set_status(f"Rack {rack} is not in Pending for QC.", 'error')

    def _validate_form(self):
        """Returns (rack, pending, inspector) or None if validation fails."""
        rack = normalise_rack_number(self._rack_var.get())
        if not rack:
            self._set_status('Rack Number is required.', 'error')
            self._rack_entry.focus()
            return None
        pending = database.get_pending_rack(rack)
        if not pending:
            self._set_status(f"Rack {rack} is not in Pending for QC.", 'error')
            self._rack_entry.focus()
            return None
        inspector = self._inspector_var.get().strip().upper()
        if not inspector:
            self._set_status('Inspected By is required.', 'error')
            self._inspector_entry.focus()
            return None
        return rack, pending, inspector

    def _on_mark_ok(self, _=None):
        result = self._validate_form()
        if not result:
            return
        rack, pending, inspector = result
        ok_scan_id = database.mark_qc_ok(
            smt_handover_id=pending['id'],
            rack_number=pending['rack_number'],
            model=pending['model'],
            quantity=pending['quantity'],
            inspected_by=inspector,
            pcb_ids=[],
        )
        self._last_action = ('OK', pending['id'], ok_scan_id)
        self._undo_btn.config(state='normal')
        self._set_status(f"Rack {rack} marked OK — added to Racks in FG.", 'success')
        self._clear_form()
        self._pending.refresh()
        self._rack_entry.focus()

    def _on_mark_not_ok(self, _=None):
        result = self._validate_form()
        if not result:
            return
        rack, pending, inspector = result
        reason = self._ask_reason()
        if reason is None:
            self._rack_entry.focus()
            return
        database.mark_qc_not_ok(pending['id'], reason)
        self._last_action = ('NOT_OK', pending['id'])
        self._undo_btn.config(state='normal')
        self._set_status(f"Rack {rack} marked NOT OK — returned to SMT.", 'warning')
        self._clear_form()
        self._pending.refresh()
        self._rack_entry.focus()

    def _ask_reason(self):
        """Show a small dialog to collect the NOT OK reason. Returns str or None."""
        dlg = tk.Toplevel(self.frame.winfo_toplevel())
        dlg.title('NOT OK — Enter Reason')
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self.frame.winfo_toplevel())

        frm = ttk.Frame(dlg, padding=16)
        frm.pack(fill='both', expand=True)
        ttk.Label(frm, text='Reason for NOT OK:',
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        reason_var = tk.StringVar()
        entry = ttk.Entry(frm, textvariable=reason_var,
                          font=('Segoe UI', 12), width=38)
        entry.pack(fill='x', pady=(6, 12), ipady=4)

        result = [None]

        def _confirm(_=None):
            r = reason_var.get().strip()
            if not r:
                return
            result[0] = r.upper()
            dlg.destroy()

        def _cancel():
            dlg.destroy()

        entry.bind('<Return>', _confirm)
        btn_row = ttk.Frame(frm)
        btn_row.pack(fill='x')
        from ui_helpers import colored_btn as cbtn
        cbtn(btn_row, 'Cancel', 'secondary', _cancel,
             bold=False, pady=5).pack(side='left', padx=(0, 8))
        cbtn(btn_row, 'Confirm NOT OK', 'danger', _confirm,
             pady=5).pack(side='left')

        entry.focus()
        dlg.wait_window()
        return result[0]

    def _on_undo(self):
        if not self._last_action:
            return
        action = self._last_action[0]
        if action == 'OK':
            _, smt_id, ok_scan_id = self._last_action
            if ask_yes_no('Undo Last Action',
                          'Undo the last OK scan? The rack will return to Pending for QC.'):
                database.undo_qc_ok(smt_id, ok_scan_id)
                self._set_status('Last OK scan undone. Rack returned to Pending for QC.', 'warning')
        else:
            _, smt_id = self._last_action
            if ask_yes_no('Undo Last Action',
                          'Undo the NOT OK decision? The rack will return to Pending for QC.'):
                database.undo_qc_not_ok(smt_id)
                self._set_status('NOT OK decision undone. Rack returned to Pending for QC.', 'warning')

        self._last_action = None
        self._undo_btn.config(state='disabled')
        self._pending.refresh()

    def _clear_form(self):
        for v in (self._rack_var, self._model_var, self._qty_var, self._inspector_var):
            v.set('')

    def _set_status(self, msg, status):
        self._sl.config(fg=STATUS_FG.get(status, '#212529'))
        self._sv.set(msg)

    def on_activate(self):
        self._pending.refresh()
        self._rack_entry.focus()
