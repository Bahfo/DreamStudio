import logging
import tkinter as tk
import customtkinter as ctk
from threading import Thread
from .kind import Kind
from ...utils import Frame

# Lightweight logger for debugging Jedi parsing and UI events
logger = logging.getLogger(__name__)


class AutoCompleteItem(Frame):
    """Autocomplete item with fixed minimum width."""

    def __init__(
        self, master, text, height=30, kind=None, min_width=500, *args, **kwargs
    ):
        super().__init__(master, *args, **kwargs)

        theme = self.base.theme.autocomplete
        self.bg = theme["background"]
        self.fg = theme["foreground"]
        self.hbg = theme["activebackground"]
        self.hfg = theme["activeforeground"]
        self.accent = self.base.theme.accent
        self.configure(height=height)

        self.text = text
        self.kind = kind or ""
        self.selected = False
        self.min_width = min_width
        self.meta = None

        self.config(bg=self.bg, pady=2, padx=1)
        self.grid_columnconfigure(1, weight=1)

        self.kindw = Kind(self, self.master.autocomplete_kinds, kind or "")

        char_width = max(1, (min_width - 32) // 6)

        self.textw = tk.Text(
            self,
            font=("Jetbrains Mono", 10),
            fg=self.fg,
            bg=self.bg,
            width=char_width,
            height=1,
            wrap="none",
            highlightthickness=0,
            borderwidth=0,
        )
        self.textw.insert("1.0", text)
        self.textw.configure(state="disabled")

        self.infobtn = tk.Label(
            self,
            text="›",
            font=("Jetbrains Mono", 10),
            fg=self.fg,
            bg=self.bg,
            padx=3,
            cursor="hand2",
        )

        self.kindw.grid(row=0, column=0, sticky=tk.NSEW, padx=(1, 0))
        self.textw.grid(row=0, column=1, sticky=tk.EW, padx=2)
        self.infobtn.grid(row=0, column=2, sticky=tk.NSEW, padx=(0, 1))

        self._bind_events()

    def _bind_events(self):
        """Bind click and hover events."""
        for widget in (self, self.kindw, self.textw):
            widget.bind("<Button-1>", self.on_click)
            widget.bind("<Enter>", self.on_hover)
            widget.bind("<Leave>", self.off_hover)
        self.infobtn.bind("<Button-1>", self.on_info_click)

    def get_text(self):
        return self.text

    def get_kind(self):
        return self.kind

    def mark_term(self, term):
        """Highlight matched term with accent color."""
        if not term:
            self.textw.config(fg=self.fg)
            return

        self.textw.configure(state="normal")

        self.textw.tag_remove("highlight", "1.0", "end")

        start_idx = self.text.lower().find(term.lower())
        if start_idx != -1:
            end_idx = start_idx + len(term)
            self.textw.tag_add("highlight", f"1.{start_idx}", f"1.{end_idx}")
            self.textw.tag_config("highlight", foreground=self.accent)
        else:
            self.textw.config(fg=self.fg)

        self.textw.configure(state="disabled")

    def on_click(self, *args):
        """Handle click - choose item."""
        self.master.choose(self)

    def on_info_click(self, event):
        editor = self.master.master
        line, column = map(int, editor.index("insert").split("."))
        name = self.get_text()
        code = editor.get_all_text()

        root = self.winfo_toplevel()
        if not hasattr(root, "doc_widget") or not root.doc_widget.winfo_exists():
            root.doc_widget = Documentation(root)

        root.doc_widget.show_loading()
        root.doc_widget.show_near(self.infobtn)

        def fetch_docs():
            try:
                content = self.master.show_item_info(
                    name=name, code=code, line=line, column=column
                )

                root.doc_widget.after(0, lambda: root.doc_widget.show_content(content))
            except Exception as e:
                error_msg = f"Error loading documentation: {str(e)}"
                root.doc_widget.after(
                    0, lambda: root.doc_widget.show_content(error_msg)
                )

        # Threading should come from module scope to avoid repeated imports
        thread = Thread(target=fetch_docs, daemon=True)  # type: ignore
        thread.start()

    def on_hover(self, *args):
        if not self.selected:
            self._set_colors(self.hbg, self.fg)

    def off_hover(self, *args):
        if not self.selected:
            self._set_colors(self.bg, self.fg)

    def select(self):
        self.selected = True
        self._set_colors(self.hbg, self.hfg)

    def deselect(self):
        self.selected = False
        self._set_colors(self.bg, self.fg)

    def _set_colors(self, bg, fg):
        """Update colors."""
        self.config(bg=bg)
        self.kindw.config(bg=bg)
        self.textw.config(bg=bg, fg=fg)
        self.infobtn.config(bg=bg, fg=fg)


class Documentation(ctk.CTkToplevel):
    def __init__(
        self,
        master,
    ):
        super().__init__(master)
        self.width = 350
        self.height = 450
        self.overrideredirect(True)

        self.box = ctk.CTkTextbox(self, font=("Jetbrains Mono", 12))
        self.box.pack(fill="both", expand=True, padx=5, pady=5)
        self.box.configure(state="disabled")

        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)

        self.bind("<Escape>", lambda e: self.withdraw())
        self.bind(
            "<FocusOut>",
            lambda e: (
                self.withdraw()
                if not self.winfo_containing(e.x_root, e.y_root)
                else None
            ),
        )

    def show_loading(self):
        """Show loading state."""
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        self.box.insert("1.0", "Loading documentation...")
        self.box.configure(state="disabled")

    def show_content(self, text):
        """Show documentation content."""
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        self.box.insert("1.0", text)
        self.box.configure(state="disabled")

    def show_near(self, widget):
        x = widget.winfo_rootx() + widget.winfo_width() + 5
        y = widget.winfo_rooty()
        self.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.deiconify()
