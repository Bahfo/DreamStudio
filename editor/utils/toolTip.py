import customtkinter as ctk
import tkinter as tk

class ToolTip(ctk.CTkFrame):
    """
    A tooltip widget that displays informative text when hovering over a widget.
    """

    def __init__(
        self, widget, text, delay=400, bg="#2b2b2b", fg="white", font=("Segoe UI", 10)
    ):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.bg = bg
        self.fg = fg
        self.font = font

        self.tip_window = None
        self._after_id = None

        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._unschedule)
        widget.bind("<Motion>", self._move_tip_position)

    def _schedule(self, event=None):
        self._unschedule()
        self._after_id = self.widget.after(self.delay, self.show_tip)

    def _unschedule(self, event=None):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self.hide_tip()

    def _move_tip_position(self, event=None):
        if self.tip_window:
            x = event.x_root + 16
            y = event.y_root + 12
            try:
                self.tip_window.wm_geometry(f"+{x}+{y}")
            except Exception:
                pass

    def show_tip(self):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 40
        y = self.widget.winfo_rooty() + 20

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            bg=self.bg,
            fg=self.fg,
            font=self.font,
            bd=0,
            padx=6,
            pady=3,
        )
        label.pack()

    def hide_tip(self):
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None