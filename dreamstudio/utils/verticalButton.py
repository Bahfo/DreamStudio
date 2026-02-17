import customtkinter as ctk
from PIL import Image

class VerticalButton(ctk.CTkFrame):
    """
    A vertical button with an icon above text.
    """

    def __init__(
        self,
        parent,
        image_path=None,
        text="",
        command=None,
        size=(27, 27),
        hover_border=["#454545","#bebebe"],
        click_border=["#737373","#808080"],
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent")

        self.command = command
        self.hover_border = hover_border
        self.click_border = click_border

        self.border_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=6,
            border_width=0,
            border_color=self.hover_border,
        )
        self.border_frame.pack(padx=2, pady=2, fill="both", expand=True)

        self.inner_frame = ctk.CTkFrame(self.border_frame, fg_color="transparent")
        self.inner_frame.pack(fill="both", expand=True, padx=4, pady=4)

        if image_path:
            self.image = ctk.CTkImage(light_image=Image.open(image_path), size=size)
            self.icon = ctk.CTkLabel(self.inner_frame, image=self.image, text="")
            self.icon.pack(pady=(0, 2))
        else:
            self.icon = None

        self.label = ctk.CTkLabel(
            self.inner_frame,
            text=text,
            font=("Segoe UI", 12),
            text_color=["#1E1E1E", "#c8c8c8"],
        )
        self.label.pack()

        for widget in (
            self,
            self.border_frame,
            self.inner_frame,
            self.icon,
            self.label,
        ):
            if widget:
                widget.bind("<Enter>", self._on_enter)
                widget.bind("<Leave>", self._on_leave)
                widget.bind("<Button-1>", self._on_click)
                widget.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event):
        self.border_frame.configure(border_width=1)

    def _on_leave(self, event):
        self.border_frame.configure(border_width=0)

    def _on_click(self, event):
        self.border_frame.configure(border_color=self.click_border)
        if self.command:
            self.command()

    def _on_release(self, event):
        self.border_frame.configure(border_color=self.hover_border)