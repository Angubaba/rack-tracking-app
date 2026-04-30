"""Dashboard tab — today's model-level status summary (auto-refreshes)."""
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timezone, timedelta

import database
import settings
from ui_helpers import BG, colored_btn, scrolled_tree

IST = timedelta(hours=5, minutes=30)

_COLS  = ('model',
          'pend_r', 'pend_q',
          'fg_r',   'fg_q',
          'th_r',   'th_q',
          'nok_r',  'nok_q',
          'tot_r',  'tot_q')
_HEADS = ('Model',
          'Pending', 'Pending',
          'FG',      'FG',
          'TH',      'TH',
          'Not OK',  'Not OK',
          'Tot. Racks', 'Tot. Cards')
_WIDTHS = {c: 82 for c in _COLS}
_WIDTHS['model'] = 100
_WIDTHS['pend_q'] = 90
_WIDTHS['fg_q']   = 90
_WIDTHS['th_q']   = 90
_WIDTHS['nok_q']  = 90
_WIDTHS['tot_q']  = 90

# Col indices (1-based, as Treeview reports them)
_COL_PEND_R = 2
_COL_FG_R   = 4

_REFRESH_MS = 30_000


def _today_utc_range():
    now_ist = datetime.now(timezone.utc) + IST
    start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0) - IST
    end   = now_ist.replace(hour=23, minute=59, second=59, microsecond=0) - IST
    return start.isoformat(), end.isoformat()


class DashboardTab:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=10)
        self.frame.columnconfigure(0, weight=1)
        self._cycles = []
        self._build()
        self._schedule_refresh()

    def _build(self):
        f = self.frame

        hdr = ttk.Frame(f)
        hdr.grid(row=0, column=0, sticky='ew', pady=(0, 4))
        self._date_var = tk.StringVar()
        tk.Label(hdr, textvariable=self._date_var,
                 font=('Segoe UI', 13, 'bold'), bg=BG, fg='#1971c2').pack(side='left')
        colored_btn(hdr, 'Refresh', 'primary',
                    self.refresh, bold=False, pady=4).pack(side='right')

        # Hint label
        tk.Label(f, text='Double-click a Racks number under Pending or In FG to see rack list.',
                 font=('Segoe UI', 9), bg=BG, fg='#868e96', anchor='w').grid(
            row=1, column=0, sticky='ew', pady=(0, 4))

        self._summary_var = tk.StringVar(value='')
        tk.Label(f, textvariable=self._summary_var,
                 font=('Segoe UI', 11), bg=BG, fg='#495057',
                 anchor='w').grid(row=2, column=0, sticky='ew', pady=(0, 6))

        container, self._tree = scrolled_tree(
            f, _COLS, _HEADS,
            col_widths=_WIDTHS, stretch_cols=('model',), height=18)
        container.grid(row=3, column=0, sticky='nsew')
        f.rowconfigure(3, weight=1)

        self._tree.bind('<Double-1>', self._on_double_click)

        self._footer_var = tk.StringVar()
        tk.Label(f, textvariable=self._footer_var,
                 font=('Segoe UI', 10, 'bold'), bg='#e9ecef', fg='#212529',
                 anchor='w', relief='flat', padx=6, pady=4).grid(
            row=4, column=0, sticky='ew', pady=(4, 0))

    # ── Data ─────────────────────────────────────────────────────────────────

    def refresh(self):
        now_ist = datetime.now(timezone.utc) + IST
        self._date_var.set(f"Today  —  {now_ist.strftime('%d/%m/%Y')}")

        utc_from, utc_to = _today_utc_range()
        self._cycles = database.get_cycles(utc_from=utc_from, utc_to=utc_to)

        md = {}
        for c in self._cycles:
            m = c['model']
            if m not in md:
                md[m] = {'pend_r': 0, 'pend_q': 0,
                          'fg_r': 0,   'fg_q': 0,
                          'th_r': 0,   'th_q': 0,
                          'nok_r': 0,  'nok_q': 0}
            cards_val = c.get('cards')
            q = settings.resolve_cards(c['quantity'], cards_val, m)
            qr = c['qc_result']
            if qr == 'PENDING':
                md[m]['pend_r'] += 1; md[m]['pend_q'] += q
            elif c.get('th_id'):
                md[m]['th_r'] += 1;   md[m]['th_q'] += q
            elif qr in ('OK', 'LEGACY'):
                md[m]['fg_r'] += 1;   md[m]['fg_q'] += q
            elif qr == 'NOT_OK':
                md[m]['nok_r'] += 1;  md[m]['nok_q'] += q

        self._tree.delete(*self._tree.get_children())
        tot = {k: 0 for k in ('pend_r', 'pend_q', 'fg_r', 'fg_q',
                               'th_r', 'th_q', 'nok_r', 'nok_q')}

        for i, model in enumerate(sorted(md)):
            d = md[model]
            tag = 'odd' if i % 2 == 0 else 'even'
            tr = d['pend_r'] + d['fg_r'] + d['th_r'] + d['nok_r']
            tq = d['pend_q'] + d['fg_q'] + d['th_q'] + d['nok_q']
            self._tree.insert('', 'end', tags=(tag,), values=(
                model,
                d['pend_r'] or '—', d['pend_q'] or '—',
                d['fg_r']   or '—', d['fg_q']   or '—',
                d['th_r']   or '—', d['th_q']   or '—',
                d['nok_r']  or '—', d['nok_q']  or '—',
                tr, tq,
            ))
            for k in tot:
                tot[k] += d[k]

        parts = []
        if tot['pend_r']: parts.append(f"Pending for QC: {tot['pend_r']} racks / {tot['pend_q']} cards")
        if tot['fg_r']:   parts.append(f"In FG: {tot['fg_r']} racks / {tot['fg_q']} cards")
        if tot['th_r']:   parts.append(f"At TH: {tot['th_r']} racks / {tot['th_q']} cards")
        if tot['nok_r']:  parts.append(f"NOT OK: {tot['nok_r']} racks / {tot['nok_q']} cards")
        self._summary_var.set('  ·  '.join(parts) if parts else 'No records for today yet.')

        tot_r = tot['pend_r'] + tot['fg_r'] + tot['th_r'] + tot['nok_r']
        tot_q = tot['pend_q'] + tot['fg_q'] + tot['th_q'] + tot['nok_q']
        self._footer_var.set(
            f"TOTALS   {tot_r} racks  /  {tot_q} cards"
            f"     |     Pending for QC: {tot['pend_r']} / {tot['pend_q']}"
            f"   In FG: {tot['fg_r']} / {tot['fg_q']}"
            f"   At TH: {tot['th_r']} / {tot['th_q']}"
            f"   NOT OK: {tot['nok_r']} / {tot['nok_q']}"
        )

    # ── Double-click popup ────────────────────────────────────────────────────

    def _on_double_click(self, event):
        col_id  = self._tree.identify_column(event.x)
        col_idx = int(col_id.replace('#', ''))
        if col_idx not in (_COL_PEND_R, _COL_FG_R):
            return

        sel = self._tree.selection()
        if not sel:
            return
        vals  = self._tree.item(sel[0], 'values')
        model = vals[0]
        count = vals[col_idx - 1]
        if count == '—':
            return

        if col_idx == _COL_PEND_R:
            title  = f"Pending for QC — {model}"
            racks  = [c['rack_number'] for c in self._cycles
                      if c['model'] == model and c['qc_result'] == 'PENDING']
        else:
            title  = f"In FG — {model}"
            racks  = [c['rack_number'] for c in self._cycles
                      if c['model'] == model
                      and c['qc_result'] in ('OK', 'LEGACY')
                      and not c.get('th_id')]

        self._show_rack_list(title, racks)

    def _show_rack_list(self, title, racks):
        dlg = tk.Toplevel(self.frame.winfo_toplevel())
        dlg.title(title)
        dlg.resizable(False, False)
        dlg.grab_set()

        frm = ttk.Frame(dlg, padding=16)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text=title,
                  font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 8))

        lb_frame = ttk.Frame(frm)
        lb_frame.pack(fill='both', expand=True)
        vsb = ttk.Scrollbar(lb_frame, orient='vertical')
        lb  = tk.Listbox(lb_frame, font=('Segoe UI', 12), width=22,
                         height=min(len(racks), 12) or 4,
                         yscrollcommand=vsb.set,
                         selectmode='browse', relief='solid', bd=1)
        vsb.config(command=lb.yview)
        lb.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        for r in sorted(racks):
            lb.insert('end', r)

        ttk.Label(frm, text=f"{len(racks)} rack{'s' if len(racks) != 1 else ''}",
                  font=('Segoe UI', 10), foreground='#868e96').pack(anchor='w', pady=(6, 4))
        colored_btn(frm, 'Close', 'secondary', dlg.destroy,
                    bold=False, pady=5).pack(fill='x')

        dlg.wait_window()

    def _schedule_refresh(self):
        self.refresh()
        self.frame.after(_REFRESH_MS, self._schedule_refresh)

    def on_activate(self):
        self.refresh()
