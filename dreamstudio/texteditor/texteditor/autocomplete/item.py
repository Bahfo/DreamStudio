import tkinter as tk
from .kind import Kind
from ...utils import Frame

class AutoCompleteItem(Frame):
    """Autocomplete item with fixed minimum width."""
    
    def __init__(self, master, text, kind=None, min_width=300, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        
        theme = self.base.theme.autocomplete
        self.bg = theme["background"]
        self.fg = theme["foreground"]
        self.hbg = theme["activebackground"]
        self.hfg = theme["activeforeground"]
        self.accent = self.base.theme.accent

        self.text = text
        self.kind = kind
        self.selected = False
        self.min_width = min_width

        # Frame config
        self.config(bg=self.bg, pady=2, padx=1)
        self.grid_columnconfigure(1, weight=1)

        # Kind Icon
        self.kindw = Kind(self, self.master.autocomplete_kinds, kind)

        # Text label - calculate character width
        # Consolas 10pt ≈ 6 pixels per character
        # Account for icon (24px) + padding (8px) = ~32px
        char_width = max(1, (min_width - 32) // 6)
        
        self.textw = tk.Label(
            self, text=text, font=("Consolas", 10), fg=self.fg, bg=self.bg,
            anchor=tk.W, justify=tk.LEFT,
            width=char_width,
            wraplength=min_width - 32
        )

        # Info Button
        self.infobtn = tk.Label(
            self, text="›", font=("Consolas", 10),
            fg=self.fg, bg=self.bg, padx=3, cursor="hand2"
        )

        # Grid layout
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

        start_idx = self.text.lower().find(term.lower())
        if start_idx == -1:
            self.textw.config(fg=self.fg)
            return

        self.textw.config(fg=self.accent)

    def on_click(self, *args):
        """Handle click - choose item."""
        self.master.choose(self)

    def on_info_click(self, event):
        """Info button click."""
        pass

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