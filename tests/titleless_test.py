import customtkinter as ctk


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.geometry("1100x700")
        self.minsize(800, 500)
        self.overrideredirect(True)

        self._is_maximized = False
        self._normal_geometry = self.geometry()

        self._drag_x = 0
        self._drag_y = 0

        self._build_ui()
        self._bind_events()

    def _build_ui(self):
        # Root layout
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Top title bar
        self.title_bar = ctk.CTkFrame(
            self, height=36, corner_radius=0, fg_color="#2b2b2b"
        )
        self.title_bar.grid(row=0, column=0, sticky="ew")
        self.title_bar.grid_propagate(False)
        self.title_bar.grid_columnconfigure(1, weight=1)

        left_area = ctk.CTkFrame(
            self.title_bar, corner_radius=0, fg_color="transparent"
        )
        left_area.grid(row=0, column=0, sticky="w", padx=10)

        self.app_icon = ctk.CTkLabel(
            left_area, text="◆", text_color="#8ab4f8", font=("Segoe UI", 14, "bold")
        )
        self.app_icon.pack(side="left", padx=(0, 8))

        self.title_label = ctk.CTkLabel(
            left_area, text="Custom Studio", font=("Segoe UI", 12), text_color="#e8eaed"
        )
        self.title_label.pack(side="left")

        self.window_buttons = ctk.CTkFrame(
            self.title_bar, corner_radius=0, fg_color="transparent"
        )
        self.window_buttons.grid(row=0, column=2, sticky="e", padx=6)

        self.min_btn = ctk.CTkButton(
            self.window_buttons,
            text="—",
            width=42,
            height=26,
            corner_radius=4,
            fg_color="#2b2b2b",
            hover_color="#3c4043",
            command=self.iconify,
        )
        self.min_btn.pack(side="left", padx=2)

        self.max_btn = ctk.CTkButton(
            self.window_buttons,
            text="▢",
            width=42,
            height=26,
            corner_radius=4,
            fg_color="#2b2b2b",
            hover_color="#3c4043",
            command=self.toggle_maximize,
        )
        self.max_btn.pack(side="left", padx=2)

        self.close_btn = ctk.CTkButton(
            self.window_buttons,
            text="✕",
            width=42,
            height=26,
            corner_radius=4,
            fg_color="#2b2b2b",
            hover_color="#c5221f",
            command=self.destroy,
        )
        self.close_btn.pack(side="left", padx=2)

        # Secondary toolbar / tab strip
        self.top_strip = ctk.CTkFrame(
            self, height=34, corner_radius=0, fg_color="#1f1f1f"
        )
        self.top_strip.grid(row=1, column=0, sticky="ew")
        self.top_strip.grid_propagate(False)
        self.top_strip.grid_columnconfigure(0, weight=1)

        tab_holder = ctk.CTkFrame(
            self.top_strip, corner_radius=0, fg_color="transparent"
        )
        tab_holder.grid(row=0, column=0, sticky="w", padx=8)

        self.tab1 = ctk.CTkButton(
            tab_holder,
            text="main.py",
            width=90,
            height=24,
            corner_radius=6,
            fg_color="#303134",
            hover_color="#3c4043",
        )
        self.tab1.pack(side="left", padx=(0, 6), pady=5)

        self.tab2 = ctk.CTkButton(
            tab_holder,
            text="settings.py",
            width=100,
            height=24,
            corner_radius=6,
            fg_color="#1f1f1f",
            hover_color="#303134",
        )
        self.tab2.pack(side="left", padx=(0, 6), pady=5)

        self.spacer = ctk.CTkFrame(
            self.top_strip, corner_radius=0, fg_color="transparent"
        )
        self.spacer.grid(row=0, column=1, sticky="e")

        # Main content area
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="#202124")
        self.content.grid(row=2, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        editor = ctk.CTkTextbox(
            self.content,
            corner_radius=10,
            fg_color="#1e1e1e",
            text_color="#e8eaed",
            border_width=1,
            border_color="#3c4043",
        )
        editor.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        editor.insert("1.0", "// Custom window chrome example\n")
        editor.insert("2.0", "print('Hello from a custom title bar')\n")

    def _bind_events(self):
        for widget in (self.title_bar, self.title_label, self.app_icon):
            widget.bind("<Button-1>", self.start_move)
            widget.bind("<B1-Motion>", self.do_move)
            widget.bind("<Double-Button-1>", self.toggle_maximize)

    def start_move(self, event):
        if self._is_maximized:
            return
        self._drag_x = event.x
        self._drag_y = event.y

    def do_move(self, event):
        if self._is_maximized:
            return
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")

    def toggle_maximize(self):
        if not self._is_maximized:
            self._normal_geometry = self.geometry()
            self._is_maximized = True
            self.overrideredirect(False)
            self.state("zoomed")
            self.after(10, lambda: self.overrideredirect(True))
            self.max_btn.configure(text="❐")
        else:
            self._is_maximized = False
            self.overrideredirect(False)
            self.state("normal")
            self.geometry(self._normal_geometry)
            self.after(10, lambda: self.overrideredirect(True))
            self.max_btn.configure(text="▢")


if __name__ == "__main__":
    app = App()
    app.mainloop()
