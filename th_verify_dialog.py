"""TH verification dialog — confirms rack details and collects 'Taken By'."""
import tkinter as tk
from tkinter import ttk

from utils import to_ist
from ui_helpers import colored_btn, BG


def show_th_verify_dialog(ok_scan, parent) -> str:
    """
    Show the verification dialog for sending a rack to TH.
    Returns the 'taken_by' string, or '' if cancelled.
    """
    dlg = _THVerifyDialog(parent, ok_scan)
    parent.wait_window(dlg.window)
    return dlg.taken_by


class _THVerifyDialog:
    def __init__(self, parent, ok_scan):
        self.taken_by = ''
        self._ok_scan = ok_scan

        win = tk.Toplevel(parent)
        self.window = win
        win.title('Verify — Send Rack to TH')
        win.minsize(460, 340)
        win.resizable(False, False)
        win.grab_set()

        root = ttk.Frame(win, padding=16)
        root.pack(fill='both', expand=True)
        root.columnconfigure(0, weight=1)

        ttk.Label(root, text='Confirm Rack Details',
                  font=('Segoe UI', 14, 'bold')).grid(
            row=0, column=0, sticky='w', pady=(0, 8))

        # Details card
        card = tk.Frame(root, bg='#f1f3f5', relief='solid', bd=1)
        card.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        card.columnconfigure(1, weight=1)

        fields = [
            ('Rack Number',  ok_scan['rack_number']),
            ('Model',        ok_scan['model']),
            ('Quantity',     str(ok_scan['quantity'])),
            ('Inspected By', ok_scan['inspected_by']),
            ('In FG Since',  to_ist(ok_scan['created_at'])),
        ]
        for r, (label, value) in enumerate(fields):
            tk.Label(card, text=f"{label}:", font=('Segoe UI', 11, 'bold'),
                     bg='#f1f3f5', anchor='e', width=14).grid(
                row=r, column=0, sticky='e', padx=(10, 6), pady=3)
            tk.Label(card, text=value, font=('Segoe UI', 11),
                     bg='#f1f3f5', anchor='w').grid(
                row=r, column=1, sticky='w', pady=3, padx=(0, 10))

        # Taken By input
        taken_row = ttk.Frame(root)
        taken_row.grid(row=2, column=0, sticky='ew', pady=(0, 4))
        taken_row.columnconfigure(1, weight=1)

        ttk.Label(taken_row, text='TAKEN BY:',
                  font=('Segoe UI', 11, 'bold')).grid(
            row=0, column=0, sticky='e', padx=(0, 8))

        self._taken_var = tk.StringVar()

        def _upper(*_):
            v = self._taken_var.get()
            u = v.upper()
            if v != u:
                self._taken_var.set(u)

        self._taken_var.trace_add('write', _upper)
        self._taken_entry = ttk.Entry(taken_row, textvariable=self._taken_var,
                                      font=('Segoe UI', 12))
        self._taken_entry.grid(row=0, column=1, sticky='ew', ipady=5)
        self._taken_entry.bind('<Return>', self._on_confirm)

        self._err_var = tk.StringVar()
        tk.Label(root, textvariable=self._err_var, font=('Segoe UI', 10),
                 fg='#c92a2a', bg=BG).grid(row=3, column=0, sticky='w')

        # Buttons
        btn_row = ttk.Frame(root)
        btn_row.grid(row=4, column=0, sticky='e', pady=(8, 0))

        colored_btn(btn_row, 'Cancel', 'secondary',
                    win.destroy, bold=False, pady=6).pack(side='left', padx=(0, 8))
        colored_btn(btn_row, 'Confirm — Send to TH', 'primary',
                    self._on_confirm, font_size=12, pady=6).pack(side='left')

        self._taken_entry.focus()

    def _on_confirm(self, _=None):
        taken_by = self._taken_var.get().strip()
        if not taken_by:
            self._err_var.set('Taken By is required.')
            return
        self.taken_by = taken_by
        self.window.destroy()
