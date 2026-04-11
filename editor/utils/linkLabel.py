import customtkinter as ctk


class LinkLabel(ctk.CTkFrame):
    """
    A clickable link label that changes color on hover.
    """

    def __init__(
        self,
        parent,
        width,
        height,
        link_color="#1a73e8",
        after_link_color="#551a8b",
        corner_radius=5,
        font=None,
        text="",
        command=None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.command = command
        self.link_color = link_color
        self.after_link_color = after_link_color
        self.corner_radius = corner_radius
        self.font = font or ("inter", 12)
        self.width = width
        self.height = height

        self.hoverframe = ctk.CTkFrame(
            self,
            width=self.width,
            height=self.height,
            fg_color=parent.cget("fg_color"),
            corner_radius=self.corner_radius,
            border_width=0,
        )
        self.hoverframe.pack(fill="both")
        self.hoverframe.pack_propagate(False)

        self.label = ctk.CTkLabel(
            self.hoverframe,
            text=text,
            font=self.font,
            text_color=self.link_color,
        )
        self.label.pack()

        for widget in (self, self.hoverframe, self.label):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def _on_enter(self, event):
        self.label.configure(text_color=self.after_link_color)

    def _on_leave(self, event):
        self.label.configure(text_color=self.link_color)

    def _on_click(self, event):
        if self.command:
            self.command()
