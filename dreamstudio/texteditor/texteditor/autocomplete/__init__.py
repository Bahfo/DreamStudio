import jedi
import tkinter as tk
from itertools import chain
from threading import Thread, Lock

from ...utils import Toplevel
from .item import AutoCompleteItem
from .kinds import Kinds
from .languages.python_completions import python_completions


class AutoComplete(Toplevel):
    """Autocomplete widget with controlled destruction/recreation."""

    def __init__(self, master, items=None, active=False, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.master = master
        self.autocomplete_kinds = Kinds(self)

        self.config(padx=1, pady=1, bg=self.base.theme.border)
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)

        self.grid_columnconfigure(0, weight=1)

        self.active = active
        if not active:
            self.withdraw()

        self.menu_items = []
        self.active_items = []
        self.row = 0
        self.selected = 0

        self._lock = Lock()
        self._debounce_id = None
        self._jedi_thread = None
        self._request_id = 0

        if items is None:
            self.items = {}
        elif isinstance(items, list):
            self.items = {name: {"type": kind} for name, kind in items}
        else:
            self.items = items

        self.add_all_items()
        self.refresh_selected()

    # Widget lifecycle

    def destroy_widget(self):
        """Destroy autocomplete window."""
        if self.winfo_exists():
            self.destroy()

    def recreate_widget(self):
        """Recreate autocomplete window."""
        pos = self.master.cursor_screen_location()
        self.__init__(self.master, items=self.items, active=True)
        self.geometry(f"+{pos[0]}+{pos[1]}")
        self.deiconify()

    # Completion update

    def update_completions(self):
        if self._debounce_id:
            self.after_cancel(self._debounce_id)

        self._debounce_id = self.after(60, self._request_jedi_update)

    def _request_jedi_update(self):
        self._debounce_id = None

        term = self.master.get_current_word()
        line, col = map(int, self.master.index("insert").split("."))
        code = self.master.get_all_text()

        self._request_id += 1
        request_id = self._request_id

        if self._jedi_thread and self._jedi_thread.is_alive():
            return

        self._jedi_thread = Thread(
            target=self._compute_jedi,
            args=(code, line, col, term, request_id),
            daemon=True
        )
        self._jedi_thread.start()

    def _compute_jedi(self, code, line, col, term, request_id):
        try:
            script = jedi.Script(code)
            jedi_results = {
                c.name: {"type": c.type}
                for c in script.complete(line, col)
            }
        except Exception:
            jedi_results = {}

        with self._lock:
            all_items = python_completions.copy()
            all_items.update(self.items)
            all_items.update(jedi_results)

            for w in self.master.words:
                if w not in all_items:
                    all_items[w] = {"type": "word"}

        self.after(0, lambda: self._update_ui(all_items, term, request_id))

    def _update_ui(self, items, term, request_id):
        if request_id != self._request_id:
            return

        if not self.winfo_exists():
            return

        existing = {i.get_text() for i in self.menu_items}

        for name, meta in items.items():
            if name not in existing:
                self.add_item(name, meta.get("type") if meta else None)

        exact, starts, includes = [], [], []

        for i in self.menu_items:
            text = i.get_text()

            if text == term:
                exact.append(i)
            elif text.startswith(term):
                starts.append(i)
            elif term in text:
                includes.append(i)

        new_active = list(chain(exact, starts, includes))

        self.hide_all_items()

        if new_active:
            self.refresh_geometry()
            self.show_items(new_active[:10], term)
            self.deiconify()
            self.active = True
        else:
            self.hide()

    # Navigation

    def move_up(self, *_):
        if self.active:
            self.select(-1)
            return "break"

    def move_down(self, *_):
        if self.active:
            self.select(1)
            return "break"

    # Item management

    def add_all_items(self):
        for completion, meta in self.items.items():
            self.add_item(completion, meta.get("type") if meta else None)

        self.active_items = self.menu_items
        self.refresh_selected()

    def add_item(self, text, kind=""):
        item = AutoCompleteItem(self, text, kind=kind)
        self.menu_items.append(item)

    def hide_all_items(self):
        for i in self.menu_items:
            i.grid_forget()

        self.active_items = []
        self.row = 0

    def show_items(self, items, term):
        self.active_items = items

        for i in items:
            i.grid(row=self.row, sticky=tk.EW)
            i.mark_term(term)
            self.row += 1

        self.reset_selection()

    # Selection logic

    def select(self, delta):
        if not self.active_items:
            return

        self.selected = (self.selected + delta) % len(self.active_items)
        self.refresh_selected()

    def reset_selection(self):
        self.selected = 0
        self.refresh_selected()

    def refresh_selected(self):
        for i, item in enumerate(self.active_items):
            if i == self.selected:
                item.select()
            else:
                item.deselect()

    # Geometry

    def refresh_geometry(self, *_):
        pos = self.master.cursor_screen_location()
        self.geometry(f"+{pos[0]}+{pos[1]}")

    def show(self, pos):
        self.active = True
        self.geometry(f"+{pos[0]}+{pos[1]}")
        self.deiconify()
        self.lift()

    def hide(self, *_):
        self.active = False
        self.withdraw()
        self.reset()

    def reset(self):
        self.selected = 0
        self.row = 0

    # Choosing completion

    def choose(self, this=None, *_):
        if not self.active_items:
            return

        if not this:
            this = self.active_items[self.selected]

        self.master.confirm_autocomplete(this.get_text())

        # destroy and recreate (requested behavior)
        self.destroy_widget()
        self.recreate_widget()

        return "break"

    # Key handlers

    def handle_escape(self):
        """Escape key behaviour (VSCode style)."""
        self.destroy_widget()

    def handle_enter(self):
        """Enter key behaviour."""
        self.destroy_widget()
        self.recreate_widget()
