import tkinter as tk
from .kind import Kind
from ...utils import Frame

class AutoCompleteItem(Frame):
    """
    Optimized AutoComplete item.
    - Fixed ValueError by matching (self, text, kind) signature.
    - Reduced size by tightening padding and font.
    - Minimalist layout to prevent lag.
    """
    def __init__(self, master, text, kind=None, *args, **kwargs):
        # Explicitly accept text and kind so they don't move into *args
        super().__init__(master, *args, **kwargs)
        
        # 1. Theme and Data Cache
        theme = self.base.theme.autocomplete
        self.bg = theme["background"]
        self.fg = theme["foreground"]
        self.hbg = theme["activebackground"]
        self.hfg = theme["activeforeground"]
        self.accent = self.base.theme.accent

        self.text = text
        self.kind = kind
        self.selected = False

        # 2. Compact Configuration
        self.config(bg=self.bg, pady=0) 
        self.grid_columnconfigure(1, weight=1)

        # 3. Smaller, Faster Widgets
        # Kind Icon
        self.kindw = Kind(self, self.master.autocomplete_kinds, kind)
        
        # Text - Set width to a fixed value to prevent the popup from being too large
        self.textw = tk.Text(
            self, font=("Consolas", 10), fg=self.fg, bg=self.bg,
            relief=tk.FLAT, highlightthickness=0, height=1,
            width=25, # Controls horizontal size
            padx=2, pady=1, cursor="arrow", state=tk.DISABLED,
            exportselection=False, takefocus=False
        )
        self.textw.tag_config("term", foreground=self.accent)

        # Info Button - Compact '›' instead of 'ⓘ'
        self.infobtn = tk.Label(
            self, text="›", font=("Consolas", 10), 
            fg=self.fg, bg=self.bg, padx=3, cursor="hand2"
        )

        # 4. Grid Placement
        self.kindw.grid(row=0, column=0, sticky=tk.NSEW)
        self.textw.grid(row=0, column=1, sticky=tk.NSEW)
        self.infobtn.grid(row=0, column=2, sticky=tk.NSEW)

        # 5. Initialization
        self._set_text_internal(text)
        self._bind_events()

    def _set_text_internal(self, text):
        """Helper to update text without widget churn."""
        self.textw.config(state=tk.NORMAL)
        self.textw.delete(1.0, tk.END)
        self.textw.insert(tk.END, text)
        self.textw.config(state=tk.DISABLED)

    def _bind_events(self):
        """Bind events once."""
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
        """Highlights the matched part of the string."""
        self.textw.tag_remove("term", "1.0", tk.END)
        if not term:
            return

        start_index = self.text.lower().find(term.lower())
        if start_index != -1:
            end_index = start_index + len(term)
            self.textw.tag_add("term", f"1.{start_index}", f"1.{end_index}")

    def on_click(self, *args):
        self.master.choose(self)
        return "break"

    def on_info_click(self, event):
        """Placeholder for documentation."""
        return "break"

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
        """Batch update colors to reduce UI flickering."""
        self.config(bg=bg)
        self.kindw.config(bg=bg)
        self.textw.config(bg=bg, fg=fg)
        self.infobtn.config(bg=bg, fg=fg)