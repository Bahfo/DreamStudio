import customtkinter as ctk
import json
import os

def open_settings_window():
        settings_and_preferences = ctk.CTk()
        settings_and_preferences.title("Settings and Preferences")
        settings_and_preferences.geometry("900x700")
        settings_and_preferences.resizable(True, True)

        CONFIG_FILE = "config.json"

        def save_theme(theme):
            config = {"theme": theme}
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)

        def load_theme():
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    return config.get("theme", "Dark")
            return "Dark"

        def switchTheme(event=None):
            user_theme = load_theme()
            save_theme(user_theme)
            ctk.set_appearance_mode(user_theme)

        scrollable_frame = ctk.CTkScrollableFrame(
            settings_and_preferences,
            fg_color="transparent",
            scrollbar_button_color="#2d2d2d",
            scrollbar_button_hover_color="#3b3b3b")
        scrollable_frame.pack(fill="both", expand=True, padx=20, pady=20)

        scrollable_frame.grid_columnconfigure(0, weight=1)

        # Section 1: Accessibility
        accessibility_label = ctk.CTkLabel(
            scrollable_frame,
            text="Accessibility",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        accessibility_label.grid(row=0, column=0, padx=0, pady=(0, 15), sticky='w')

        # Accessibility sub-frame for grouping
        accessibility_frame = ctk.CTkFrame(
            scrollable_frame,
            corner_radius=8)
        accessibility_frame.grid(row=1, column=0, padx=0, pady=(0, 20), sticky='ew')
        accessibility_frame.grid_columnconfigure(0, weight=1)
        accessibility_frame.grid_columnconfigure(1, weight=0)

        # Font Size in Accessibility
        settings_font_label = ctk.CTkLabel(
            accessibility_frame,
            text="Font Size",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        settings_font_label.grid(row=0, column=0, padx=(20, 10), pady=(15, 10), sticky="w")

        font_number_changer = ctk.CTkLabel(
            accessibility_frame,
            text="13",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        font_number_changer.grid(row=0, column=1, padx=(0, 30), pady=(15, 10), sticky="e")

        def on_font_slider_change(value):
            size = int(float(value))
            font_number_changer.configure(text=str(size))

        font_change_slider = ctk.CTkSlider(
            accessibility_frame,
            from_=8,
            to=24,
            number_of_steps=16,
            command=on_font_slider_change,
            width=270)
        font_change_slider.set(13)
        font_change_slider.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        on_font_slider_change(font_change_slider.get())

        # High Contrast Mode
        high_contrast_label = ctk.CTkLabel(
            accessibility_frame,
            text="High Contrast Mode",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        high_contrast_label.grid(row=2, column=0, padx=(20, 10), pady=(0, 10), sticky="w")

        high_contrast_switch = ctk.CTkSwitch(
            accessibility_frame,
            text="")
        high_contrast_switch.grid(row=2, column=1, padx=(0, 20), pady=(0, 10), sticky="e")

        # Section 2: Appearance/Theme
        appearance_label = ctk.CTkLabel(
            scrollable_frame,
            text="Appearance",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        appearance_label.grid(row=2, column=0, padx=0, pady=(0, 15), sticky='w')

        appearance_frame = ctk.CTkFrame(
            scrollable_frame,
            corner_radius=8)
        appearance_frame.grid(row=3, column=0, padx=0, pady=(0, 20), sticky='ew')
        appearance_frame.grid_columnconfigure(0, weight=1)
        appearance_frame.grid_columnconfigure(1, weight=0)

        # Theme Mode
        theme_label = ctk.CTkLabel(
            appearance_frame,
            text="Theme Mode",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        theme_label.grid(row=0, column=0, padx=(20, 10), pady=(15, 10), sticky="w")

        theme_var = ctk.StringVar(value="Dark")
        theme_combo = ctk.CTkComboBox(
            appearance_frame,
            values=["Light", "Dark", "System"],
            variable=theme_var,
            command=lambda value: ctk.set_appearance_mode(value.lower()))
        theme_combo.grid(row=0, column=1, padx=(0, 20), pady=(15, 10), sticky="e")

        font_family_label = ctk.CTkLabel(
            appearance_frame,
            text="Font Family",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        font_family_label.grid(row=1, column=0, padx=(20, 10), pady=(0, 10), sticky="w")

        font_family_var = ctk.StringVar(value="Segoe UI")
        font_family_combo = ctk.CTkComboBox(
            appearance_frame,
            values=["Segoe UI", "Consolas", "Courier", "Monaco"],
            variable=font_family_var,
            width=150)
        font_family_combo.grid(row=1, column=1, padx=(0, 20), pady=(0, 10), sticky="e")

        accent_label = ctk.CTkLabel(
            appearance_frame,
            text="Accent Color",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        accent_label.grid(row=2, column=0, padx=(20, 10), pady=(0, 10), sticky="w")

        accent_var = ctk.StringVar(value="Blue")
        accent_combo = ctk.CTkComboBox(
            appearance_frame,
            values=["Blue", "Green", "Dark Blue"],
            variable=accent_var,
            command=lambda value: ctk.set_default_color_theme(value.lower().replace(" ", "_")))
        accent_combo.grid(row=2, column=1, padx=(0, 20), pady=(0, 10), sticky="e")

        # Section 3: Editor
        editor_label = ctk.CTkLabel(
            scrollable_frame,
            text="Editor",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        editor_label.grid(row=4, column=0, padx=0, pady=(0, 15), sticky='w')

        editor_frame = ctk.CTkFrame(
            scrollable_frame,
            corner_radius=8)
        editor_frame.grid(row=5, column=0, padx=0, pady=(0, 20), sticky='ew')
        editor_frame.grid_columnconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(1, weight=0)

        # Tab Size
        tab_size_label = ctk.CTkLabel(
            editor_frame,
            text="Tab Size",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        tab_size_label.grid(row=1, column=0, padx=(20, 10), pady=(10, 10), sticky="w")

        tab_size_number = ctk.CTkLabel(
            editor_frame,
            text="4",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        tab_size_number.grid(row=1, column=1, padx=(0, 30), pady=(10, 10), sticky="e")

        def on_tab_slider_change(value):
            size = int(float(value))
            tab_size_number.configure(text=str(size))

        tab_size_slider = ctk.CTkSlider(
            editor_frame,
            from_=2,
            to=8,
            number_of_steps=6,
            command=on_tab_slider_change,
            width=270)
        tab_size_slider.set(4)
        tab_size_slider.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        on_tab_slider_change(tab_size_slider.get())

        # Use Spaces Instead of Tabs
        spaces_label = ctk.CTkLabel(
            editor_frame,
            text="Use Spaces Instead of Tabs",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        spaces_label.grid(row=3, column=0, padx=(20, 10), pady=(0, 10), sticky="w")

        spaces_switch = ctk.CTkSwitch(
            editor_frame,
            text="")
        spaces_switch.grid(row=3, column=1, padx=(0, 20), pady=(0, 10), sticky="e")

        # Auto-Save
        auto_save_label = ctk.CTkLabel(
            editor_frame,
            text="Auto-Save (every 10s)",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        auto_save_label.grid(row=5, column=0, padx=(20, 10), pady=(0, 15), sticky="w")

        auto_save_switch = ctk.CTkSwitch(
            editor_frame,
            text="")
        auto_save_switch.grid(row=5, column=1, padx=(0, 20), pady=(0, 15), sticky="e")

        # Section 4: Files and Workspaces
        files_label = ctk.CTkLabel(
            scrollable_frame,
            text="Files and Workspaces",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        files_label.grid(row=6, column=0, padx=0, pady=(0, 15), sticky='w')

        files_frame = ctk.CTkFrame(
            scrollable_frame,
            corner_radius=8)
        files_frame.grid(row=7, column=0, padx=0, pady=(0, 20), sticky='ew')
        files_frame.grid_columnconfigure(0, weight=1)
        files_frame.grid_columnconfigure(1, weight=0)

        # Allow Untrusted Workspaces
        trusted_workspaces_label = ctk.CTkLabel(
            files_frame,
            text="Allow Untrusted Workspaces",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        trusted_workspaces_label.grid(row=0, column=0, sticky='w', padx=(20, 10), pady=15)

        trusted_workspaces_allow = ctk.CTkSwitch(
            files_frame,
            text="",
            button_color="#361E1E",
            button_hover_color="#ffffff")
        trusted_workspaces_allow.grid(row=0, column=1, sticky='e', padx=(0, 20), pady=15)

        # Default Workspace Path (Entry)
        workspace_path_label = ctk.CTkLabel(
            files_frame,
            text="Default Workspace Path",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        workspace_path_label.grid(row=2, column=0, sticky='w', padx=(20, 10), pady=(0, 10))

        workspace_entry = ctk.CTkEntry(
            files_frame,
            placeholder_text=f"C:/Users/{os.getlogin()}/Documents",
            width=300)
        workspace_entry.grid(row=2, column=1, sticky='w', padx=(0, 20), pady=(0, 10))

        settings_and_preferences.mainloop()

if __name__ == '__main__':
    open_settings_window()