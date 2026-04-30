"""Widget showing racks currently in FG (QC OK, not yet sent to TH)."""
import tkinter as tk
from tkinter import ttk

import database
import settings
from utils import to_ist
from ui_helpers import scrolled_tree, fill_tree, BG

_COLS = ('rack', 'model', 'panels', 'cards', 'inspector', 'since')
_HEADS = ('Rack No.', 'Model', 'Panels', 'Cards', 'Inspected By', 'In FG Since (IST)')
_WIDTHS = {'panels': 70, 'cards': 70, 'since': 160}
_STRETCH = ('rack', 'model', 'inspector', 'since')


class ActiveRacksWidget:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        tk.Label(self.frame, text='Racks in FG',
                 font=('Segoe UI', 11, 'bold'), bg=BG).grid(
            row=0, column=0, sticky='w', pady=(4, 2))

        container, self._tree = scrolled_tree(
            self.frame, _COLS, _HEADS,
            col_widths=_WIDTHS, stretch_cols=_STRETCH, height=8)
        container.grid(row=1, column=0, sticky='nsew')

        # Double-click PCB cell to show IDs
        self._tree.bind('<Double-1>', self._on_double_click)
        self._pcb_data = {}   # iid -> list[str]

    def refresh(self):
        racks = database.get_active_racks()
        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(racks):
            tag = 'odd' if i % 2 == 0 else 'even'
            qty = r['quantity']
            cards_val = r['cards'] if 'cards' in r.keys() else None
            cards = settings.resolve_cards(qty, cards_val, r['model'])
            self._tree.insert('', 'end', tags=(tag,), values=(
                r['rack_number'], r['model'], qty, cards,
                r['inspected_by'], to_ist(r['created_at']),
            ))

    def _on_double_click(self, event):
        pass


def _show_pcb_popup(pcb_ids, parent):
    import tkinter as tk
    from tkinter import ttk
    dlg = tk.Toplevel(parent)
    dlg.title(f"PCB Sample IDs  ({len(pcb_ids)} total)")
    dlg.resizable(False, False)
    dlg.grab_set()

    frame = ttk.Frame(dlg, padding=14)
    frame.pack(fill='both', expand=True)

    lb = tk.Listbox(frame, font=('Segoe UI', 12), width=30, height=12,
                    selectmode='none', relief='solid', bd=1)
    sb = ttk.Scrollbar(frame, command=lb.yview)
    lb.configure(yscrollcommand=sb.set)
    lb.pack(side='left', fill='both', expand=True)
    sb.pack(side='left', fill='y')

    for pid in pcb_ids:
        lb.insert('end', pid)

    tk.Button(dlg, text='Close', font=('Segoe UI', 11),
              bg='#e9ecef', fg='#495057', relief='flat',
              command=dlg.destroy, pady=6).pack(
        fill='x', padx=14, pady=(0, 14))

    dlg.wait_window()
