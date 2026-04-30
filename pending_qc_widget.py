"""Widget showing SMT handovers currently waiting for QC."""
import tkinter as tk
from tkinter import ttk

import database
import settings
from utils import to_ist
from ui_helpers import scrolled_tree, fill_tree, BG

_COLS = ('rack', 'model', 'panels', 'cards', 'line', 'operator', 'time')
_HEADS = ('Rack No.', 'Model', 'Panels', 'Cards', 'Line', 'SMT Operator', 'Handed Over (IST)')
_WIDTHS = {'panels': 70, 'cards': 70, 'time': 160}
_STRETCH = ('rack', 'model', 'line', 'operator', 'time')


class PendingQCWidget:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        tk.Label(self.frame, text='Pending for QC',
                 font=('Segoe UI', 11, 'bold'), bg=BG).grid(
            row=0, column=0, sticky='w', pady=(4, 2))

        container, self._tree = scrolled_tree(
            self.frame, _COLS, _HEADS,
            col_widths=_WIDTHS, stretch_cols=_STRETCH, height=7)
        container.grid(row=1, column=0, sticky='nsew')

    def refresh(self):
        rows = database.get_pending_for_qc()
        fill_tree(self._tree, rows, lambda r: (
            r['rack_number'], r['model'],
            r['quantity'],
            settings.resolve_cards(r['quantity'], r['cards'] if 'cards' in r.keys() else None, r['model']),
            r['line'] or '—', r['smt_operator'], to_ist(r['created_at']),
        ))
