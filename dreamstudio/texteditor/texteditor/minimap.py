import tkinter as tk
from ..utils import Frame
from .peer import TextPeer

class Minimap(Frame):
    MIN_SLIDER_HEIGHT = 20  # Minimum height of the slider in pixels
    BUFFER_LINES = 5        # Extra lines above/below for context

    def __init__(self, master, textw, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.tw = textw
        self.base = master.base
        self.slider_drag_offset = 0  # For accurate drag handling
        self._after_id = None        # For scheduled sync callbacks
        self.config(highlightthickness=0, bg=self.base.theme.border)

        # 1. Canvas container
        self.cw = tk.Canvas(
            self, width=100, highlightthickness=0, **self.base.theme.minimap
        )
        self.cw.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(1, 0))

        # 2. TextPeer (shares buffer with main text)
        self.peer = TextPeer(
            self.cw,
            self.tw,
            font=("Arial", 2),
            state=tk.DISABLED,
            width=100,
            highlightthickness=0,
            bd=0,
            wrap=tk.NONE,
            **self.base.theme.minimap
        )
        self.peer_window = self.cw.create_window(0, 0, window=self.peer, anchor="nw", width=100)

        # 3. Slider (represents visible region)
        self.slider = tk.Frame(
            self.cw,
            bg=self.base.theme.border,
            highlightbackground="white",
            highlightthickness=1,
            cursor="hand2"
        )
        self.slider.place(x=0, y=0, width=100, height=self.MIN_SLIDER_HEIGHT)

        # Bindings
        self.slider.bind("<Button-1>", self._start_drag)
        self.slider.bind("<B1-Motion>", self._drag)
        self.cw.bind("<Button-1>", self._click_scroll)
        self.bind("<Configure>", self._on_resize)
        self.tw.bind("<<Change>>", self.sync_scroll)  # Custom virtual event if implemented
        self.tw.bind("<Configure>", self.sync_scroll)

        # Schedule initial sync
        self._schedule_sync()

        # Cleanup on destroy
        self.bind("<Destroy>", lambda e: self._cancel_sync())

    def _schedule_sync(self):
        self._after_id = self.after(100, self.sync_scroll)

    def _cancel_sync(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _on_resize(self, event=None):
        """Adjust peer height and slider on minimap resize."""
        try:
            total_lines = max(1, int(self.tw.index("end-1c").split('.')[0]))
            canvas_h = self.cw.winfo_height()
            # Scale peer to match total lines with minimal performance overhead
            self.cw.itemconfig(self.peer_window, height=canvas_h * total_lines / max(1, int(total_lines / 50)))
        except Exception:
            pass
        self.sync_scroll()

    def sync_scroll(self, event=None):
        """Update slider position/size and peer scroll."""
        if not self.tw.winfo_exists() or not self.cw.winfo_exists():
            return

        try:
            top, bottom = self.tw.yview()
            canvas_h = self.cw.winfo_height()
            if canvas_h <= 0:
                return

            slider_y = top * canvas_h
            slider_h = max((bottom - top) * canvas_h, self.MIN_SLIDER_HEIGHT)
            self.slider.place(y=slider_y, height=slider_h)

            # Move peer to match main text scroll
            self.peer.yview_moveto(top)
        except Exception:
            pass

        # Reschedule next sync for continuous updates
        self._schedule_sync()

    def _start_drag(self, event):
        """Store offset from mouse to slider top for precise dragging."""
        self.slider_drag_offset = event.y

    def _drag(self, event):
        """Drag slider to scroll main text."""
        canvas_h = self.cw.winfo_height()
        if canvas_h <= 0:
            return

        mouse_y = self.slider.winfo_y() + event.y - self.slider_drag_offset
        fraction = mouse_y / canvas_h
        fraction = max(0, min(fraction, 1.0))
        self.tw.yview_moveto(fraction)
        self.sync_scroll()

    def _click_scroll(self, event):
        """Click on minimap to jump scroll position."""
        canvas_h = self.cw.winfo_height()
        if canvas_h <= 0:
            return

        fraction = event.y / canvas_h
        fraction = max(0, min(fraction, 1.0))
        self.tw.yview_moveto(fraction)
        self.sync_scroll()

    def attach(self, textw):
        """Attach minimap to a new text widget buffer."""
        self.tw = textw
        if self.peer.winfo_exists():
            self.peer.destroy()

        self.peer = TextPeer(
            self.cw,
            self.tw,
            font=("Arial", 2),
            state=tk.DISABLED,
            width=100,
            highlightthickness=0,
            bd=0,
            wrap=tk.NONE,
            **self.base.theme.minimap
        )
        self.peer_window = self.cw.create_window(0, 0, window=self.peer, anchor="nw", width=100)
        self.sync_scroll()
