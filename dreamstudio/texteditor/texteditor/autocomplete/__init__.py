import jedi
import tkinter as tk
from itertools import chain
from threading import Thread, Lock

from ...utils import Toplevel
from .item import AutoCompleteItem
from .kinds import Kinds
from .languages.python_completions import python_completions

class AutoComplete(Toplevel):
    """Optimized AutoComplete class with asynchronous Jedi processing."""

    def __init__(self, master, items=None, active=False, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.autocomplete_kinds = Kinds(self)
        self.config(padx=1, pady=1, bg=self.base.theme.border)

        self.active = active
        if not self.active:
            self.withdraw()

        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.grid_columnconfigure(0, weight=1)

        self.menu_items = []
        self.active_items = []
        self.row = 0
        self.selected = 0
        
        # Performance/Threading controls
        self._lock = Lock()
        self._debounce_id = None
        self._jedi_thread = None
        
        if items is None:
            self.items = {}
        elif isinstance(items, list):
            self.items = {name: {"type": kind} for name, kind in items}
        else:
            self.items = items

        self.add_all_items()
        self.refresh_selected()

    def update_completions(self):
        """Updates completions using debouncing and background threading."""
        # Cancel previous pending update
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        
        # Debounce: Wait 50ms before starting the heavy Jedi computation
        self._debounce_id = self.after(50, self._request_jedi_update)

    def _request_jedi_update(self):
        """Prepares data and starts the background thread."""
        term = self.master.get_current_word()
        line, col = map(int, self.master.index("insert").split("."))
        code = self.master.get_all_text()
        
        # Start threading to prevent UI freezing
        if self._jedi_thread and self._jedi_thread.is_alive():
            return # Let the current one finish or implement a queue
            
        self._jedi_thread = Thread(
            target=self._compute_jedi, 
            args=(code, line, col, term), 
            daemon=True
        )
        self._jedi_thread.start()

    def _compute_jedi(self, code, line, col, term):
        """Heavy lifting done in a background thread."""
        try:
            script = jedi.Script(code)
            jedi_results = {c.name: {"type": c.type} for c in script.complete(line, col)}
        except Exception:
            jedi_results = {}

        # Merge results efficiently
        with self._lock:
            all_items = python_completions.copy()
            all_items.update(self.items)
            all_items.update(jedi_results)
            
            # Incorporate buffer words
            for w in self.master.words:
                if w not in all_items:
                    all_items[w] = {"type": "word"}
            
            self.items = all_items

        # Schedule UI update back on the main thread
        self.after(0, lambda: self._update_ui_items(term))

    def _update_ui_items(self, term):
        """Updates the actual widgets on the main thread."""
        if not self.winfo_exists(): return

        existing_texts = {i.get_text() for i in self.menu_items}
        
        # Only add widgets for items we don't have yet
        for name, meta in self.items.items():
            if name not in existing_texts:
                self.add_item(name, meta.get("type") if meta else None)

        # Filtering logic
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
            # Refresh geometry before showing to prevent flickering
            self.refresh_geometry() 
            self.show_items(new_active[:10], term) # Limit to top 10 for speed
            self.deiconify()
            self.active = True
        else:
            self.hide()

    def move_up(self, *_):
        if self.active:
            self.select(-1)
            return "break"

    def move_down(self, *_):
        if self.active:
            self.select(1)
            return "break"

    def add_all_items(self):
        for completion, meta in self.items.items():
            self.add_item(completion, meta.get("type") if meta else None)
        self.active_items = self.menu_items
        self.refresh_selected()

    def update_all_words(self):
        current_texts = self.get_items_text()
        for word in self.master.words:
            if word not in current_texts:
                self.add_item(word, "word")

    def add_item(self, text: str, kind=""):
        new_item = AutoCompleteItem(self, text, kind=kind)
        # We don't grid it yet to keep update_completions fast
        self.menu_items.append(new_item)

    def remove_item(self, item: AutoCompleteItem):
        item.grid_forget()
        if item in self.menu_items:
            self.menu_items.remove(item)
        item.destroy()

    def select(self, delta: int):
        if not self.active_items: return
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

    def get_items_text(self):
        return [i.get_text() for i in self.menu_items]

    def hide_all_items(self):
        for i in self.menu_items:
            i.grid_forget()
        self.active_items = []
        self.row = 0

    def show_items(self, items: list[AutoCompleteItem], term: str):
        self.active_items = items
        for i in items:
            i.grid(row=self.row, sticky=tk.EW)
            i.mark_term(term)
            self.row += 1
        self.reset_selection()

    def refresh_geometry(self, *_):
        pos = self.master.cursor_screen_location()
        self.geometry(f"+{pos[0]}+{pos[1]}")

    def show(self, pos: tuple[int, int]):
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

    def choose(self, this=None, *_):
        if not self.active_items:
            return
        if not this:
            this = self.active_items[self.selected]

        self.master.confirm_autocomplete(this.get_text())
        self.hide()
        return "break"