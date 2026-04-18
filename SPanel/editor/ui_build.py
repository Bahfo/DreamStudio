# COPYRIGHT 2026 DREAMSTUDIO IDE ... EX-TECHNOLOGIES
# WRITTEN BY BAHAA NOFAL
# CODE IS LICENSED UNDER THE CLOSED LICENSE OF DREAMSTUDIO

import os
import sys
import json
import platform
import subprocess
import customtkinter as ctk

from functools import lru_cache
from tkinter import PhotoImage
from CTkMenuBar import CTkMenuBar, CustomDropdownMenu
from customtkinter import set_widget_scaling, set_window_scaling

from connection.about import *
from editor.imageload import *
from editor.rename_util import *
from editor.menu_builders import *
from editor.utils.verticalButton import VerticalButton
import spanel.command_window as command_window

# OUTER DEFINITIONS FOR MENUS
file_menu = {
    "New File": lambda: print("New File"),
    "New Project": lambda: print("New Project"),
}

open_menu = {
    "Open File": lambda: print("Open File"),
    "Open Project": lambda: print("Open Project"),
    "Open File from Template": lambda: print("Open Template"),
}


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


#######################################
# MAIN WINDOW
#######################################
class App:
    def __init__(self, workspace, path):
        self.window = ctk.CTk()
        screen_dpi = self.window.winfo_fpixels("1i")
        system = platform.system()
        scaling_factor = 1.0  # default

        self.window.attributes("-zoomed", True)
        self.path = path

        if system == "Windows":
            # Tk already respects Windows scaling
            scaling_factor = self.window.tk.call("tk", "scaling")
            self.window.iconbitmap(resource_path(r"assets/logos/ds.ico"))
            self.editor_initial_font = ("Consolas", 13)
        elif system == "Linux":
            # Linux: apply a reasonable factor to match Windows
            scaling_factor = 1.25
            set_window_scaling(scaling_factor)
            set_widget_scaling(scaling_factor)
            icon = PhotoImage(file="assets/logos/dreamStudio_icon.png")
            self.window.iconphoto(True, icon)
            self.editor_initial_font = ("Jetbrains Mono", 10)
        elif system == "Darwin":
            # macOS Retina displays usually need 2.0 scaling
            scaling_factor = 2.0
            set_window_scaling(scaling_factor)
            set_widget_scaling(scaling_factor)

        self.window.tk.call("tk", "scaling", scaling_factor)

        self.window.title("Dream Studio")
        self.window.geometry("1000x700")
        self.window.resizable(True, True)

        ##############################
        # DEFINITIONS
        ##############################

        # CLEANUP ON CLOSE
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.workspace = dict[str, ctk.CTkButton]
        self.workspace_container = {
            "path": None,
            "name": "No Project",
            "files": [],
            "is_git": False,
        }
        self.mode = ctk.get_appearance_mode()
        self.shell_frame = None

        if self.mode == "Light":
            self.text_editor_mode_bool = False
        else:
            self.text_editor_mode_bool = True

        # Segmented Buttons Sepcific Font
        self.seg_font = ctk.CTkFont(family="inter", size=12, weight="normal")

        self.font_size_var = ctk.IntVar(value=14)
        self.code_font_var = ctk.StringVar(value="Consolas")

        for attr, path in icon_paths.items():
            setattr(self, attr, AppIcons.padded_icon(path))

        for attr, (path, size) in ctk_icons.items():
            setattr(self, attr, load_ctk_icon(path, size))

        self.styles_menu = {
            "Light": lambda: self._on_theme_toggle("light"),
            "Dark": lambda: self._on_theme_toggle("dark"),
        }

        ###############################
        # MENUS
        ###############################
        self.menubar = CTkMenuBar(
            self.window, bg_color="#004073", width=30, padx=6, pady=2
        )

        file_button = self.menubar.add_cascade(
            "New",
            text_color="#FFFFFF",
            font=("inter", 12),
        )
        # File dropdown menu and its options
        new_dropdown = CustomDropdownMenu(
            widget=file_button,
            corner_radius=10,
            font=("inter", 12),
            width=250,
        )
        new_dropdown.add_option("Server")
        new_dropdown.add_option("Connection")
        new_dropdown.add_option("Open Saved Connection")
        new_dropdown.add_separator()
        new_dropdown.add_option("Save Current Session")
        new_dropdown.add_option("Save Current Commands History")
        new_dropdown.add_separator()
        new_dropdown.add_option("Close Current Connection")
        new_dropdown.add_separator()
        new_dropdown.add_option("Settings and Preferences")
        new_dropdown.add_option("Exit")

        view_button = self.menubar.add_cascade(
            "Connect",
            text_color="#FFFFFF",
            font=("inter", 12),
        )
        connect_dropdown = CustomDropdownMenu(
            widget=view_button,
            corner_radius=10,
            font=("inter", 12),
            width=250,
            padx=10,
        )
        connect_dropdown.add_option("Connect")
        connect_dropdown.add_option("Disconnect")
        connect_dropdown.add_option("Reconnect")

        code_button = self.menubar.add_cascade(
            "Commands",
            text_color="#FFFFFF",
            font=("inter", 12),
        )
        code_dropdown = CustomDropdownMenu(
            widget=code_button,
            corner_radius=10,
            font=("inter", 12),
            width=250,
            padx=10,
        )
        code_dropdown.add_option("Run Command")
        code_dropdown.add_option("Commands History")
        code_dropdown.add_option("Clear Output")
        code_dropdown.add_separator()
        code_dropdown.add_option("Search Commands")
        code_dropdown.add_option("View all Commands")

        help_button = self.menubar.add_cascade(
            "Help",
            text_color="#FFFFFF",
            font=("inter", 12),
        )
        help_dropdown = CustomDropdownMenu(
            widget=help_button,
            corner_radius=10,
            font=("inter", 12),
            width=250,
            padx=10,
        )
        help_dropdown.add_option("Welcome", command=lambda: print("Hello"))
        help_dropdown.add_option("Documentation")
        help_dropdown.add_option("Keybindings Reference")
        help_dropdown.add_separator()
        help_dropdown.add_option("View License", command=lambda: License(self.window))
        help_dropdown.add_option("About", command=lambda: AboutWindow(self.window))

        self.menuFrame = ctk.CTkFrame(self.window, height=85, corner_radius=0)
        self.menuFrame.pack(fill="x", side="top")
        self.menuFrame.pack_propagate(False)

        self.exploreBtnOptions = VerticalButton(
            self.menuFrame, image_path=explr_btn, text="File"
        )
        self.exploreBtnOptions.place(x=8, y=3)

        findBtnOptions = VerticalButton(
            self.menuFrame, image_path=find_btn_img, text="Open"
        )
        findBtnOptions.place(x=62, y=3)

        saveBtn = VerticalButton(
            self.menuFrame,
            image_path=save_btn_img,
            text="Save",
            size=(20, 20),
        )
        saveBtn.place(x=116, y=5)

        ##############################
        # STATUS BAR
        ##############################

        self.status_bar = ctk.CTkFrame(
            self.window, height=24, corner_radius=0, fg_color="#004073"
        )
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        self.Version_button = ctk.CTkLabel(
            self.status_bar,
            text_color="#D5D5D5",
            text="V0.0.1 BETA",
            font=("inter", 11),
            corner_radius=0,
        )
        self.Version_button.pack(padx=(7, 15), side="right", pady=(2, 2))

        self.terminal_open_button = ctk.CTkButton(
            self.status_bar,
            text_color="#D5D5D5",
            text="SPanel Logs",
            font=("inter", 11),
            width=25,
            fg_color=self.status_bar.cget("fg_color"),
            height=8,
            corner_radius=0,
            command=self.open_shell,
        )

        self.terminal_open_button.pack(padx=(7, 7), side="right", pady=(2, 2))

        self.status_button = ctk.CTkLabel(
            self.status_bar,
            text_color="#D5D5D5",
            text="Ready",
            font=("inter", 11),
            width=15,
            height=8,
            corner_radius=0,
            fg_color=self.status_bar.cget("fg_color"),
        )
        self.status_button.pack(padx=(7, 7), side="right", pady=(2, 2))

        ##############################
        # SERVICES LEFTMOST BAR
        ##############################
        self.services_bar = ctk.CTkFrame(
            self.window,
            width=50,
            corner_radius=0,
            fg_color=["#FFFFFF", "#1B1B1B"],
        )
        self.services_bar.pack_propagate(False)
        self.services_bar.pack(side="left", fill="y")

        self.open_button = ctk.CTkButton(
            self.services_bar,
            text="",
            image=self.open_photo,
            width=36,
            height=36,
            corner_radius=5,
            fg_color=self.services_bar.cget("fg_color"),
        )
        self.open_button.pack(pady=5)

        self.search_button = ctk.CTkButton(
            self.services_bar,
            text="",
            image=self.search_photo,
            width=36,
            height=36,
            corner_radius=5,
            fg_color=self.services_bar.cget("fg_color"),
        )
        self.search_button.pack(pady=5)

        self.user_button = ctk.CTkButton(
            self.services_bar,
            text="",
            image=self.user_photo,
            width=36,
            height=36,
            corner_radius=5,
            fg_color=self.services_bar.cget("fg_color"),
        )
        self.user_button.pack(pady=5, side="bottom")

        self.settings_button = ctk.CTkButton(
            self.services_bar,
            text="",
            image=self.settings_photo,
            width=36,
            height=36,
            corner_radius=5,
            fg_color=self.services_bar.cget("fg_color"),
        )
        self.settings_button.pack(pady=5, side="bottom")

        ##############################
        # MAIN EDITOR AREA
        ##############################
        self.editor_frame = ctk.CTkFrame(self.window, corner_radius=0)
        self.editor_frame.pack(fill="both", expand=True)

        self.upper_frame = ctk.CTkFrame(self.editor_frame, corner_radius=0)
        self.upper_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.commands_window = command_window.SPanel(
            directory=self.path,
            main_app=self.upper_frame,
            status_button=self.status_button,
        )
        self.commands_window.place()

        self.middle_frame = ctk.CTkFrame(self.editor_frame, corner_radius=0)
        self.middle_frame.place_forget()

        ##############################
        # BINDINGS
        ##############################
        self.window.bind("<Control-t>", self.open_terminal)
        self.window.bind("<Control-m>", self.open_shell)

    ############### FUNCTIONS ###############
    def _check_for_theme(self):
        return ctk.get_appearance_mode()

    def _on_theme_toggle(self, type):
        ctk.set_appearance_mode(type)
        mode = self._check_for_theme()

    def load_theme(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    theme = config.get("theme")
                    if theme in ["Light", "Dark"]:
                        return theme
            except json.JSONDecodeError:
                pass
        return "Dark"

    #### TERMINAL LOGIC ####

    def open_terminal(self, event=None):
        if platform.system() == "Windows":
            subprocess.Popen("start cmd", shell=True)
        elif platform.system() == "Linux":
            subprocess.Popen(["gnome-terminal"], shell=True)

    def open_shell(self, event=None):
        if not hasattr(self, "shell_frame") or self.shell_frame is None:
            self.shell_frame = ctk.CTkFrame(self.middle_frame)
            self.shell_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        is_opening = not self.middle_frame.winfo_ismapped()

        if is_opening:
            self.middle_frame.place(relx=0, rely=1.0, relwidth=1, relheight=0.30)
            self.animate_shell(current_rely=1.0, target_rely=0.70, opening=True)
        else:
            self.animate_shell(current_rely=0.70, target_rely=1.0, opening=False)

    def animate_shell(self, current_rely, target_rely, opening):
        step = 0.05  # Animation speed

        if opening:
            if current_rely > target_rely:
                current_rely -= step
                self.upper_frame.place(relheight=current_rely)
                self.middle_frame.place(rely=current_rely)
                self.upper_frame.after(
                    10, lambda: self.animate_shell(current_rely, target_rely, True)
                )
            else:
                self.upper_frame.place(relheight=0.70)
                self.middle_frame.place(rely=0.70)
                self.shell_frame.focus_set()
        else:
            if current_rely < target_rely:
                current_rely += step
                self.upper_frame.place(relheight=current_rely)
                self.middle_frame.place(rely=current_rely)
                self.upper_frame.after(
                    10, lambda: self.animate_shell(current_rely, target_rely, False)
                )
            else:
                self.middle_frame.place_forget()
                self.upper_frame.place(relheight=1.0)

    #### RUN LOGIC ####

    @lru_cache(maxsize=None)
    def run(self):
        self.window.mainloop()
        self.window.update_idletasks()

    #### CLEANUP LOGIC ####

    def on_close(self):
        self._cleanup()
        import threading
        import time
        import os

        def delayed_force_exit():
            time.sleep(0.5)
            os._exit(0)

        t = threading.Thread(target=delayed_force_exit, daemon=True)
        t.start()

    def _cleanup(self):
        if hasattr(self, "tabSwitch") and self.tabSwitch:
            for tab_name in list(self.tabSwitch._tab_dict.keys()):
                self.tabSwitch.delete(tab_name)

        if hasattr(self, "shell_frame") and self.shell_frame:
            try:
                self.shell_frame.destroy()
            except Exception:
                pass

        self.window.quit()
