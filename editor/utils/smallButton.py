import customtkinter as ctk
from PIL import Image

class SmallButton(ctk.CTkFrame):
    """
    A small button for typical no-background colors and custom interaction.
    """

    def __init__(
        self,
        parent,
        image_path=None,
        command=None,
        size=(16, 16),
        hover_border=["#B7B7B7","#434343"],
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
            corner_radius=3,
            border_width=0,
            border_color=self.hover_border,
        )
        self.border_frame.pack(padx=1, pady=1, fill="both", expand=True)
        self.border_frame.pack_propagate(True)

        self.inner_frame = ctk.CTkFrame(self.border_frame, fg_color="transparent")
        self.inner_frame.pack(fill="both", expand=True, padx=1, pady=1)
        self.inner_frame.pack_propagate(True)

        if image_path:
            self.image = ctk.CTkImage(light_image=Image.open(image_path), size=size)
            self.icon = ctk.CTkLabel(self.inner_frame, image=self.image, text="",width=16,height=16)
            self.icon.pack(pady=(0,0))
        else:
            self.icon = None

        for widget in (
            self,
            self.border_frame,
            self.inner_frame,
            self.icon,
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