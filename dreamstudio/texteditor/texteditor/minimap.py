import tkinter as tk
from ..utils import Frame

class Minimap(Frame):
    MIN_SLIDER_HEIGHT = 20

    def __init__(self, master, textw, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.tw = textw
        self.base = master.base
        self._after_id = None
        
        # Performance: Pre-define the tiny font
        self.mini_font = ("Arial", 2)
        self.line_color = "#AAAAAA" # Simple gray for all text
        
        self.config(width=110, highlightthickness=0, bg=self.base.theme.border)
        
        self.cw = tk.Canvas(
            self, width=110, highlightthickness=0, 
            bg=self.base.theme.minimap.get("background", "#1e1e1e"),
            # Speed up rendering by disabling borders
            borderwidth=0
        )
        self.cw.pack(fill=tk.BOTH, expand=True)

        # Slider: A simple outlined frame
        self.slider = tk.Frame(
            self.cw, 
            bg=self.base.theme.border,
            highlightbackground="white", 
            highlightthickness=1,
            cursor="hand2"
        )
        
        # Interaction
        self.cw.bind("<Button-1>", self._click_scroll)
        self.cw.bind("<B1-Motion>", self._click_scroll)
        
        # Track main text changes
        self.tw.bind("<<Change>>", self._debounce_draw)
        self.tw.bind("<Configure>", self._debounce_draw)
        
        # Sync scroll
        self.tw.config(yscrollcommand=self._sync_slider_only)

        self._debounce_draw()

    def _debounce_draw(self, *args):
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(100, self.redraw)

    def redraw(self):
        """Draws actual text characters onto the canvas at a tiny scale."""
        if not self.cw.winfo_exists():
            return
            
        self.cw.delete("content")
        
        # Get text content (clamped for performance)
        # 1000 lines is usually plenty for a minimap preview
        lines = self.tw.get("1.0", "1000.0").splitlines()
        
        curr_y = 2
        line_height = 4 # Small spacing for size 2 font
        
        for line in lines:
            if line.strip():
                # We use anchor='nw' to align text to the top-left
                self.cw.create_text(
                    5, curr_y,
                    text=line,
                    fill=self.line_color,
                    font=self.mini_font,
                    anchor="nw",
                    tags="content"
                )
            curr_y += line_height
            
        self._sync_slider_only()

    def _sync_slider_only(self, *args):
        try:
            top, bottom = self.tw.yview()
            h = self.cw.winfo_height()
            
            slider_y = top * h
            slider_h = max((bottom - top) * h, self.MIN_SLIDER_HEIGHT)
            
            # Prevent slider from jittering out of bounds
            if slider_y + slider_h > h:
                slider_y = h - slider_h

            self.slider.place(x=0, y=max(0, slider_y), width=self.cw.winfo_width(), height=slider_h)
        except (tk.TclError, AttributeError):
            pass

    def _click_scroll(self, event):
        h = self.cw.winfo_height()
        if h > 0:
            fraction = event.y / h
            view_range = self.tw.yview()
            view_size = view_range[1] - view_range[0]
            target = fraction - (view_size / 2)
            self.tw.yview_moveto(max(0, min(target, 1.0)))

    def attach(self, textw):
        self.tw = textw
        self._debounce_draw()