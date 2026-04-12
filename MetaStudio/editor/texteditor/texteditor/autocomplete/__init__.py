import jedi
import tkinter as tk
import logging
from threading import Thread, Lock

from ...utils import Toplevel

logger = logging.getLogger(__name__)
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

        # Bind mouse wheel for scrolling
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", self._on_mousewheel)  # Linux
        self.bind("<Button-5>", self._on_mousewheel)  # Linux

        self.menu_items = []
        self.active_items = []
        self.row = 0
        self.selected = 0

        self._lock = Lock()
        self._debounce_id = None
        self._jedi_thread = None
        self._request_id = 0
        self._scroll_offset = 0  # For scrolling through completions

        if items is None:
            self.items = {}
        elif isinstance(items, list):
            self.items = {name: {"type": kind} for name, kind in items}
        else:
            self.items = items

        self._static_items = python_completions.copy()
        self._static_items.update(self.items)

        self._builtin_names = set(python_completions.keys())

        # Widget pooling: Pre-create 10 items for reuse
        self._item_pool = []
        self._pool_size = 10
        for _ in range(self._pool_size):
            item = AutoCompleteItem(self, "")
            self._item_pool.append(item)

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
        line, col = map(int, self.master.index(tk.INSERT).split("."))
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
            logger.exception("Jedi computation failed in _compute_jedi")
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

    def _score_match(self, term, name):
        """Score a completion match for better relevance."""
        if not term:
            return 0
        if not name:
            return -1000  # Very low score for empty names

        term_lower = term.lower()
        name_lower = name.lower()

        # Exact match
        if term_lower == name_lower:
            return 1000

        # Starts with term
        if name_lower.startswith(term_lower):
            return 900 + len(term)  # Longer term = higher score

        # Contains term
        pos = name_lower.find(term_lower)
        if pos != -1:
            # Earlier position = higher score
            # Fewer gaps between matched chars = higher score
            return 800 - pos * 10

        # Fuzzy matching: count consecutive matches
        # Simple version: count how many chars of term appear in order in name
        term_idx = 0
        name_idx = 0
        matched_chars = 0

        while term_idx < len(term_lower) and name_idx < len(name_lower):
            if term_lower[term_idx] == name_lower[name_idx]:
                matched_chars += 1
                term_idx += 1
            name_idx += 1

        if matched_chars > 0:
            # Score based on percentage of term matched and consecutiveness
            return 700 + (matched_chars * 10) - ((len(term) - matched_chars) * 5)

        return 0  # No match

    def _update_ui(self, items, term, request_id):
        """Update UI from main thread."""
        if request_id != self._request_id:
            return

        if not self.winfo_exists():
            return

        if not term:
            # No term, show all items
            scored_items = [(name, meta, 0) for name, meta in items.items()]
        else:
            # Score all items
            scored_items = []
            for name, meta in items.items():
                score = self._score_match(term, name)
                if score > 0:  # Only include items with some match
                    scored_items.append((name, meta, score))

        # Sort by score (descending) and take items based on scroll offset
        scored_items.sort(key=lambda x: x[2], reverse=True)
        # Track maximum offset for scrolling (show 10 items at a time)
        self._scroll_max = max(0, len(scored_items) - 10)
        # Get items for current view (10 items at a time)
        start_idx = self._scroll_offset
        end_idx = start_idx + 10
        new_active_data = [
            (name, meta) for name, meta, score in scored_items[start_idx:end_idx]
        ]

        if not new_active_data:
            self.hide()
            return

        self._render_items(new_active_data, term)
        self.refresh_geometry()
        self.deiconify()
        self.active = True

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling for completions."""
        if not self.active or not self.active_items:
            return "break"
        # Normalize wheel delta across platforms
        delta = 0
        if getattr(event, "num", None) in (4, 5):
            # Linux: Button-4 (up) and Button-5 (down)
            delta = -1 if getattr(event, "num") == 4 else 1
        else:
            # Windows/macOS
            delta = -1 if getattr(event, "delta", 0) > 0 else 1
        max_off = getattr(self, "_scroll_max", 0)
        current = getattr(self, "_scroll_offset", 0)
        self._scroll_offset = max(0, min(max_off, current + delta))
        # Refresh UI with new offset using cached items if available
        with self._lock:
            cache = getattr(self, "_last_jedi_cache", None)
        if cache:
            request_id, items = cache
            term = (
                self.master.get_current_word()
                if hasattr(self.master, "get_current_word")
                else ""
            )
            self._update_ui(items, term, request_id)
        return "break"

    def _render_items(self, items_data, term):
        """Render visible items using widget pool."""
        self.hide_all_items()

        # Use pooled widgets, updating their content
        display_items = []
        for i, (name, meta) in enumerate(items_data[: self._pool_size]):
            if i < len(self._item_pool):
                item = self._item_pool[i]
                item.text = name
                item.kind = meta.get("type") if meta else ""
                item.meta = meta
                # Update the UI components
                # For tk.Text widget, we need to delete and insert text
                item.textw.configure(state="normal")
                item.textw.delete("1.0", "end")
                item.textw.insert("1.0", name)
                item.textw.configure(state="disabled")
                item.kindw.set_kind(item.kind)
                display_items.append(item)

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
        # With widget pooling, we don't need to pre-add all items
        # Items will be added dynamically in _render_items
        self.active_items = []
        self.refresh_selected()

    # add_item is no longer needed with widget pooling
    # Keeping it for compatibility but it won't be used
    def add_item(self, text, meta=None):
        pass  # Widget pooling handles item creation

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
        height = max(27, len(self.active_items) * 27)
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
        # 1) Try to use cached Jedi completions for performance
        with self._lock:
            cache = getattr(self, "_last_jedi_cache", None)
        if cache:
            request_id, items = cache
            if name in items:
                comp = items[name].get("completion")
                if comp is not None:
                    sig_text = ""
                    try:
                        sig = comp.get_signatures()
                        sig_text = sig[0].to_string() if sig else ""
                    except Exception:
                        sig_text = ""
                    return (
                        f"Name: {comp.name}\n"
                        f"Type: {comp.type}\n"
                        f"Description: {comp.description}\n"
                        f"Signature: {sig_text}\n\n"
                        f"{comp.docstring()}"
                    )

        # 2) Fallback: compute using Jedi normally
        script = jedi.Script(code)
        try:
            completions = script.complete(line, column)
        except Exception:
            return "No documentation available."

        for c in completions:
            if c.name == name:
                sig_text = ""
                try:
                    sig = c.get_signatures()
                    sig_text = sig[0].to_string() if sig else ""
                except Exception:
                    sig_text = ""

                return (
                    f"Name: {c.name}\n"
                    f"Type: {c.type}\n"
                    f"Description: {c.description}\n"
                    f"Signature: {sig_text}\n\n"
                    f"{c.docstring()}"
                )

        return "No documentation available."
