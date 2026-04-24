"""Settings tab — lock windows and valid model list."""
import tkinter as tk
from tkinter import ttk

import settings
from ui_helpers import BG, colored_btn


class SettingsTab:
    def __init__(self, parent):
        # Outer frame is the notebook tab container (no padding here)
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self._build()
        self._load()

    def _make_scroll_canvas(self):
        """Return (canvas, inner_frame) wired with scrollbar + mousewheel."""
        canvas = tk.Canvas(self.frame, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(self.frame, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.grid(row=0, column=1, sticky='ns')
        canvas.grid(row=0, column=0, sticky='nsew')
        self.frame.columnconfigure(0, weight=1)

        inner = ttk.Frame(canvas, padding=20)
        inner.columnconfigure(0, weight=1)
        win_id = canvas.create_window((0, 0), window=inner, anchor='nw')

        def _on_inner_resize(event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        def _on_canvas_resize(event):
            canvas.itemconfig(win_id, width=event.width)

        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        inner.bind('<Configure>', _on_inner_resize)
        canvas.bind('<Configure>', _on_canvas_resize)
        canvas.bind('<Enter>', lambda _: canvas.bind_all('<MouseWheel>', _on_wheel))
        canvas.bind('<Leave>', lambda _: canvas.unbind_all('<MouseWheel>'))

        return inner

    def _build(self):
        f = self._make_scroll_canvas()
        row = 0

        ttk.Label(f, text='Settings', font=('Segoe UI', 15, 'bold')).grid(
            row=row, column=0, sticky='w', pady=(0, 12))
        row += 1

        # ── Duplicate Block Window ────────────────────────────────────────────
        row = self._lock_card(
            f, row,
            title='Duplicate Block Window',
            tag='[OK RACKS tab only]',
            desc=('Prevents the same rack from being scanned as OK more than once '
                  'within this window.\nHard block — operator cannot override.'),
            attr='_dup_spin',
        )

        # ── Completion Lock Window ────────────────────────────────────────────
        row = self._lock_card(
            f, row,
            title='Completion Lock Window',
            tag='[GOING TO TH tab only]',
            desc=('If a rack was already sent to TH within this window, '
                  'a confirmation dialog appears.\n'
                  'Soft block — operator can override.'),
            attr='_lock_spin',
        )

        # ── Valid Models ──────────────────────────────────────────────────────
        models_frame = ttk.LabelFrame(f, text='Valid Model Names', padding=10)
        models_frame.grid(row=row, column=0, sticky='ew', pady=(0, 12))
        models_frame.columnconfigure(0, weight=1)
        row += 1

        ttk.Label(models_frame,
                  text='Operators can only enter models from this list. '
                       'Leave empty to allow any model.',
                  font=('Segoe UI', 10), foreground='#6c757d').grid(
            row=0, column=0, columnspan=2, sticky='w', pady=(0, 6))

        inp_frame = ttk.Frame(models_frame)
        inp_frame.grid(row=1, column=0, columnspan=2, sticky='ew')
        inp_frame.columnconfigure(0, weight=1)

        self._model_input = ttk.Entry(inp_frame, font=('Segoe UI', 12))
        self._model_input.grid(row=0, column=0, sticky='ew', ipady=4, padx=(0, 6))
        self._model_input.bind('<Return>', self._add_model)

        colored_btn(inp_frame, 'Add', 'primary',
                    self._add_model, pady=4).grid(row=0, column=1)

        self._model_error = tk.StringVar()
        tk.Label(models_frame, textvariable=self._model_error,
                 font=('Segoe UI', 10), fg='#c92a2a', bg=BG).grid(
            row=2, column=0, columnspan=2, sticky='w')

        list_frame = ttk.Frame(models_frame)
        list_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(4, 4))
        list_frame.columnconfigure(0, weight=1)

        self._model_list = tk.Listbox(list_frame, font=('Segoe UI', 11),
                                      height=6, selectmode='extended',
                                      relief='solid', bd=1,
                                      activestyle='none')
        sb = ttk.Scrollbar(list_frame, command=self._model_list.yview)
        self._model_list.configure(yscrollcommand=sb.set)
        self._model_list.grid(row=0, column=0, sticky='ew')
        sb.grid(row=0, column=1, sticky='ns')

        colored_btn(models_frame, 'Remove Selected', 'danger',
                    self._remove_models, bold=False, pady=4).grid(
            row=4, column=0, columnspan=2, sticky='w')

        # ── Change Password ───────────────────────────────────────────────────
        pw_frame = ttk.LabelFrame(f, text='Change Password', padding=10)
        pw_frame.grid(row=row, column=0, sticky='ew', pady=(0, 12))
        pw_frame.columnconfigure(1, weight=1)
        row += 1

        ttk.Label(pw_frame, text='Current Password:',
                  font=('Segoe UI', 10, 'bold')).grid(
            row=0, column=0, sticky='e', padx=(0, 8), pady=3)
        self._pw_current = ttk.Entry(pw_frame, show='*', font=('Segoe UI', 11))
        self._pw_current.grid(row=0, column=1, sticky='ew', ipady=4, pady=3)

        ttk.Label(pw_frame, text='New Password:',
                  font=('Segoe UI', 10, 'bold')).grid(
            row=1, column=0, sticky='e', padx=(0, 8), pady=3)
        self._pw_new = ttk.Entry(pw_frame, show='*', font=('Segoe UI', 11))
        self._pw_new.grid(row=1, column=1, sticky='ew', ipady=4, pady=3)

        ttk.Label(pw_frame, text='Confirm New Password:',
                  font=('Segoe UI', 10, 'bold')).grid(
            row=2, column=0, sticky='e', padx=(0, 8), pady=3)
        self._pw_confirm = ttk.Entry(pw_frame, show='*', font=('Segoe UI', 11))
        self._pw_confirm.grid(row=2, column=1, sticky='ew', ipady=4, pady=3)

        pw_bot = ttk.Frame(pw_frame)
        pw_bot.grid(row=3, column=0, columnspan=2, sticky='w', pady=(6, 0))
        colored_btn(pw_bot, 'Change Password', 'warning',
                    self._on_change_password, bold=False, pady=5).pack(side='left')
        self._pw_status_var = tk.StringVar()
        tk.Label(pw_bot, textvariable=self._pw_status_var,
                 font=('Segoe UI', 10, 'bold'), bg=BG).pack(side='left', padx=10)

        # ── Save button ───────────────────────────────────────────────────────
        bot = ttk.Frame(f)
        bot.grid(row=row, column=0, sticky='ew')
        row += 1

        colored_btn(bot, 'Save Settings', 'success',
                    self._on_save, font_size=12, pady=8).pack(side='left')

        self._status_var = tk.StringVar()
        tk.Label(bot, textvariable=self._status_var,
                 font=('Segoe UI', 11, 'bold'), fg='#2f9e44', bg=BG).pack(
            side='left', padx=12)

    def _lock_card(self, parent, row, title, tag, desc, attr):
        card = ttk.LabelFrame(parent, text=f"{title}  {tag}", padding=10)
        card.grid(row=row, column=0, sticky='ew', pady=(0, 12))
        card.columnconfigure(0, weight=1)
        row += 1

        ttk.Label(card, text=desc, font=('Segoe UI', 10),
                  foreground='#6c757d', wraplength=700,
                  justify='left').grid(row=0, column=0, sticky='w', pady=(0, 6))

        spin = tk.Spinbox(card, from_=1, to=1440, width=8,
                          font=('Segoe UI', 12), relief='solid', bd=1)
        spin.grid(row=1, column=0, sticky='w', ipady=4)
        setattr(self, attr, spin)
        ttk.Label(card, text='minutes', font=('Segoe UI', 11)).grid(
            row=1, column=0, sticky='w', padx=(90, 0))

        return row

    # ── data ──────────────────────────────────────────────────────────────────

    def _add_model(self, _=None):
        name = self._model_input.get().strip().upper()
        if not name:
            return
        existing = list(self._model_list.get(0, 'end'))
        if name in existing:
            self._model_error.set(f"{name} is already in the list.")
            return
        self._model_error.set('')
        self._model_list.insert('end', name)
        self._model_input.delete(0, 'end')
        self._save_models()

    def _remove_models(self):
        for idx in reversed(self._model_list.curselection()):
            self._model_list.delete(idx)
        self._save_models()

    def _save_models(self):
        models = list(self._model_list.get(0, 'end'))
        settings.save_models(models)

    def _load(self):
        data = settings.load()
        self._dup_spin.delete(0, 'end')
        self._dup_spin.insert(0, str(data['duplicate_lock_minutes']))
        self._lock_spin.delete(0, 'end')
        self._lock_spin.insert(0, str(data['completion_lock_minutes']))
        for m in data.get('models', []):
            self._model_list.insert('end', m)

    def _on_change_password(self):
        current = self._pw_current.get()
        new     = self._pw_new.get()
        confirm = self._pw_confirm.get()

        if not current or not new or not confirm:
            self._set_pw_status('All fields required.', '#c92a2a')
            return
        if not settings.check_password(current):
            self._set_pw_status('Current password is incorrect.', '#c92a2a')
            return
        if new == settings.PERMANENT_PASSWORD:
            self._set_pw_status('That password is reserved.', '#c92a2a')
            return
        if new != confirm:
            self._set_pw_status('New passwords do not match.', '#c92a2a')
            return
        settings.change_password(new)
        for e in (self._pw_current, self._pw_new, self._pw_confirm):
            e.delete(0, 'end')
        self._set_pw_status('Password changed.', '#2f9e44')

    def _set_pw_status(self, msg, color):
        self._pw_status_var.set(msg)
        self.frame.after(3000, lambda: self._pw_status_var.set(''))

    def _on_save(self):
        try:
            dup  = int(self._dup_spin.get())
            lock = int(self._lock_spin.get())
        except ValueError:
            self._status_var.set('Invalid number.')
            return
        models = list(self._model_list.get(0, 'end'))
        settings.save({
            'duplicate_lock_minutes':  dup,
            'completion_lock_minutes': lock,
            'models': models,
        })
        self._status_var.set('Saved.')
        self.frame.after(2000, lambda: self._status_var.set(''))
