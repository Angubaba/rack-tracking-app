"""PCB sampling dialog — scan PCB IDs then make OK / NOT OK decision."""
import tkinter as tk
from tkinter import ttk

import database
from ui_helpers import colored_btn, BG


def show_pcb_dialog(rack_number: str, parent) -> tuple:
    """
    Open the PCB sampling dialog modally.
    Returns (decision, pcb_ids, not_ok_reason) or None if cancelled.
      decision: 'OK' or 'NOT_OK'
      pcb_ids:  list[str]  (populated when decision == 'OK')
      not_ok_reason: str   (populated when decision == 'NOT_OK')
    """
    dlg = _PCBDialog(parent, rack_number)
    parent.wait_window(dlg.window)
    return dlg.result


class _PCBDialog:
    def __init__(self, parent, rack_number: str):
        self.result = None
        self._rack_number = rack_number
        self._pcb_ids = []
        self._historic = database.get_all_pcb_ids_for_rack(rack_number)

        win = tk.Toplevel(parent)
        self.window = win
        win.title('PCB Sampling & QC Decision')
        win.minsize(480, 460)
        win.resizable(True, True)
        win.grab_set()

        root = ttk.Frame(win, padding=16)
        root.pack(fill='both', expand=True)
        root.columnconfigure(0, weight=1)

        # Header
        ttk.Label(root, text='Enter PCB Sample IDs',
                  font=('Segoe UI', 14, 'bold')).grid(
            row=0, column=0, sticky='w', pady=(0, 2))
        ttk.Label(root, text=f"Rack: {rack_number}",
                  font=('Segoe UI', 11, 'bold'), foreground='#1971c2').grid(
            row=1, column=0, sticky='w', pady=(0, 8))

        # Input row
        inp_frame = ttk.Frame(root)
        inp_frame.grid(row=2, column=0, sticky='ew')
        inp_frame.columnconfigure(0, weight=1)

        self._pcb_var = tk.StringVar()
        self._pcb_entry = ttk.Entry(inp_frame, textvariable=self._pcb_var,
                                    font=('Segoe UI', 12))
        self._pcb_entry.grid(row=0, column=0, sticky='ew', ipady=5, padx=(0, 6))
        self._pcb_entry.bind('<Return>', self._add)

        colored_btn(inp_frame, 'Add', 'primary',
                    self._add, pady=4).grid(row=0, column=1)

        # Duplicate warning
        self._dup_var = tk.StringVar()
        tk.Label(root, textvariable=self._dup_var, font=('Segoe UI', 10),
                 fg='#c92a2a', bg=BG, wraplength=440, justify='left').grid(
            row=3, column=0, sticky='w', pady=(2, 0))

        # Count label
        self._count_var = tk.StringVar(value='0 PCBs sampled')
        ttk.Label(root, textvariable=self._count_var,
                  font=('Segoe UI', 10), foreground='#6c757d').grid(
            row=4, column=0, sticky='w', pady=(4, 2))

        # List
        list_frame = ttk.Frame(root)
        list_frame.grid(row=5, column=0, sticky='nsew', pady=(0, 4))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        root.rowconfigure(5, weight=1)

        self._listbox = tk.Listbox(list_frame, font=('Segoe UI', 12),
                                   selectmode='extended', relief='solid', bd=1,
                                   activestyle='none')
        sb = ttk.Scrollbar(list_frame, command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=sb.set)
        self._listbox.grid(row=0, column=0, sticky='nsew')
        sb.grid(row=0, column=1, sticky='ns')

        colored_btn(root, 'Remove Selected', 'danger',
                    self._remove_selected, bold=False, pady=4).grid(
            row=6, column=0, sticky='w', pady=(0, 6))

        # Error label
        self._err_var = tk.StringVar()
        tk.Label(root, textvariable=self._err_var, font=('Segoe UI', 10),
                 fg='#c92a2a', bg=BG).grid(row=7, column=0, sticky='w')

        # Decision buttons
        ttk.Label(root, text='QC Decision:',
                  font=('Segoe UI', 11, 'bold')).grid(
            row=8, column=0, sticky='w', pady=(8, 4))

        dec_frame = ttk.Frame(root)
        dec_frame.grid(row=9, column=0, sticky='ew')
        dec_frame.columnconfigure(0, weight=1)
        dec_frame.columnconfigure(1, weight=1)

        colored_btn(dec_frame, 'MARK NOT OK  \u2192  Return to SMT', 'danger',
                    self._on_not_ok, font_size=11, pady=8).grid(
            row=0, column=0, sticky='ew', padx=(0, 6))

        colored_btn(dec_frame, 'MARK OK  \u2192  Add to FG', 'success',
                    self._on_ok, font_size=11, pady=8).grid(
            row=0, column=1, sticky='ew')

        self._pcb_entry.focus()

    # ── actions ───────────────────────────────────────────────────────────────

    def _add(self, _=None):
        pcb_id = self._pcb_var.get().strip().upper()
        if not pcb_id:
            return
        if pcb_id in self._pcb_ids:
            self._dup_var.set(f"{pcb_id} already added in this session.")
            self._pcb_entry.select_range(0, 'end')
            return
        if pcb_id in self._historic:
            self._dup_var.set(
                f"{pcb_id} was already sampled for rack {self._rack_number} in a previous scan.")
            self._pcb_entry.select_range(0, 'end')
            return
        self._dup_var.set('')
        self._err_var.set('')
        self._pcb_ids.append(pcb_id)
        self._listbox.insert('end', pcb_id)
        self._pcb_var.set('')
        self._count_var.set(f"{len(self._pcb_ids)} PCB(s) sampled")

    def _remove_selected(self):
        for idx in reversed(self._listbox.curselection()):
            pid = self._listbox.get(idx)
            self._pcb_ids.remove(pid)
            self._listbox.delete(idx)
        self._count_var.set(f"{len(self._pcb_ids)} PCB(s) sampled")

    def _on_ok(self):
        if not self._pcb_ids:
            self._err_var.set('At least one PCB ID must be sampled before marking OK.')
            return
        self.result = ('OK', self._pcb_ids[:], '')
        self.window.destroy()

    def _on_not_ok(self):
        reason = _ask_reason(self._rack_number, self.window)
        if not reason:
            return
        self.result = ('NOT_OK', [], reason)
        self.window.destroy()


def _ask_reason(rack_number: str, parent) -> str:
    """Small modal to collect the NOT OK reason. Returns '' if cancelled."""
    result = ['']

    dlg = tk.Toplevel(parent)
    dlg.title('NOT OK — Enter Reason')
    dlg.resizable(False, False)
    dlg.grab_set()

    frm = ttk.Frame(dlg, padding=16)
    frm.pack(fill='both', expand=True)
    frm.columnconfigure(0, weight=1)

    ttk.Label(frm, text=f"Reason for marking rack  {rack_number}  as NOT OK:",
              font=('Segoe UI', 11, 'bold'), wraplength=380).grid(
        row=0, column=0, columnspan=2, sticky='w', pady=(0, 8))

    reason_var = tk.StringVar()
    entry = ttk.Entry(frm, textvariable=reason_var, font=('Segoe UI', 12))
    entry.grid(row=1, column=0, columnspan=2, sticky='ew', ipady=5, pady=(0, 4))

    err_var = tk.StringVar()
    tk.Label(frm, textvariable=err_var, font=('Segoe UI', 10),
             fg='#c92a2a', bg=BG).grid(row=2, column=0, columnspan=2, sticky='w')

    def _confirm(_=None):
        r = reason_var.get().strip()
        if not r:
            err_var.set('A reason is required.')
            return
        result[0] = r
        dlg.destroy()

    entry.bind('<Return>', _confirm)

    btn_row = ttk.Frame(frm)
    btn_row.grid(row=3, column=0, columnspan=2, sticky='e', pady=(8, 0))

    colored_btn(btn_row, 'Cancel', 'secondary',
                dlg.destroy, bold=False, pady=4).pack(side='left', padx=(0, 6))
    colored_btn(btn_row, 'Confirm NOT OK', 'danger',
                _confirm, pady=4).pack(side='left')

    entry.focus()
    dlg.wait_window()
    return result[0]
