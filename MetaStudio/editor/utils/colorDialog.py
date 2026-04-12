import customtkinter as ctk


class ColorDialog(ctk.CTkToplevel):
    """
    A comprehensive color picker dialog with RGB sliders, hex input,
    a default color palette, and recent colors.
    """

    def __init__(self, master, initial_color="#FFFFFF"):
        super().__init__(master)
        self.title("Color Picker")
        self.resizable(False, False)
        self.geometry("330x400")

        self.current_rgb = self.hex_to_rgb(initial_color)
        self.current_hex = initial_color
        self.selected_color = None
        self.recent_colors = []
        self.max_recent = 10

        self.transient(master)

        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=10)

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        self.preview_frame = ctk.CTkFrame(
            top_frame, width=120, height=135, corner_radius=5, fg_color=self.current_hex
        )
        self.preview_frame.pack(side="left", padx=(0, 10))

        self.palette_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        self.palette_frame.pack(side="left", fill="both", expand=True)

        self.default_palette = [
            "#000000",
            "#4B4B4B",
            "#9C9C9C",
            "#CDCDCD",
            "#FFFFFF",
            "#6F0000",
            "#FF0000",
            "#FF4D00",
            "#FF9D00",
            "#FFD000",
            "#EAFF00",
            "#A6FF00",
            "#2EB700",
            "#008B09",
            "#006B1B",
            "#00A2ED",
            "#008CFF",
            "#0046AF",
            "#000073",
            "#4E008E",
        ]
        self._create_palette_buttons()

        slider_frame = ctk.CTkFrame(self, fg_color="transparent")
        slider_frame.pack(fill="x", padx=10, pady=5)

        self.slider_r, self.label_r = self._create_slider(
            slider_frame, "R", self.current_rgb[0]
        )
        self.slider_g, self.label_g = self._create_slider(
            slider_frame, "G", self.current_rgb[1]
        )
        self.slider_b, self.label_b = self._create_slider(
            slider_frame, "B", self.current_rgb[2]
        )

        self.hex_entry = ctk.CTkEntry(slider_frame, width=100, font=("inter", 13))
        self.hex_entry.pack(pady=(5, 5), side="right")
        self.hex_label = ctk.CTkLabel(
            slider_frame, width=40, text="Hex:", font=("inter", 13)
        )
        self.hex_label.pack(pady=(5, 5), side="right")
        self.gradient_label = ctk.CTkLabel(
            slider_frame, width=70, text="Gradients", font=("inter", 13)
        )
        self.gradient_label.pack(pady=(5, 5), side="left", padx=(0, 10))
        self.hex_entry.insert(0, self.current_hex)
        self.hex_entry.bind("<KeyRelease>", lambda e: self._hex_live_update())
        self.hex_entry.bind("<Return>", lambda e: self._hex_changed())
        self.hex_entry.bind("<FocusOut>", lambda e: self._hex_changed())

        self.recent_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.recent_frame.pack(fill="x", padx=10, pady=(5, 0))
        self._update_recent_colors()

        cancel_button = ctk.CTkButton(
            bottom_frame,
            text="Cancel",
            width=80,
            font=("inter", 12),
            command=self._on_cancel,
        )
        cancel_button.pack(side="right", padx=5)
        ok_button = ctk.CTkButton(
            bottom_frame,
            text="OK",
            width=80,
            font=("inter", 12),
            command=self._on_ok,
        )
        ok_button.pack(side="right", padx=5)

        self.update_preview()

    def _create_slider(self, parent, label_text, initial_value):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(2, 5))
        label = ctk.CTkLabel(frame, text=label_text, font=("inter", 14))
        label.pack(side="left")
        slider = ctk.CTkSlider(
            frame, from_=0, to=255, number_of_steps=255, command=self._slider_changed
        )
        slider.set(initial_value)
        slider.pack(side="left", fill="x", expand=True, padx=(5, 5))
        value_label = ctk.CTkLabel(
            frame, text=str(initial_value), width=30, font=("inter", 13)
        )
        value_label.pack(side="right")
        return slider, value_label

    def _create_palette_buttons(self):
        btn_size = 30
        buttons_per_row = 5
        for idx, color in enumerate(self.default_palette):
            btn = ctk.CTkButton(
                self.palette_frame,
                fg_color=color,
                width=btn_size,
                height=btn_size,
                corner_radius=5,
                text="",
                command=lambda c=color: self._palette_color_selected(c),
            )
            row = idx // buttons_per_row
            col = idx % buttons_per_row
            btn.grid(row=row, column=col, padx=2, pady=2)

    def _palette_color_selected(self, hex_color):
        self.current_hex = hex_color
        self.update_sliders_from_hex()
        self._save_recent_color(hex_color)

    def _slider_changed(self, value):
        r = int(self.slider_r.get())
        g = int(self.slider_g.get())
        b = int(self.slider_b.get())
        self.current_rgb = [r, g, b]
        self.label_r.configure(text=str(r))
        self.label_g.configure(text=str(g))
        self.label_b.configure(text=str(b))
        self.update_preview()
        self._save_recent_color(self.rgb_to_hex(r, g, b))

    def _hex_changed(self):
        hex_value = self.hex_entry.get()
        if not hex_value.startswith("#"):
            hex_value = "#" + hex_value
        self.current_hex = hex_value
        self.update_sliders_from_hex()
        self._save_recent_color(self.current_hex)

    def _hex_live_update(self):
        hex_value = self.hex_entry.get()
        if not hex_value.startswith("#"):
            hex_value = "#" + hex_value
        if len(hex_value) == 7:
            try:
                self.current_hex = hex_value
                self.current_rgb = self.hex_to_rgb(self.current_hex)
                self.slider_r.set(self.current_rgb[0])
                self.slider_g.set(self.current_rgb[1])
                self.slider_b.set(self.current_rgb[2])
                self.label_r.configure(text=str(self.current_rgb[0]))
                self.label_g.configure(text=str(self.current_rgb[1]))
                self.label_b.configure(text=str(self.current_rgb[2]))
                self.update_preview()
            except ValueError:
                pass

    def update_sliders_from_hex(self):
        hex_code = self.current_hex.lstrip("#")
        if len(hex_code) != 6:
            return
        try:
            self.current_rgb = self.hex_to_rgb(self.current_hex)
            self.slider_r.set(self.current_rgb[0])
            self.slider_g.set(self.current_rgb[1])
            self.slider_b.set(self.current_rgb[2])
            self.label_r.configure(text=str(self.current_rgb[0]))
            self.label_g.configure(text=str(self.current_rgb[1]))
            self.label_b.configure(text=str(self.current_rgb[2]))
            self.update_preview()
        except ValueError:
            pass

    def update_preview(self):
        hex_color = self.rgb_to_hex(*self.current_rgb)
        self.current_hex = hex_color
        self.preview_frame.configure(fg_color=hex_color)
        self.hex_entry.delete(0, "end")
        self.hex_entry.insert(0, hex_color)

    def _save_recent_color(self, color):
        if color in self.recent_colors:
            return
        self.recent_colors.insert(0, color)
        if len(self.recent_colors) > self.max_recent:
            self.recent_colors.pop()
        self._update_recent_colors()

    def _update_recent_colors(self):
        for widget in self.recent_frame.winfo_children():
            widget.destroy()
        btn_size = 25
        for idx, color in enumerate(self.recent_colors):
            btn = ctk.CTkButton(
                self.recent_frame,
                fg_color=color,
                width=btn_size,
                height=btn_size,
                corner_radius=5,
                text="",
                command=lambda c=color: self._palette_color_selected(c),
            )
            btn.grid(row=0, column=idx, padx=2)

    def rgb_to_hex(self, r, g, b):
        return f"#{r:02X}{g:02X}{b:02X}"

    def hex_to_rgb(self, hex_code):
        hex_code = hex_code.lstrip("#")
        if len(hex_code) != 6:
            raise ValueError("Invalid hex code")
        r = int(hex_code[0:2], 16)
        g = int(hex_code[2:4], 16)
        b = int(hex_code[4:6], 16)
        return [r, g, b]

    def _on_ok(self):
        self._hex_changed()
        self.selected_color = self.current_hex
        self.destroy()

    def _on_cancel(self):
        self.selected_color = None
        self.destroy()

    def get_color(self):
        self.wait_window()
        return self.selected_color
