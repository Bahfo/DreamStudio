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

import dreamstudio.TabView as TabView

from others.about import *
from dreamstudio.imageload import *
from dreamstudio.menus.home import *
from dreamstudio.menu_builders import *
from dreamstudio.utils.ctk_tabview import *
from dreamstudio.texteditor.config import Config
from dreamstudio.texteditor.config.styles import Style

# OUTER DEFINITIONS FOR MENUS
file_menu = {
    "New File":lambda: print("New File"),
    "New Project":lambda: print("New Project")
}

open_menu = {
    "Open File":lambda: print("Open File"),
    "Open Project":lambda: print("Open Project"),
    "Open File from Template":lambda: print("Open Template")
}

styles_menu = {
    "Light": lambda: ctk.set_appearance_mode("light"),
    "Dark": lambda: ctk.set_appearance_mode("dark"),
}

#######################################
# MAIN WINDOW
#######################################
class App:
    def __init__(self, workspace):
        self.window = ctk.CTk()
        screen_dpi = self.window.winfo_fpixels('1i')
        system = platform.system()
        scaling_factor = 1.0  # default

        if system == "Windows":
            # Tk already respects Windows scaling
            scaling_factor = self.window.tk.call('tk', 'scaling')
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

        self.window.tk.call('tk', 'scaling', scaling_factor)
        print("Scaling factor applied:", scaling_factor)

        self.window.title("Dream Studio")
        self.window.geometry("1000x700")
        self.window.resizable(True, True)

        ##############################
        # DEFINITIONS
        ##############################

        self.workspace = dict[str, ctk.CTkButton]
        self.mode = ctk.get_appearance_mode()
        self.shell_frame = None

        self.text_editor_mode_bool = False

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

        self.config_obj = Config(
            master=self.window,
            darkmode=True if self.mode == 'dark' else False,
            font=("Consolas", 11),
            uifont=("Segoe UI", 11))
        self.app_style = Style(self.window, self.config_obj)

        ###############################
        # MENUS LOOP ITERATION
        ###############################
        self.menubar = CTkMenuBar(self.window, bg_color="#004073", width=20, padx=6, pady=2)

        file_button = self.menubar.add_cascade("File",text_color = "#FFFFFF",font=("Segoe UI",12))
        # File dropdown menu and its options
        file_dropdown = CustomDropdownMenu(widget=file_button, corner_radius=0, font=("Segoe UI",12))
        file_dropdown.add_option("🗒️   New File")
        file_dropdown.add_option("📁   New Project")
        file_dropdown.add_option("📂   Open File")
        file_dropdown.add_option("🗂️   Open Project")
        file_dropdown.add_separator()
        file_dropdown.add_option("💾   Save Current File")
        file_dropdown.add_option("💾   Save Current File As")
        file_dropdown.add_option("💾   Save Project")
        file_dropdown.add_option("💾   Save All")
        file_dropdown.add_separator()
        file_dropdown.add_option("❌   Close Current File")
        file_dropdown.add_option("❌   Close Opened Files")
        file_dropdown.add_option("🚪   Close DreamStudio")
        file_dropdown.add_separator()
        file_dropdown.add_option("⚙️   Settings and Preferences")
        file_dropdown.add_option("⏏️   Exit")


        edit_button = self.menubar.add_cascade("Edit",text_color = "#FFFFFF",font=("Segoe UI",12))
        # Edit dropdown menu and its options
        edit_dropdown = CustomDropdownMenu(widget=edit_button, corner_radius=0, font=("Segoe UI",12))
        edit_dropdown.add_option("✂️   Cut")
        edit_dropdown.add_option("📄   Copy")
        edit_dropdown.add_option("📋   Paste")
        edit_dropdown.add_separator()
        edit_dropdown.add_option("🔍   Find")
        edit_dropdown.add_option("🔁   Replace")
        edit_dropdown.add_separator()
        edit_dropdown.add_option("🗂️   Find in Files")
        edit_dropdown.add_option("📝   Replace in Files")
        edit_dropdown.add_separator()
        edit_dropdown.add_option("💬   Comment Selection")
        edit_dropdown.add_option("🧹   Uncomment Selection")
        edit_dropdown.add_option("⬅️   Emmet Selection Left")
        edit_dropdown.add_option("➡️   Emmet Selection Right")
        edit_dropdown.add_option("🔲   Select All")
        edit_dropdown.add_separator()
        edit_dropdown.add_option("⌨️   Switch to Vim Keybindings")
        edit_dropdown.add_option("🎹   Switch to Dream Keybindings")
        edit_dropdown.add_option("♻️   Reset Keybindings (Normal)")


        view_button = self.menubar.add_cascade("View",text_color = "#FFFFFF",font=("Segoe UI",12))
        # View dropdown menu and its options
        view_dropdown = CustomDropdownMenu(widget=view_button, corner_radius=0, font=("Segoe UI",12))
        view_dropdown.add_option("🎛️   Command Palette")
        view_dropdown.add_option("💻   PromptX Shell")
        view_dropdown.add_option("🖥️   Terminal Window")
        view_dropdown.add_separator()
        view_dropdown.add_option("📁   Solution Explorer")
        view_dropdown.add_option("👥   Team Explorer")
        view_dropdown.add_option("🗄️   Server Explorer")
        view_dropdown.add_option("☁️   Cloud Explorer")
        view_dropdown.add_option("🗃️   SQL Server Object Explorer")
        view_dropdown.add_separator()
        view_dropdown.add_option("🧭   Outline Browser")
        view_dropdown.add_option("📅   Timeline Browser")
        view_dropdown.add_separator()
        view_dropdown.add_option("📛   Errors List")
        view_dropdown.add_option("📟   Output Window")
        view_dropdown.add_option("📌   Tasks List")
        view_dropdown.add_option("🧰   Toolbox")
        view_dropdown.add_option("🔔   Notifications")
        view_dropdown.add_separator()
        view_dropdown.add_option("🐍   Python Environment Manager")
        view_dropdown.add_option("📦   Python Packages Manager")
        view_dropdown.add_option("🧩   JavaScript Environment Manager")
        view_dropdown.add_option("📚   JavaScript Package Manager")
        view_dropdown.add_separator()
        view_dropdown.add_option("🧪   Tests Manager")
        view_dropdown.add_option("📊   Data Tools Manager")
        view_dropdown.add_option("📜   History Manager")


        code_button = self.menubar.add_cascade("Code",text_color = "#FFFFFF",font=("Segoe UI",12))
        # Code dropdown menu and its options
        code_dropdown = CustomDropdownMenu(widget=code_button, corner_radius=0, font=("Segoe UI",12))
        code_dropdown.add_option("🛠️   Refactor Current File")
        code_dropdown.add_option("✏️   Refactor Selected Content")
        code_dropdown.add_option("🧩   Refactor All Files")
        code_dropdown.add_separator()
        code_dropdown.add_option("📂   Go to File")
        code_dropdown.add_option("📍   Go to Line")
        code_dropdown.add_option("📁   List Folder Properties")
        code_dropdown.add_option("📄   List File Properties")
        code_dropdown.add_separator()
        code_dropdown.add_option("⏭️   Next Problem")
        code_dropdown.add_option("⏮️   Previous Problem")
        code_dropdown.add_option("➡️   Next Change")
        code_dropdown.add_option("⬅️   Previous Change")


        run_button = self.menubar.add_cascade("Debug",text_color = "#FFFFFF",font=("Segoe UI",12))
        # Code dropdown menu and its options
        run_dropdown = CustomDropdownMenu(widget=run_button, corner_radius=0, font=("Segoe UI",12))
        run_dropdown.add_option("🐞   Start Debugging")
        run_dropdown.add_option("▮▮   Run without Debugging")
        run_dropdown.add_option("◼️   Stop Debugging")
        run_dropdown.add_option("🔄   Restart Debugging")
        run_dropdown.add_separator()
        run_dropdown.add_option("🌐   Run in Specified Environment")
        run_dropdown.add_option("🖥️   Run in Virtual Machine")
        run_dropdown.add_option("⚙️   Open Configurations")
        run_dropdown.add_option("➕   Add Configurations")
        run_dropdown.add_separator()
        run_dropdown.add_option("⤵️   Step Over")
        run_dropdown.add_option("↘️   Step Into")
        run_dropdown.add_option("↗️   Step Out")
        run_dropdown.add_option("⏵️   Continue")
        run_dropdown.add_separator()
        run_dropdown.add_option("📍   Breakpoints Manager")
        run_dropdown.add_option("🗑️   Remove All Breakpoints")
        run_dropdown.add_option("🔔   Enable All Breakpoints")
        run_dropdown.add_option("🔕   Disable All Breakpoints")


        build_button = self.menubar.add_cascade("Build",text_color = "#FFFFFF",font=("Segoe UI",12))
        # Code dropdown menu and its options
        build_dropdown = CustomDropdownMenu(widget=build_button, corner_radius=0, font=("Segoe UI",12))
        build_dropdown.add_option("🔨   Build Solution")
        build_dropdown.add_option("⚙️   Configure Build Options")
        build_dropdown.add_option("🧹   Clean Options")
        build_dropdown.add_option("📦   Pack Build")
        build_dropdown.add_separator()
        build_dropdown.add_option("🧾   Configure Build Options in JSON")
        build_dropdown.add_option("🕘   Show Build History")


        terminal_button = self.menubar.add_cascade("Terminal",text_color = "#FFFFFF",font=("Segoe UI",12))
        # Code dropdown menu and its options
        terminal_dropdown = CustomDropdownMenu(widget=terminal_button, corner_radius=0, font=("Segoe UI",12))
        terminal_dropdown.add_option("🖥️   Open Terminal")
        terminal_dropdown.add_option("💻   Open PromptX Shell in New Window")
        terminal_dropdown.add_option("📂   Open Files Manager")
        terminal_dropdown.add_separator()
        terminal_dropdown.add_option("🧱   Open CMake Manager")
        terminal_dropdown.add_option("🏃   Run Specific Task")
        terminal_dropdown.add_separator()
        terminal_dropdown.add_option("⚙️   Configure Tasks")


        help_button = self.menubar.add_cascade("Help",text_color = "#FFFFFF",font=("Segoe UI",12))
        # Code dropdown menu and its options
        help_dropdown = CustomDropdownMenu(widget=help_button, corner_radius=0, font=("Segoe UI",12))
        help_dropdown.add_option("👋   Welcome", command=print("Hello"))
        help_dropdown.add_option("📘   Documentation")
        help_dropdown.add_option("⌨️   Keybindings Reference")
        help_dropdown.add_option("📗   Open DShell Documentation", command=lambda: subprocess.Popen(
                                 ["x-terminal-emulator", "-e", "./ddocs/manual"]))
        help_dropdown.add_separator()
        help_dropdown.add_option("📜   View License", command=lambda: License(self.window))
        help_dropdown.add_option("🔄   Check for Updates", command=lambda: CheckForUpdates(self.window))
        help_dropdown.add_separator()
        help_dropdown.add_option("ℹ️   About", command=lambda: AboutWindow(self.window))


        self.menuFrame = ctk.CTkFrame(self.window, height=85, corner_radius=0)
        self.menuFrame.pack(fill="x", side="top")
        self.menuFrame.pack_propagate(False)

        self.exploreBtnOptions = VerticalButton(self.menuFrame, 
                                                image_path=r"icons/system/newvar.png", 
                                                text="File")
        self.exploreBtnOptions.place(x=8, y=3)

        findBtnOptions = VerticalButton(
            self.menuFrame,
            image_path=r"icons/system/folder.png",
            text="Open",
            command=lambda: open_menu_popup(None, self.window, findBtnOptions, open_menu,66,98)
        )
        findBtnOptions.place(x=62, y=3)

        mngBtnOptions = VerticalButton(self.menuFrame, image_path=r"icons/system/save_file.png", 
                                        text="Save")
        mngBtnOptions.place(x=116, y=5)

        trackChangesBtn = HorizontalButton(self.menuFrame, image_path=r"icons/system/database.png",
                                          text="Track Changes")
        trackChangesBtn.place(x=170, y=5)

        compareBtn = HorizontalButton(self.menuFrame, image_path=r"icons/system/feedback.png",
                                      text="Compare Files")
        compareBtn.place(x=170, y=38)

        verticalSep1 = CTkFrame(self.menuFrame, width=2, height=78, corner_radius=0, 
                               fg_color=["#C4C4C4","#414141"])
        verticalSep1.place(x=288, y=3)

        RunCode = VerticalButton(self.menuFrame, image_path=r"icons/system/start.png", 
                                   text="Run\nFile")
        RunCode.place(x=296, y=5)

        cutBtn = HorizontalButton(self.menuFrame, image_path=r"icons/system/bug.png",
                                  text="Debug Files")
        cutBtn.place(x=350, y=5)

        copyBtn = HorizontalButton(self.menuFrame, image_path=r"icons/system/version.png",
                                   text="Configure")
        copyBtn.place(x=350, y=38)

        verticalSep2 = CTkFrame(self.menuFrame, width=2, height=78, corner_radius=0, 
                               fg_color=["#C4C4C4","#414141"])
        verticalSep2.place(x=476, y=3)

        stylesBtn = VerticalButton(self.menuFrame,
            image_path=r"icons/system/container.png", 
            text="Styles",
            command=lambda: open_menu_popup(None, self.window,stylesBtn,styles_menu,484,98))
        stylesBtn.place(x=484, y=5)

        addonsBtn = VerticalButton(self.menuFrame, image_path=r"icons/system/console.png", 
                                   text="Add\nOns")
        addonsBtn.place(x=542, y=5)


        ##############################
        # STATUS BAR
        ##############################

        self.status_bar = ctk.CTkFrame(self.window, height=24, corner_radius=0, fg_color="#004073")
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        self.warnings_label1 = ctk.CTkLabel(
            self.status_bar, text="", text_color="#D5D5D5", image=self.warning, height=8)
        self.warnings_label1.pack(padx=(15, 2), side="left", pady=(2, 2))

        self.warnings_label2 = ctk.CTkLabel(
            self.status_bar,
            text="0",
            text_color="#D5D5D5",
            font=("Segoe UI", 12),
            width=8,
            height=8)
        self.warnings_label2.pack(padx=(0, 2), side="left", pady=(2, 2))

        self.problems_label1 = ctk.CTkLabel(
            self.status_bar, text="", text_color="#D5D5D5", image=self.problem, height=8)
        self.problems_label1.pack(padx=(15, 2), side="left", pady=(2, 2))

        self.problems_label2 = ctk.CTkLabel(
            self.status_bar,
            text="0",
            text_color="#D5D5D5",
            font=("Segoe UI", 12),
            width=8,
            height=8)
        self.problems_label2.pack(padx=(0, 2), side="left", pady=(2, 2))

        self.line_and_pos = ctk.CTkLabel(
            self.status_bar,
            text_color="#D5D5D5",
            text="Ln: 1, Col: 1",
            font=("Segoe UI", 12))
        self.line_and_pos.pack(padx=(10, 0), side="left")

        self.Version_button = ctk.CTkLabel(
            self.status_bar,
            text_color="#D5D5D5",
            text="V0.0.1 BETA",
            font=("Segoe UI", 11),
            corner_radius=0)
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
            command=self.open_shell)

        self.terminal_open_button.pack(padx=(7, 7), side="right", pady=(2, 2))

        self.status_button = ctk.CTkLabel(
            self.status_bar,
            text_color="#D5D5D5",
            text="Ready",
            font=("Segoe UI", 11),
            width=15,
            height=8,
            corner_radius=0,
            fg_color=self.status_bar.cget("fg_color"))
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
            command=lambda: open_current_file(self.status_button, current_session_editors_open,
                                              self.tabSwitch, self.editor_initial_font,
                                              self.text_editor_mode_bool))
        self.open_button.pack(pady=5)
        ToolTip(self.open_button, "Opens a file")

        self.search_button = ctk.CTkButton(
            self.services_bar,
            text="",
            image=self.search_photo,
            width=36,
            height=36,
            corner_radius=5,
            fg_color=self.services_bar.cget("fg_color"))
        self.search_button.pack(pady=5)
        ToolTip(
            self.search_button, "Searches inside the file for a specific key")

        self.save_button = ctk.CTkButton(
            self.services_bar,
            text="",
            image=self.save_photo,
            width=36,
            height=36,
            corner_radius=5,
            fg_color=self.services_bar.cget("fg_color"))
        self.save_button.pack(pady=5)
        ToolTip(self.save_button, "Saves the current loaded workspace file")

        self.user_button = ctk.CTkButton(
            self.services_bar,
            text="",
            image=self.user_photo,
            width=36,
            height=36,
            corner_radius=5,
            fg_color=self.services_bar.cget("fg_color"))
        self.user_button.pack(pady=5, side="bottom")
        ToolTip(self.user_button, "Show user's account")

        self.settings_button = ctk.CTkButton(
            self.services_bar,
            text="",
            image=self.settings_photo,
            width=36,
            height=36,
            corner_radius=5,
            fg_color=self.services_bar.cget("fg_color"))
        self.settings_button.pack(pady=5, side="bottom")
        ToolTip(self.settings_button, "Show IDE settings and preferences")

        ##############################
        # LEFT SIDEBAR FRAME
        ##############################
        self.sidebar = TabView.TabView(master=self.window, border_color=["#C8C8C8", "#444444"])
        self.sidebar.mainFrame.pack(side="left", fill="y")

        ##############################
        # MAIN EDITOR AREA
        ##############################
        self.editor_frame = ctk.CTkFrame(self.window, corner_radius=0)
        self.editor_frame.pack(fill="both", expand=True)

        # --- FRAMES ---
        self.upper_frame = ctk.CTkFrame(self.editor_frame, corner_radius=0)
        self.upper_frame.pack(fill="both", expand = True)

        self.middle_frame = ctk.CTkFrame(self.editor_frame, corner_radius=0)
        self.middle_frame.place_forget()


        # --- Editor ---
        # The editor widget has a texteditor with autocompletion and syntax highlight.
        # It also has an image viewer to view images.
        # It can also show diff windows for comparing two files together side by side.
        
        self.tabSwitch = CTkTabview(self.upper_frame,
                                        corner_radius=0,
                                        border_width=0,
                                        anchor="w",
                                        text_color=["#1E1E1E","#FFFFFF"],
                                        fg_color=["#F5F5F5","#454545"],
                                        segmented_button_fg_color=["#F5F5F5","#1F1F1F"],
                                        segmented_button_selected_color=["#FFFFFF","#1F1F1F"],
                                        segmented_button_selected_hover_color=["#FFFFFF","#1F1F1F"],
                                        segmented_button_unselected_color=["#F5F5F5","#454545"])
        self.tabSwitch.pack(expand=0.9, fill='both')
        self.tabSwitch._segmented_button.configure(font = self.seg_font)

        self.tabSwitch.newtab_btn.configure(command=self.on_add_tab_click)

        self.tabSwitch.add("    Welcome Page    ")
        welcome_tab = self.tabSwitch.tab("    Welcome Page    ")

        welcomeTabElements = GettingStartedTab(welcome_tab)

        #################################################################################################
        # BINDINGS
        #################################################################################################
        self.window.bind("<Control-t>", self.open_terminal)
        self.window.bind("<Control-m>", self.open_shell)

    def _rename_tab_in_texteditor_tabs(self, old_name, new_name):
        if old_name not in self.tabSwitch._tab_dict:
            messagebox.showerror("Error in Tabs Construction",
                                 message="Tab is not found",
                                 default="ok")
            return
        
        self.tabSwitch._tab_dict[new_name] = self.tabSwitch._tab_dict.pop(old_name)
        values = self.tabSwitch._segmented_button.cget("values")
        new_values = [new_name if v == old_name else v for v in values]
        self.tabSwitch._segmented_button.configure(values = new_values)

        self.tabSwitch.set(new_name)

    def on_add_tab_click(self):
        add_new_text_tab(self.tabSwitch, self.editor_initial_font, self.text_editor_mode_bool)

    def on_rename_tab_click(self, new_name):
        current_tab = self.tabSwitch.get()
        self._rename_tab_in_texteditor_tabs(current_tab, new_name)

    def customDropDownFrameChanger(self, frame_to_show):
        for f in [self.plots2d, self.plots3d, self.scientific]:
            f.place_forget()
        frame_to_show.place(x=2, y=2)

    def open_terminal(self, event=None):
        subprocess.Popen("start cmd", shell=True)

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

    def open_shell(self):
        import dreamstudio.command_window as command_window

        if self.shell_frame is None:
            self.upper_frame.place(relx=0, rely=0, relwidth=1, relheight=0.70)
            self.middle_frame.place(relx=0, rely=0.70, relwidth=1, relheight=0.30)

            self.shell_frame = command_window.PromptXShell(main_app=self.middle_frame, status_button=self.status_button)
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

    @lru_cache(maxsize=None)
    def run(self):
        self.window.mainloop()
        self.window.update_idletasks()

news1 = """A new era with B# has started!
Get to be of the first developers to try B#: A modern 
established, strongly-typed, and compiled programming 
language. Think of what you can build and try with its 
standard, but huge ecosystem. Available inside 
DreamStudio."""

news2 = """Get started with a strong ecosystem for your 
Python applications.
Python, and its ecosystem, are all built-in DreamStudio. 
Not only that, but with visual  support (Visual Python) 
for UI related applications.  Drag and drop the elements 
using  Visual-Dream Engine support inside DreamStudio.
"""

news3 = """The cloud, and databases are available.
DreamStudio comes with strong support for databases and 
cloud applications through its  rich and huge ecosystem."""

class GettingStartedTab:
    def __init__(self, welcome_tab):
        welcomeTabFrame = ctk.CTkFrame(welcome_tab, fg_color=["#FFFFFF","#1F1F1F"], corner_radius=0, border_width=0)
        welcomeTabFrame.pack(fill="both", expand=True)

        welcomeTabLabel = ctk.CTkLabel(welcomeTabFrame, text="Get Started With", font=("Microsoft YaHei UI",22),
                                       text_color=["#004073","#97C0FF"], fg_color=["#FFFFFF","#1F1F1F"],
                                       anchor="w", justify="left")
        welcomeTabLabel.place(x = 20, y = 15)

        welcomeTabLabel2 = ctk.CTkLabel(welcomeTabFrame, text="DreamStudio", font=("Microsoft YaHei UI",46),
                                       text_color=["#004073","#97C0FF"], fg_color=["#FFFFFF","#1F1F1F"],
                                       anchor="w", justify="left")
        welcomeTabLabel2.place(x = 20, y = 50)

        versionLabel = ctk.CTkLabel(welcomeTabFrame, text="version 1.0 - 0.0.1 BETA", font=("Microsoft YaHei UI",14),
                                       text_color=["#004073","#97C0FF"], fg_color=["#FFFFFF","#1F1F1F"],
                                       anchor="w", justify="left")
        versionLabel.place(x = 320, y = 80)

        whats_new_label = ctk.CTkLabel(welcomeTabFrame, font=("Microsoft YaHei UI",16),
                                       text_color=["#730047","#FF97E2"], fg_color=["#FFFFFF","#1F1F1F"],
                                       text="Discover Stronger Tools to Build Your Next Dream App", 
                                       anchor="w", justify="left")
        whats_new_label.place(x = 60, y = 150)

        welcomeTabLabel3 = ctk.CTkLabel(welcomeTabFrame, text="Take a tour in DreamStudio to help you get started",
                                        font=("Microsoft YaHei UI",13), text_color=["#000000","#FFFFFF"], 
                                        fg_color=["#FFFFFF","#1F1F1F"], anchor="w", justify="left")
        welcomeTabLabel3.place(x = 20, y = 250)

        welcomeTabLabel4 = LinkLabel(welcomeTabFrame, text="Start My Tour!", corner_radius=0, font=("Segoe UI",12),
                                     width=80, height=18)
        welcomeTabLabel4.place(x = 340, y = 255)

        welcomeTabLabel5 = ctk.CTkLabel(welcomeTabFrame, text="Or read the full documentation for further information",
                                        font=("Microsoft YaHei UI",13), text_color=["#000000","#FFFFFF"], 
                                        fg_color=["#FFFFFF","#1F1F1F"], anchor="w", justify="left")
        welcomeTabLabel5.place(x = 20, y = 275)

        welcomeTabLabel6 = LinkLabel(welcomeTabFrame, text="Read the Documentation", corner_radius=0,
                                     font=("Segoe UI",12), width=136, height=18)
        welcomeTabLabel6.place(x = 362, y = 280)

        ########## SOME RANDOM BUTTONS TO HELP TOURING ##########
        copyright_label = ctk.CTkLabel(welcomeTabFrame, font=("Microsoft YaHei UI",10),
                                       text_color=["#000000","#FFFFFF"], fg_color=["#FFFFFF","#1F1F1F"],
                                       text="Copyright 2026 © DreamStudio - All Rights Reserved",
                                       anchor="w", justify="left")
        copyright_label.place(x = 20, y = 600)

        ########## THE OTHER RIGHT-SIDE ###########
        label1_right = ctk.CTkLabel(welcomeTabFrame, font=("Microsoft YaHei UI",16),
                                    text_color=["#000000","#FFFFFF"], fg_color=["#FFFFFF","#1F1F1F"],
                                    text="Start", anchor="w", justify="left")
        label1_right.place(x = 720, y = 15)
        
        option1 = LinkLabel(welcomeTabFrame, text="Start a New Project", corner_radius=0, font=("Segoe UI",12),
                                     width=106, height=20)
        option1.place(x = 720, y = 50)

        option2 = LinkLabel(welcomeTabFrame, text="Open a Recent Project", corner_radius=0, font=("Segoe UI",12),
                                     width=125, height=20)
        option2.place(x = 720, y = 70)

        label2_right = ctk.CTkLabel(welcomeTabFrame, font=("Microsoft YaHei UI",16),
                                    text_color=["#000000","#FFFFFF"], fg_color=["#FFFFFF","#1F1F1F"],
                                    text="What's New?", anchor="w", justify="left")
        label2_right.place(x = 720, y = 120)

        label3_right = ctk.CTkLabel(welcomeTabFrame, font=("Microsoft YaHei UI",11), width=80,
                                    text_color=["#000000","#FFFFFF"], fg_color=["#FFFFFF","#1F1F1F"],
                                    text=news1, anchor="w", justify="left")
        label3_right.place(x = 720, y = 150)

        label4_right = ctk.CTkLabel(welcomeTabFrame, font=("Microsoft YaHei UI",11), width=80,
                                    text_color=["#000000","#FFFFFF"], fg_color=["#FFFFFF","#1F1F1F"],
                                    text=news2, anchor="w", justify="left")
        label4_right.place(x = 720, y = 260)

        label5_right = ctk.CTkLabel(welcomeTabFrame, font=("Microsoft YaHei UI",11), width=80,
                                    text_color=["#000000","#FFFFFF"], fg_color=["#FFFFFF","#1F1F1F"],
                                    text=news3, anchor="w", justify="left")
        label5_right.place(x = 720, y = 370)
        