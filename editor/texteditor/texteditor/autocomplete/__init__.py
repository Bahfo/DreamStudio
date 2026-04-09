import jedi
import tkinter as tk
from threading import Thread, Lock

from ...utils import Toplevel
from .item import AutoCompleteItem
from .kinds import Kinds
from .languages.python_completions import python_completions
from .symbol_extractor import SymbolExtractor


class AutoComplete(Toplevel):
    """Autocomplete widget with proper lifecycle management."""

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

        self._static_items = python_completions.copy()
        self._static_items.update(self.items)

        self._builtin_names = set(python_completions.keys())

        self.add_all_items()
        self.refresh_selected()

    # Widget lifecycle

    def destroy_widget(self):
        """Hide and reset autocomplete."""
        if self.winfo_exists():
            self.withdraw()
            self.reset()
            self.hide_all_items()
            self.active = False

    # Completion update

    def update_completions(self):
        """Trigger debounced Jedi update."""
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(250, self._request_jedi_update)

    def _request_jedi_update(self):
        """Request Jedi completions."""
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
            daemon=True,
        )
        self._jedi_thread.start()

    def _compute_jedi(self, code, line, col, term, request_id):
        """Compute completions in background thread."""
        try:
            script = jedi.Script(code)
            jedi_results = {
                c.name: {"type": c.type, "completion": c}
                for c in script.complete(line, col)
            }
        except Exception:
            jedi_results = {}

        defined_names = SymbolExtractor.get_defined_names_before_cursor(code, line)

        filtered_results = {}
        for name, meta in jedi_results.items():
            if name in self._builtin_names or name in self._static_items:
                filtered_results[name] = meta
            elif name in defined_names:
                filtered_results[name] = meta

        all_items = self._static_items.copy()
        all_items.update(filtered_results)

        with self._lock:
            self._last_jedi_cache = (request_id, all_items)

        self.after(0, lambda: self._update_ui(all_items, term, request_id))

    def _update_ui(self, items, term, request_id):
        """Update UI from main thread."""
        if request_id != self._request_id:
            return

        if not self.winfo_exists():
            return

        exact, starts, includes = [], [], []

        for name, meta in items.items():
            if not term or name == term:
                exact.append((name, meta))
            elif name.startswith(term):
                starts.append((name, meta))
            elif term in name:
                includes.append((name, meta))

        new_active_data = exact + starts + includes

        if not new_active_data:
            self.hide()
            return

        self._render_items(new_active_data[:10], term)
        self.refresh_geometry()
        self.deiconify()
        self.active = True

    def _render_items(self, items_data, term):
        """Render visible items."""
        existing_texts = {i.get_text() for i in self.menu_items}

        for name, meta in items_data:
            if name not in existing_texts:
                self.add_item(name, meta)

        self.hide_all_items()

        display_items = []
        for name, meta in items_data:
            for item in self.menu_items:
                if item.get_text() == name:
                    display_items.append(item)
                    break

        self.show_items(display_items, term)

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

    def add_item(self, text, meta=None):
        kind = meta.get("type") if meta else ""
        item = AutoCompleteItem(self, text, kind=kind)
        item.meta = meta
        self.menu_items.append(item)

    def hide_all_items(self):
        for i in self.menu_items:
            i.grid_forget()

        self.active_items = []
        self.row = 0

    def show_items(self, items, term):
        self.active_items = items

        for i in items:
            i.grid(row=self.row, column=0, sticky=tk.EW)
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

    # Geometry - FIXED WIDTH

    def refresh_geometry(self, *_):
        """Position widget at cursor with fixed width."""
        if not self.winfo_exists():
            return

        pos = self.master.cursor_screen_location()
        height = max(30, len(self.active_items) * 30)
        self.geometry(f"{500}x{height}+{pos[0]}+{pos[1]}")

    def show(self, pos=None):
        """Show autocomplete at position or cursor."""
        if not self.winfo_exists():
            return

        self.active = True
        self.refresh_geometry()
        self.deiconify()
        self.lift()

    def hide(self, *_):
        """Hide autocomplete."""
        if not self.winfo_exists():
            return

        self.active = False
        self.withdraw()
        self.reset()

    def reset(self):
        """Reset internal state."""
        self.selected = 0
        self.row = 0

    # Choosing completion

    def choose(self, this=None, *_):
        """Accept completion and hide widget."""
        if not self.active_items:
            return

        if not this:
            this = self.active_items[self.selected]

        self.master.confirm_autocomplete(this.get_text())
        self.hide()

    # Key handlers
    def handle_escape(self):
        """Escape key - hide widget."""
        self.destroy_widget()

    def handle_enter(self):
        """Enter key - hide widget."""
        self.destroy_widget()

    def show_item_info(self, name, code, line, column):
        script = jedi.Script(code)
        completions = script.complete(line, column)

        for c in completions:
            if c.name == name:
                sig = c.get_signatures()
                sig_text = sig[0].to_string() if sig else ""

                return (
                    f"Name: {c.name}\n"
                    f"Type: {c.type}\n"
                    f"Description: {c.description}\n"
                    f"Signature: {sig_text}\n\n"
                    f"{c.docstring()}"
                )

        return "No documentation available."
