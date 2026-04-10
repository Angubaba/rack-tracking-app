"""Edit dialog for a full lookup cycle (SMT, QC, TH sections)."""
import tkinter as tk
from tkinter import ttk

import database
from utils import validate_rack_number
from ui_helpers import colored_btn, BG, ask_yes_no


def show_edit_dialog(cycle: dict, parent) -> bool:
    """
    Open the edit dialog for a cycle.
    Returns True if the cycle was saved/modified, False if cancelled.
    """
    dlg = _EditCycleDialog(parent, cycle)
    parent.wait_window(dlg.window)
    return dlg.saved


class _EditCycleDialog:
    def __init__(self, parent, cycle: dict):
        self.saved = False
        self._cycle = cycle

        win = tk.Toplevel(parent)
        self.window = win
        win.title(f"Edit Cycle — Rack {cycle['rack_number']}")
        win.minsize(500, 400)
        win.resizable(True, True)
        win.grab_set()

        # Scrollable container
        canvas = tk.Canvas(win, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(win, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        root = ttk.Frame(canvas, padding=16)
        canvas_win = canvas.create_window((0, 0), window=root, anchor='nw')

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox('all'))
            canvas.itemconfigure(canvas_win, width=canvas.winfo_width())

        root.bind('<Configure>', _on_configure)
        canvas.bind('<Configure>', _on_configure)

        root.columnconfigure(1, weight=1)
        self._err_var = tk.StringVar()
        cur_row = [0]

        def next_row():
            r = cur_row[0]; cur_row[0] += 1; return r

        def section(text):
            tk.Label(root, text=text, font=('Segoe UI', 11, 'bold'),
                     fg='#1971c2', bg=BG).grid(
                row=next_row(), column=0, columnspan=2,
                sticky='w', pady=(10, 2))

        def divider():
            ttk.Separator(root, orient='horizontal').grid(
                row=next_row(), column=0, columnspan=2,
                sticky='ew', pady=4)

        def field_row(label, var, readonly=False):
            ttk.Label(root, text=label,
                      font=('Segoe UI', 10, 'bold')).grid(
                row=cur_row[0], column=0, sticky='e', padx=(0, 8), pady=3)
            if readonly:
                e = tk.Entry(root, textvariable=var, state='readonly',
                             font=('Segoe UI', 11), bg='#f1f3f5', fg='#6c757d',
                             readonlybackground='#f1f3f5', relief='solid', bd=1)
            else:
                e = ttk.Entry(root, textvariable=var, font=('Segoe UI', 11))
            e.grid(row=cur_row[0], column=1, sticky='ew', ipady=4, pady=3)
            cur_row[0] += 1
            return e

        def spin_row(label, var, from_=1, to=10000):
            ttk.Label(root, text=label,
                      font=('Segoe UI', 10, 'bold')).grid(
                row=cur_row[0], column=0, sticky='e', padx=(0, 8), pady=3)
            sp = tk.Spinbox(root, textvariable=var, from_=from_, to=to,
                            width=12, font=('Segoe UI', 11),
                            relief='solid', bd=1)
            sp.grid(row=cur_row[0], column=1, sticky='w', ipady=4, pady=3)
            cur_row[0] += 1
            return sp

        # ── SMT HANDOVER ──────────────────────────────────────────────────────
        self._smt_model = self._smt_qty = self._smt_line = self._smt_op = None
        if cycle.get('smt_id'):
            section('SMT HANDOVER')
            rack_ro = tk.StringVar(value=cycle['rack_number'])
            field_row('Rack Number:', rack_ro, readonly=True)
            self._smt_model = tk.StringVar(value=cycle.get('model', ''))
            field_row('Model:', self._smt_model)
            self._smt_qty = tk.IntVar(value=cycle.get('quantity', 1))
            spin_row('Quantity:', self._smt_qty)
            self._smt_line = tk.StringVar(value=cycle.get('line', ''))
            field_row('Line:', self._smt_line)
            self._smt_op = tk.StringVar(value=cycle.get('smt_operator', ''))
            field_row('SMT Operator:', self._smt_op)
            divider()

        # ── QC ────────────────────────────────────────────────────────────────
        self._qc_inspector = self._qc_rack = self._qc_model = self._qc_qty = None
        if cycle.get('ok_scan_id'):
            section('QC')
            if cycle['cycle_type'] == 'legacy':
                self._qc_rack  = tk.StringVar(value=cycle['rack_number'])
                field_row('Rack Number:', self._qc_rack)
                self._qc_model = tk.StringVar(value=cycle.get('model', ''))
                field_row('Model:', self._qc_model)
                self._qc_qty = tk.IntVar(value=cycle.get('quantity', 1))
                spin_row('Quantity:', self._qc_qty)
            self._qc_inspector = tk.StringVar(value=cycle.get('qc_inspector', ''))
            field_row('Inspected By:', self._qc_inspector)
            divider()

        # ── TH ────────────────────────────────────────────────────────────────
        self._th_taken = None
        if cycle.get('th_id'):
            section('TH')
            self._th_taken = tk.StringVar(value=cycle.get('th_taken_by', ''))
            field_row('Taken By:', self._th_taken)
            divider()

        # ── Revert ────────────────────────────────────────────────────────────
        has_th  = bool(cycle.get('th_id'))
        has_ok  = bool(cycle.get('ok_scan_id'))
        has_smt = bool(cycle.get('smt_id'))
        if has_th or (has_ok and has_smt):
            section('REVERT STAGE')
            rev_frame = ttk.Frame(root)
            rev_frame.grid(row=next_row(), column=0, columnspan=2,
                           sticky='ew', pady=(0, 4))
            if has_th:
                colored_btn(rev_frame, 'Undo TH \u2192 Back to Racks in FG',
                            'warning', self._on_undo_th,
                            bold=False, pady=5).pack(side='left', padx=(0, 6))
            if has_ok and has_smt:
                colored_btn(rev_frame, 'Undo QC \u2192 Back to Pending for QC',
                            'danger', self._on_undo_qc,
                            bold=False, pady=5).pack(side='left')
            divider()

        # ── Error + action buttons ────────────────────────────────────────────
        tk.Label(root, textvariable=self._err_var, font=('Segoe UI', 10),
                 fg='#c92a2a', bg=BG, wraplength=440).grid(
            row=next_row(), column=0, columnspan=2, sticky='w')

        bot = ttk.Frame(root)
        bot.grid(row=next_row(), column=0, columnspan=2, sticky='e', pady=(8, 0))
        colored_btn(bot, 'Cancel', 'secondary',
                    win.destroy, bold=False, pady=6).pack(side='left', padx=(0, 8))
        colored_btn(bot, 'Save', 'success',
                    self._on_save, font_size=12, pady=6).pack(side='left')

    # ── Save ──────────────────────────────────────────────────────────────────

    def _on_save(self):
        cycle = self._cycle
        with database._connect() as conn:

            if cycle.get('smt_id'):
                model    = self._smt_model.get().strip().upper()
                quantity = int(self._smt_qty.get())
                line     = self._smt_line.get().strip().upper()
                operator = self._smt_op.get().strip().upper()
                if not model:
                    self._err_var.set('Model is required.'); return
                if not operator:
                    self._err_var.set('SMT Operator is required.'); return
                conn.execute(
                    "UPDATE smt_handovers SET model=?,quantity=?,line=?,smt_operator=? WHERE id=?",
                    (model, quantity, line, operator, cycle['smt_id']))
                if cycle.get('ok_scan_id'):
                    conn.execute(
                        "UPDATE ok_scans SET model=?,quantity=? WHERE id=?",
                        (model, quantity, cycle['ok_scan_id']))
                if cycle.get('th_id'):
                    conn.execute(
                        "UPDATE th_scans SET model=?,quantity=? WHERE id=?",
                        (model, quantity, cycle['th_id']))

            if cycle.get('ok_scan_id'):
                inspector = self._qc_inspector.get().strip().upper()
                if not inspector:
                    self._err_var.set('Inspected By is required.'); return
                if cycle['cycle_type'] == 'legacy':
                    rack  = self._qc_rack.get().strip().upper() if self._qc_rack else cycle['rack_number']
                    model = self._qc_model.get().strip().upper() if self._qc_model else cycle['model']
                    qty   = int(self._qc_qty.get()) if self._qc_qty else cycle['quantity']
                    if not rack:
                        self._err_var.set('Rack Number is required.'); return
                    if not validate_rack_number(rack):
                        self._err_var.set('Expected PR/### or MR/###.'); return
                    if not model:
                        self._err_var.set('Model is required.'); return
                    conn.execute(
                        "UPDATE ok_scans SET rack_number=?,model=?,quantity=?,inspected_by=? WHERE id=?",
                        (rack, model, qty, inspector, cycle['ok_scan_id']))
                    if cycle.get('th_id'):
                        conn.execute(
                            "UPDATE th_scans SET rack_number=?,model=?,quantity=?,inspected_by=?"
                            " WHERE ok_scan_id=?",
                            (rack, model, qty, inspector, cycle['ok_scan_id']))
                else:
                    conn.execute(
                        "UPDATE ok_scans SET inspected_by=? WHERE id=?",
                        (inspector, cycle['ok_scan_id']))
                    if cycle.get('th_id'):
                        conn.execute(
                            "UPDATE th_scans SET inspected_by=? WHERE ok_scan_id=?",
                            (inspector, cycle['ok_scan_id']))

            if cycle.get('th_id'):
                taken_by = self._th_taken.get().strip().upper()
                if not taken_by:
                    self._err_var.set('Taken By is required.'); return
                conn.execute(
                    "UPDATE th_scans SET taken_by=? WHERE id=?",
                    (taken_by, cycle['th_id']))

            conn.commit()

        self.saved = True
        self.window.destroy()

    # ── Revert ────────────────────────────────────────────────────────────────

    def _on_undo_th(self):
        cycle = self._cycle
        if not ask_yes_no('Undo TH',
                          f"Remove the TH record for rack {cycle['rack_number']}?\n"
                          f"The rack will return to Racks in FG."):
            return
        with database._connect() as conn:
            conn.execute("DELETE FROM th_scans WHERE id=?", (cycle['th_id'],))
            conn.commit()
        self.saved = True
        self.window.destroy()

    def _on_undo_qc(self):
        cycle = self._cycle
        msg = (f"Undo the QC result for rack {cycle['rack_number']}?\n"
               f"The OK scan will be deleted.")
        if cycle.get('th_id'):
            msg += '\nThe TH record will also be removed.'
        msg += '\n\nThe rack will return to Pending for QC.'
        if not ask_yes_no('Undo QC', msg):
            return
        database.undo_qc_ok(cycle['smt_id'], cycle['ok_scan_id'])
        self.saved = True
        self.window.destroy()
