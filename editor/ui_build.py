# COPYRIGHT 2026 DREAMSTUDIO IDE ... EX-TECHNOLOGIES
# WRITTEN BY BAHAA NOFAL
# CODE IS LICENSED UNDER THE CLOSED LICENSE OF DREAMSTUDIO

import os
import json
import platform
import subprocess
import customtkinter as ctk

from functools import lru_cache
from tkinter import messagebox, PhotoImage
from CTkMenuBar import CTkMenuBar, CustomDropdownMenu
from customtkinter import set_widget_scaling, set_window_scaling

import editor.TabView as TabView

from others.about import *
from editor.imageload import *
from editor.menus.home import *
from editor.rename_util import *
from editor.menu_builders import *
from editor.utils.ctk_tabview import *
from editor.texteditor.config import Config
from editor.texteditor.config.styles import Style

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


#######################################
# MAIN WINDOW
#######################################
class App:
    def __init__(self, workspace):
        self.window = ctk.CTk()
        screen_dpi = self.window.winfo_fpixels("1i")
        system = platform.system()
        scaling_factor = 1.0  # default

        if system == "Windows":
            # Tk already respects Windows scaling
            scaling_factor = self.window.tk.call("tk", "scaling")
            self.window.iconbitmap(r"icons/logos/ds.ico")
            self.editor_initial_font = ("Consolas", 13)
        elif system == "Linux":
            # Linux Mint: apply a reasonable factor to match Windows
            scaling_factor = 1.25
            set_window_scaling(scaling_factor)
            set_widget_scaling(scaling_factor)
            icon = PhotoImage(file="icons/logos/dreamStudio_icon.png")
            self.window.iconphoto(True, icon)
            self.editor_initial_font = ("Liberation Mono", 10)
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

        self.workspace = dict[str, ctk.CTkButton]
        self.mode = ctk.get_appearance_mode()
        self.shell_frame = None

        if self.mode == "Light":
            self.text_editor_mode_bool = False
        else:
            self.text_editor_mode_bool = True

        # Segmented Buttons Sepcific Font
        self.seg_font = ctk.CTkFont(family="Segoe UI", size=12, weight="normal")

        self.font_size_var = ctk.IntVar(value=14)
        self.code_font_var = ctk.StringVar(value="Consolas")

        for attr, path in icon_paths.items():
            setattr(self, attr, AppIcons.padded_icon(path))

        for attr, (path, size) in ctk_icons.items():
            setattr(self, attr, load_ctk_icon(path, size))

        for attr, (path, size) in arrow_icons.items():
            setattr(self, attr, load_ctk_icon(path, size, dark_path=path))

        self.styles_menu = {
            "Light": lambda: self._on_theme_toggle("light"),
            "Dark": lambda: self._on_theme_toggle("dark"),
        }

        self.config_obj = Config(
            master=self.window,
            darkmode=True if self.mode == "dark" else False,
            font=("Consolas", 11),
            uifont=("Segoe UI", 11),
        )
        self.app_style = Style(self.window, self.config_obj)

        ###############################
        # MENUS LOOP ITERATION
        ###############################
        self.menubar = CTkMenuBar(
            self.window, bg_color="#004073", width=20, padx=6, pady=2
        )

        file_button = self.menubar.add_cascade(
            "File", text_color="#FFFFFF", font=("Segoe UI", 12)
        )
        # File dropdown menu and its options
        file_dropdown = CustomDropdownMenu(
            widget=file_button, corner_radius=0, font=("Segoe UI", 12)
        )
        file_dropdown.add_option("New File")
        file_dropdown.add_option("New Project")
        file_dropdown.add_option("Open File")
        file_dropdown.add_option("Open Project")
        file_dropdown.add_separator()
        file_dropdown.add_option("Save Current File")
        file_dropdown.add_option("Save Current File As")
        file_dropdown.add_option("Save Project")
        file_dropdown.add_option("Save All")
        file_dropdown.add_separator()
        file_dropdown.add_option("Close Current File")
        file_dropdown.add_option("Close Opened Files")
        file_dropdown.add_option("Close DreamStudio")
        file_dropdown.add_separator()
        file_dropdown.add_option("Settings and Preferences")
        file_dropdown.add_option("Exit")

        edit_button = self.menubar.add_cascade(
            "Edit", text_color="#FFFFFF", font=("Segoe UI", 12)
        )
        edit_dropdown = CustomDropdownMenu(
            widget=edit_button, corner_radius=0, font=("Segoe UI", 12)
        )
        edit_dropdown.add_option("Cut")
        edit_dropdown.add_option("Copy")
        edit_dropdown.add_option("Paste")
        edit_dropdown.add_separator()
        edit_dropdown.add_option("Find")
        edit_dropdown.add_option("Replace")
        edit_dropdown.add_separator()
        edit_dropdown.add_option("Find in Files")
        edit_dropdown.add_option("Replace in Files")
        edit_dropdown.add_separator()
        edit_dropdown.add_option("Comment Selection")
        edit_dropdown.add_option("Uncomment Selection")
        edit_dropdown.add_option("Select All")

        view_button = self.menubar.add_cascade(
            "View", text_color="#FFFFFF", font=("Segoe UI", 12)
        )
        view_dropdown = CustomDropdownMenu(
            widget=view_button, corner_radius=0, font=("Segoe UI", 12)
        )
        view_dropdown.add_option("Command Palette")
        view_dropdown.add_option("PromptX Shell")
        view_dropdown.add_option("Terminal Window")
        view_dropdown.add_option("Open Files Manager")
        view_dropdown.add_separator()
        view_dropdown.add_option("Errors List")
        view_dropdown.add_option("Output Window")
        view_dropdown.add_option("Tasks List")
        view_dropdown.add_option("Notifications")
        view_dropdown.add_separator()
        view_dropdown.add_option("Python Environment Manager")
        view_dropdown.add_option("Python Packages Manager")
        view_dropdown.add_separator()
        view_dropdown.add_option("Tests Manager")
        view_dropdown.add_option("History Manager")

        code_button = self.menubar.add_cascade(
            "Code", text_color="#FFFFFF", font=("Segoe UI", 12)
        )
        code_dropdown = CustomDropdownMenu(
            widget=code_button, corner_radius=0, font=("Segoe UI", 12)
        )
        code_dropdown.add_option("Refactor Current File")
        code_dropdown.add_option("Refactor Selected Content")
        code_dropdown.add_option("Refactor All Files")
        code_dropdown.add_separator()
        code_dropdown.add_option("Go to File")
        code_dropdown.add_option("Go to Line")
        code_dropdown.add_option("List Folder Properties")
        code_dropdown.add_option("List File Properties")
        code_dropdown.add_separator()
        code_dropdown.add_option("Next Problem")
        code_dropdown.add_option("Previous Problem")

        run_button = self.menubar.add_cascade(
            "Debug", text_color="#FFFFFF", font=("Segoe UI", 12)
        )
        run_dropdown = CustomDropdownMenu(
            widget=run_button, corner_radius=0, font=("Segoe UI", 12)
        )
        run_dropdown.add_option("Start Debugging")
        run_dropdown.add_option("Run without Debugging")
        run_dropdown.add_option("Stop Debugging")
        run_dropdown.add_option("Restart Debugging")
        run_dropdown.add_separator()
        run_dropdown.add_option("Run in Virtual Environment")
        run_dropdown.add_option("Open Configurations")
        run_dropdown.add_option("Add Configurations")
        run_dropdown.add_separator()
        run_dropdown.add_option("Step Over")
        run_dropdown.add_option("Step Into")
        run_dropdown.add_option("Step Out")
        run_dropdown.add_option("Continue")
        run_dropdown.add_separator()
        run_dropdown.add_option("Breakpoints Manager")
        run_dropdown.add_option("Remove All Breakpoints")
        run_dropdown.add_option("Enable All Breakpoints")
        run_dropdown.add_option("Disable All Breakpoints")

        help_button = self.menubar.add_cascade(
            "Help", text_color="#FFFFFF", font=("Segoe UI", 12)
        )
        help_dropdown = CustomDropdownMenu(
            widget=help_button, corner_radius=0, font=("Segoe UI", 12)
        )
        help_dropdown.add_option("Welcome", command=lambda: print("Hello"))
        help_dropdown.add_option("Documentation")
        help_dropdown.add_option("Keybindings Reference")
        help_dropdown.add_option(
            "Open DShell Documentation",
            command=lambda: subprocess.Popen(
                ["x-terminal-emulator", "-e", "./ddocs/manual"]
            ),
        )
        help_dropdown.add_separator()
        help_dropdown.add_option("View License", command=lambda: License(self.window))
        help_dropdown.add_option(
            "Check for Updates", command=lambda: CheckForUpdates(self.window)
        )
        help_dropdown.add_separator()
        help_dropdown.add_option("About", command=lambda: AboutWindow(self.window))

        self.menuFrame = ctk.CTkFrame(self.window, height=85, corner_radius=0)
        self.menuFrame.pack(fill="x", side="top")
        self.menuFrame.pack_propagate(False)

        self.exploreBtnOptions = VerticalButton(
            self.menuFrame, image_path=r"icons/system/newvar.png", text="File"
        )
        self.exploreBtnOptions.place(x=8, y=3)

        findBtnOptions = VerticalButton(
            self.menuFrame,
            image_path=r"icons/system/folder.png",
            text="Open",
            command=lambda: open_menu_popup(
                None, self.window, findBtnOptions, open_menu, 66, 98
            ),
        )
        findBtnOptions.place(x=62, y=3)

        mngBtnOptions = VerticalButton(
            self.menuFrame, image_path=r"icons/system/save_file.png", text="Save"
        )
        mngBtnOptions.place(x=116, y=5)

        trackChangesBtn = HorizontalButton(
            self.menuFrame,
            image_path=r"icons/system/database.png",
            text="Track Changes",
        )
        trackChangesBtn.place(x=170, y=5)

        compareBtn = HorizontalButton(
            self.menuFrame,
            image_path=r"icons/system/feedback.png",
            text="Compare Files",
        )
        compareBtn.place(x=170, y=38)

        verticalSep1 = CTkFrame(
            self.menuFrame,
            width=2,
            height=78,
            corner_radius=0,
            fg_color=["#C4C4C4", "#414141"],
        )
        verticalSep1.place(x=288, y=3)

        RunCode = VerticalButton(
            self.menuFrame, image_path=r"icons/system/start.png", text="Run\nFile"
        )
        RunCode.place(x=296, y=5)

        debugBtn = HorizontalButton(
            self.menuFrame, image_path=r"icons/system/bug.png", text="Debug Files"
        )
        debugBtn.place(x=350, y=5)

        configBtn = HorizontalButton(
            self.menuFrame, image_path=r"icons/system/manager.png", text="Configure"
        )
        configBtn.place(x=350, y=38)

        verticalSep2 = CTkFrame(
            self.menuFrame,
            width=2,
            height=78,
            corner_radius=0,
            fg_color=["#C4C4C4", "#414141"],
        )
        verticalSep2.place(x=476, y=3)

        stylesBtn = VerticalButton(
            self.menuFrame,
            image_path=r"icons/system/container.png",
            text="Styles",
            command=lambda: open_menu_popup(
                None, self.window, stylesBtn, self.styles_menu, 484, 98
            ),
        )
        stylesBtn.place(x=484, y=5)

        addonsBtn = VerticalButton(
            self.menuFrame, image_path=r"icons/system/console.png", text="Add\nOns"
        )
        addonsBtn.place(x=542, y=5)

        ##############################
        # STATUS BAR
        ##############################

        self.status_bar = ctk.CTkFrame(
            self.window, height=24, corner_radius=0, fg_color="#004073"
        )
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        self.warnings_label1 = ctk.CTkLabel(
            self.status_bar, text="", text_color="#D5D5D5", image=self.warning, height=8
        )
        self.warnings_label1.pack(padx=(15, 2), side="left", pady=(2, 2))

        self.warnings_label2 = ctk.CTkLabel(
            self.status_bar,
            text="0",
            text_color="#D5D5D5",
            font=("Segoe UI", 12),
            width=8,
            height=8,
        )
        self.warnings_label2.pack(padx=(0, 2), side="left", pady=(2, 2))

        self.problems_label1 = ctk.CTkLabel(
            self.status_bar, text="", text_color="#D5D5D5", image=self.problem, height=8
        )
        self.problems_label1.pack(padx=(15, 2), side="left", pady=(2, 2))

        self.problems_label2 = ctk.CTkLabel(
            self.status_bar,
            text="0",
            text_color="#D5D5D5",
            font=("Segoe UI", 12),
            width=8,
            height=8,
        )
        self.problems_label2.pack(padx=(0, 2), side="left", pady=(2, 2))

        self.line_and_pos = ctk.CTkLabel(
            self.status_bar,
            text_color="#D5D5D5",
            text="Ln: 1, Col: 1",
            font=("Segoe UI", 12),
        )
        self.line_and_pos.pack(padx=(10, 0), side="left")

        self.notifications_button = ctk.CTkButton(
            self.status_bar,
            fg_color="#004073",
            text="🔔",
            width=30,
            corner_radius=0,
            command=lambda: open_notifications(
                root_window=self.window,
                title="Update Available",
                content="Version 1.0.1 BETA is ready to download",
            ),
        )
        self.notifications_button.pack(padx=(7, 7), side="right")

        self.Version_button = ctk.CTkLabel(
            self.status_bar,
            text_color="#D5D5D5",
            text="V0.0.1 BETA",
            font=("Segoe UI", 11),
            corner_radius=0,
        )
        self.Version_button.pack(padx=(7, 15), side="right", pady=(2, 2))

        self.terminal_open_button = ctk.CTkButton(
            self.status_bar,
            text_color="#D5D5D5",
            text="PromptX-Shell",
            font=("Segoe UI", 11),
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
            font=("Segoe UI", 11),
            width=15,
            height=8,
            corner_radius=0,
            fg_color=self.status_bar.cget("fg_color"),
        )
        self.status_button.pack(padx=(7, 7), side="right", pady=(2, 2))

        ##############################
        # SERVICES LEFTMOST BAR
        ##############################

        self.services_bar = ctk.CTkFrame(self.window, width=50, corner_radius=-1)
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
            command=lambda: open_current_file(
                self.status_button,
                current_session_editors_open,
                self.tabSwitch,
                self.editor_initial_font,
                self.text_editor_mode_bool,
            ),
        )
        self.open_button.pack(pady=5)
        ToolTip(self.open_button, "Opens a file")

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
        ToolTip(self.search_button, "Searches inside the file for a specific key")

        self.save_button = ctk.CTkButton(
            self.services_bar,
            text="",
            image=self.save_photo,
            width=36,
            height=36,
            corner_radius=5,
            fg_color=self.services_bar.cget("fg_color"),
        )
        self.save_button.pack(pady=5)
        ToolTip(self.save_button, "Saves the current loaded workspace file")

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
        ToolTip(self.user_button, "Show user's account")

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
        ToolTip(self.settings_button, "Show IDE settings and preferences")

        ##############################
        # LEFT SIDEBAR FRAME
        ##############################
        self.sidebar = TabView.TabView(
            master=self.window, border_color=["#C8C8C8", "#444444"]
        )
        self.sidebar.mainFrame.pack(side="left", fill="y")

        ##############################
        # MAIN EDITOR AREA
        ##############################
        self.editor_frame = ctk.CTkFrame(self.window, corner_radius=0)
        self.editor_frame.pack(fill="both", expand=True)

        # --- FRAMES ---
        self.upper_frame = ctk.CTkFrame(self.editor_frame, corner_radius=0)
        self.upper_frame.pack(fill="both", expand=True)

        self.middle_frame = ctk.CTkFrame(self.editor_frame, corner_radius=0)
        self.middle_frame.place_forget()

        # --- Editor ---
        # The editor widget has a texteditor with autocompletion and syntax highlight.
        # It also has an image viewer to view images.
        # It can also show diff windows for comparing two files together side by side.

        self.tabSwitch = CTkTabview(
            self.upper_frame,
            corner_radius=0,
            border_width=0,
            anchor="w",
            text_color=["#1E1E1E", "#FFFFFF"],
            fg_color=["#F5F5F5", "#454545"],
            segmented_button_fg_color=["#F5F5F5", "#1F1F1F"],
            segmented_button_selected_color=["#FFFFFF", "#1F1F1F"],
            segmented_button_selected_hover_color=["#FFFFFF", "#1F1F1F"],
            segmented_button_unselected_color=["#F5F5F5", "#454545"],
        )
        self.tabSwitch.pack(expand=True, fill="both")
        self.tabSwitch._segmented_button.configure(font=self.seg_font)

        self.tabSwitch.newtab_btn.configure(command=self.on_add_tab_click)
        self.tabSwitch.close_btn.configure(command=self._close_tab)

        for btn in self.tabSwitch._segmented_button._buttons_dict.values():
            btn.bind(
                "<Double-Button-1>",
                lambda event: self.on_rename_tab_click("New Name 1"),
            )

        # Set up treeview file opening callback
        self.sidebar.treeView.file_click_callback = (
            lambda file_path: open_file_from_tree(
                file_path,
                self.status_button,
                self.tabSwitch,
                self.editor_initial_font,
                self.text_editor_mode_bool,
            )
        )

        #################################################################################################
        # BINDINGS
        #################################################################################################
        self.window.bind("<Control-t>", self.open_terminal)
        self.window.bind("<Control-m>", self.open_shell)

    ############### FUNCTIONS ###############

    def _check_for_theme(self):
        return ctk.get_appearance_mode()

    def _on_theme_toggle(self, type):
        ctk.set_appearance_mode(type)
        mode = self._check_for_theme()
        update_all_editors_theme(mode)

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

    #### TABSWITCH LOGIC ####

    def _bind_tab_rename_events(self):
        """Bind double-click rename to all tab buttons"""
        for btn in self.tabSwitch._segmented_button._buttons_dict.values():
            btn.bind("<Double-Button-1>", self.on_rename_tab_click)

    def on_add_tab_click(self):
        add_new_text_tab(
            self.tabSwitch, self.editor_initial_font, self.text_editor_mode_bool
        )
        self._bind_tab_rename_events()

    def _close_tab(self):
        on_close_tab_click(self.tabSwitch)

    def on_rename_tab_click(self, event=None):
        """Open rename dialog for the currently selected tab

        If user closes the dialog without entering a name, the original tab name is preserved.
        """
        current_tab = self.tabSwitch.get()

        if not current_tab:
            messagebox.showwarning("No Tab", "No tab is currently selected")
            return

        def on_confirm(new_name):
            """Called when user confirms rename"""
            try:
                self.tabSwitch.rename(current_tab, new_name)
                # Update the current tab to the new name to sync internal state
                self.tabSwitch.set(new_name)
            except ValueError as e:
                messagebox.showerror("Rename Error", str(e))

        def on_cancel():
            """Called when user cancels or closes the dialog - original name is preserved"""
            pass

        RenameDialog(
            self.window,
            current_name=current_tab,
            on_confirm=on_confirm,
            on_cancel=on_cancel,
        )

    #### TERMINAL LOGIC ####

    def open_terminal(self, event=None):
        if platform.system() == "Windows":
            subprocess.Popen("start cmd", shell=True)
        elif platform.system() == "Linux":
            subprocess.Popen(["gnome-terminal"], shell=True)

    def open_shell(self, event=None):
        import editor.command_window as command_window

        if self.shell_frame is None:
            self.upper_frame.place(relx=0, rely=0, relwidth=1, relheight=0.70)
            self.middle_frame.place(relx=0, rely=0.70, relwidth=1, relheight=0.30)

            self.shell_frame = command_window.PromptXShell(
                main_app=self.middle_frame, status_button=self.status_button
            )
            self.shell_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        else:
            if self.shell_frame.winfo_ismapped():
                self.shell_frame.place_forget()
                self.middle_frame.place_forget()
                self.upper_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            else:
                self.upper_frame.place(relx=0, rely=0, relwidth=1, relheight=0.70)
                self.middle_frame.place(relx=0, rely=0.70, relwidth=1, relheight=0.30)
                self.shell_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    #### RUN LOGIC ####

    @lru_cache(maxsize=None)
    def run(self):
        self.window.mainloop()
        self.window.update_idletasks()
