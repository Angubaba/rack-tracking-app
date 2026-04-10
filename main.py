"""QC Rack Tracking System — tkinter desktop application."""
import sys
import tkinter as tk
from tkinter import ttk

import database
from smt_tab import SMTTab
from ok_tab import OKTab
from th_tab import THTab
from lookup_tab import LookupTab
from settings_tab import SettingsTab

BG = '#f8f9fa'


def _setup_style(root):
    s = ttk.Style(root)
    s.theme_use('clam')
    root.configure(bg=BG)

    s.configure('TFrame',          background=BG)
    s.configure('TLabel',          background=BG, font=('Segoe UI', 11))
    s.configure('TLabelframe',     background=BG)
    s.configure('TLabelframe.Label', background=BG, font=('Segoe UI', 11, 'bold'))
    s.configure('TCheckbutton',    background=BG, font=('Segoe UI', 11))

    s.configure('TNotebook',       background='#e9ecef', borderwidth=0)
    s.configure('TNotebook.Tab',   font=('Segoe UI', 11, 'bold'),
                padding=[18, 7],   background='#e9ecef', foreground='#495057')
    s.map('TNotebook.Tab',
          background=[('selected', '#1971c2'), ('active', '#dee2e6')],
          foreground=[('selected', '#ffffff'), ('active', '#212529')])

    s.configure('TEntry',  font=('Segoe UI', 11), fieldbackground='white',
                padding=[5, 4])
    s.configure('TSpinbox', font=('Segoe UI', 11), fieldbackground='white',
                padding=[5, 4])
    s.configure('TButton', font=('Segoe UI', 11), padding=[8, 5])

    s.configure('Treeview', font=('Segoe UI', 10), rowheight=24,
                background='white', fieldbackground='white', foreground='#212529')
    s.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'),
                background='#e9ecef', foreground='#1971c2')
    s.map('Treeview', background=[('selected', '#a5d8ff')],
          foreground=[('selected', '#1864ab')])

    s.configure('TSeparator', background='#dee2e6')


def main():
    database.init_db()

    root = tk.Tk()
    root.title("QC Rack Tracking System")
    root.minsize(1100, 700)
    _setup_style(root)

    nb = ttk.Notebook(root)
    nb.pack(fill='both', expand=True, padx=6, pady=6)

    tabs = [
        SMTTab(nb),
        OKTab(nb),
        THTab(nb),
        LookupTab(nb),
        SettingsTab(nb),
    ]
    labels = ['  SMT  ', '  QC  ', '  PRODUCTION  ',
              '  LOOKUP  ', '  SETTINGS  ']
    for tab, lbl in zip(tabs, labels):
        nb.add(tab.frame, text=lbl)

    def _on_tab_change(event):
        idx = nb.index(nb.select())
        if hasattr(tabs[idx], 'on_activate'):
            tabs[idx].on_activate()

    nb.bind('<<NotebookTabChanged>>', _on_tab_change)
    tabs[0].on_activate()
    root.mainloop()


if __name__ == '__main__':
    main()
