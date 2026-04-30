"""Shared UI helpers for the tkinter rewrite."""
import re as _re
import tkinter as tk
from tkinter import ttk

BG = '#f8f9fa'

# ── Colours ───────────────────────────────────────────────────────────────────
STATUS_FG = {
    'success': '#2f9e44',
    'warning': '#e67700',
    'error':   '#c92a2a',
}

BTN_STYLES = {
    'primary':  dict(bg='#1971c2', fg='white', activebackground='#1562a8'),
    'success':  dict(bg='#2f9e44', fg='white', activebackground='#276943'),
    'danger':   dict(bg='#c92a2a', fg='white', activebackground='#a62020'),
    'warning':  dict(bg='#e67700', fg='white', activebackground='#cc6900'),
    'secondary':dict(bg='#e9ecef', fg='#495057', activebackground='#dee2e6'),
}


def colored_btn(parent, text, style_key, command, font_size=11, bold=True, **kw):
    """Create a tk.Button with a predefined colour style."""
    weight = 'bold' if bold else 'normal'
    cfg = dict(BTN_STYLES[style_key])
    cfg.update(kw)
    return tk.Button(
        parent, text=text, font=('Segoe UI', font_size, weight),
        relief='flat', cursor='hand2', activeforeground=cfg.get('fg', 'white'),
        command=command, **cfg,
    )


def form_label(parent, text, row, col=0, width=14):
    """Right-aligned bold label for a form row."""
    lbl = ttk.Label(parent, text=text, font=('Segoe UI', 11, 'bold'),
                    anchor='e', width=width)
    lbl.grid(row=row, column=col, sticky='e', padx=(0, 8), pady=3)
    return lbl


def readonly_entry(parent, textvariable, row, col=1, **kw):
    """Blue readonly entry used for live clock display."""
    e = tk.Entry(parent, textvariable=textvariable, state='readonly',
                 font=('Segoe UI', 12), bg='#e7f5ff', fg='#1864ab',
                 readonlybackground='#e7f5ff', relief='solid', bd=1, **kw)
    e.grid(row=row, column=col, sticky='ew', pady=3, ipady=3)
    return e


def text_entry(parent, textvariable, row, col=1, font_size=11, ipady=4, **kw):
    """Standard editable Entry."""
    e = ttk.Entry(parent, textvariable=textvariable,
                  font=('Segoe UI', font_size), **kw)
    e.grid(row=row, column=col, sticky='ew', pady=3, ipady=ipady)
    return e


def status_label(parent, row, colspan=2):
    var = tk.StringVar()
    lbl = tk.Label(parent, textvariable=var, font=('Segoe UI', 11, 'bold'),
                   bg=BG, wraplength=800, justify='center')
    lbl.grid(row=row, column=0, columnspan=colspan, pady=4)
    return var, lbl


def make_upper(var):
    """No-op kept for compatibility — uppercase on read instead to avoid cursor bugs."""
    pass


def attach_rack_cleaner(var):
    """Strip non-printable/non-rack characters in real-time as the scanner types."""
    import re
    _busy = [False]

    def _clean(*_):
        if _busy[0]:
            return
        raw = var.get()
        cleaned = re.sub(r'[^A-Za-z0-9/]', '', raw).upper()
        if cleaned != raw:
            _busy[0] = True
            var.set(cleaned)
            _busy[0] = False

    var.trace_add('write', _clean)


_RACK_LIKE = _re.compile(r'^(PR|MR)/\d', _re.IGNORECASE)


def attach_rack_blocker(var, on_blocked):
    """
    Reject rack barcodes (PR/xxx or MR/xxx) typed/scanned into a non-rack field.
    Clears the variable and calls on_blocked() as soon as the pattern is detected.
    """
    _busy = [False]

    def _check(*_):
        if _busy[0]:
            return
        if _RACK_LIKE.match(var.get()):
            _busy[0] = True
            var.set('')
            _busy[0] = False
            on_blocked()

    var.trace_add('write', _check)


_SCAN_BLOCK_TAG = 'ScannerGuardBlock'


def scanner_guard(rack_entry, entries, block_ms=2000):
    """
    Block scanner overflow after a rack scan for block_ms milliseconds.

    Two-pronged defence:
      1. Sets all entries (including rack_entry itself) to readonly so the
         re-sent barcode characters are discarded.
      2. Inserts a high-priority bindtag that swallows <Return> before the
         widget's own binding can fire — stops Enter from triggering
         downstream handlers (mark-OK, handover, focus-shift lambdas, etc).

    Usage:
        rack_entry.bind('<Return>', lambda e: (
            scanner_guard(rack_entry, [inspector_entry]), process_scan()))
    """
    all_entries = [rack_entry] + list(entries)

    # Register the swallow binding once per application lifecycle (idempotent).
    rack_entry.bind_class(_SCAN_BLOCK_TAG, '<Return>', lambda ev: 'break')

    for e in all_entries:
        try:
            e.config(state='readonly')
        except Exception:
            pass
        tags = list(e.bindtags())
        if _SCAN_BLOCK_TAG not in tags:
            tags.insert(0, _SCAN_BLOCK_TAG)
            e.bindtags(tags)

    def _restore():
        for e in all_entries:
            try:
                e.config(state='normal')
            except Exception:
                pass
            tags = list(e.bindtags())
            if _SCAN_BLOCK_TAG in tags:
                tags.remove(_SCAN_BLOCK_TAG)
            e.bindtags(tags)

    rack_entry.after(block_ms, _restore)


def scrolled_tree(parent, columns, headings, col_widths=None,
                  stretch_cols=None, height=8, selectmode='browse'):
    """
    Return (container_frame, treeview).
    col_widths : dict {col_id: width} for fixed-width columns
    stretch_cols : list of col_ids that should stretch (default: all)
    """
    container = ttk.Frame(parent)
    container.columnconfigure(0, weight=1)
    container.rowconfigure(0, weight=1)

    tree = ttk.Treeview(container, columns=columns, show='headings',
                        height=height, selectmode=selectmode)
    vsb = ttk.Scrollbar(container, orient='vertical',   command=tree.yview)
    hsb = ttk.Scrollbar(container, orient='horizontal', command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky='nsew')
    vsb.grid(row=0, column=1, sticky='ns')
    hsb.grid(row=1, column=0, sticky='ew')

    for col, heading in zip(columns, headings):
        w = (col_widths or {}).get(col, 120)
        stretch = col in (stretch_cols or columns)
        tree.heading(col, text=heading, anchor='center')
        tree.column(col, width=w, anchor='center', stretch=stretch)

    tree.tag_configure('odd',  background='#f8f9fa')
    tree.tag_configure('even', background='white')

    return container, tree


def fill_tree(tree, rows, key_fn):
    """Replace all rows in a Treeview. key_fn(row) -> tuple of cell values."""
    tree.delete(*tree.get_children())
    for i, row in enumerate(rows):
        tag = 'odd' if i % 2 == 0 else 'even'
        tree.insert('', 'end', values=key_fn(row), tags=(tag,))


def ask_password(parent, title='Enter Password'):
    """Show a password prompt. Returns True if correct password entered, False otherwise."""
    import settings as _settings
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.resizable(False, False)
    dlg.grab_set()
    dlg.transient(parent)

    frm = ttk.Frame(dlg, padding=16)
    frm.pack(fill='both', expand=True)
    ttk.Label(frm, text='Password:', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
    pw_var = tk.StringVar()
    entry = ttk.Entry(frm, textvariable=pw_var, show='*', font=('Segoe UI', 12), width=22)
    entry.pack(fill='x', pady=(6, 4), ipady=4)

    err_var = tk.StringVar()
    tk.Label(frm, textvariable=err_var, font=('Segoe UI', 10),
             fg='#c92a2a', bg=BG).pack(anchor='w')

    result = [False]

    def _confirm(_=None):
        if _settings.check_password(pw_var.get()):
            result[0] = True
            dlg.destroy()
        else:
            err_var.set('Incorrect password.')
            pw_var.set('')
            entry.focus()

    def _cancel():
        dlg.destroy()

    entry.bind('<Return>', _confirm)
    btn_row = ttk.Frame(frm)
    btn_row.pack(fill='x', pady=(8, 0))
    colored_btn(btn_row, 'Cancel', 'secondary', _cancel, bold=False, pady=5).pack(side='left', padx=(0, 8))
    colored_btn(btn_row, 'OK', 'primary', _confirm, pady=5).pack(side='left')

    entry.focus()
    dlg.wait_window()
    return result[0]


def ask_yes_no(title, message):
    from tkinter import messagebox
    return messagebox.askyesno(title, message)


def show_info(title, message):
    from tkinter import messagebox
    messagebox.showinfo(title, message)


def show_error(title, message):
    from tkinter import messagebox
    messagebox.showerror(title, message)


def show_warning(title, message):
    from tkinter import messagebox
    messagebox.showwarning(title, message)
