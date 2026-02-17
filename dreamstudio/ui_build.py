# COPYRIGHT 2026 DREAMSTUDIO IDE ... EX-TECHNOLOGIES
# WRITTEN BY BAHAA NOFAL 

# CODE IS LICENSED UNDER THE CLOSED LICENSE OF DREAMSTUDIO

import os
import json
import subprocess
import customtkinter as ctk

from tkinter import filedialog, messagebox
from functools import lru_cache

from dreamstudio.imageload import *
from dreamstudio.utils.ctk_tabview import *
from dreamstudio.menu_builders import *
from dreamstudio.texteditor import Editor, Languages

import dreamstudio.TabView as TabView

#######################################
# MAIN WINDOW
#######################################

ctk.set_appearance_mode("system")

class App:
    def __init__(self, workspace):
        self.window = ctk.CTk()
        self.window.title("Dream Studio")
        self.window.geometry("1000x700")
        self.window.iconbitmap(r"icons/dreamstudio_icon.ico")
        self.window.resizable(True, True)

        ##############################
        # DEFINITIONS
        ##############################

        self.workspace = dict[str, ctk.CTkButton]
        self.current_session_editors_open = {}
        self.mode = ctk.get_appearance_mode()
        self.shell_frame = None
        self.tab_count = 0

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

        ###############################
        # MENUS LOOP ITERATION
        ###############################
        self.menubar = ctk.CTkFrame(self.window, height=110, corner_radius=0)
        self.menubar.pack(fill="x", side="top")
        self.menubar.pack_propagate(False)

        # Creating Holding Frames for the Menus
        self.topFrame = ctk.CTkFrame(
            self.menubar, height=18, fg_color="#004073", corner_radius=0)
        self.topFrame.pack(fill="x", side="top")

        # Menus Services
        self.downFrame = ctk.CTkFrame(self.menubar, height=100, corner_radius=0)
        self.downFrame.pack(fill="x", side="top")

        ###############################
        # MENUS FRAMES
        ###############################
        self.homeFrame = ctk.CTkFrame(self.downFrame, corner_radius=0, height=122,
                                      border_color="#5e5e5e", border_width=1,
                                      fg_color=["#D2D2D2","#1E1E1E"])
        
        self.toolsFrame = ctk.CTkFrame(self.downFrame, corner_radius=0, height=122,
                                      border_color="#5e5e5e", border_width=1,
                                      fg_color=["#D2D2D2","#1E1E1E"])

        self.debugFrame = ctk.CTkFrame(self.downFrame, corner_radius=0, height=122,
                                      border_color="#5e5e5e", border_width=1,
                                      fg_color=["#D2D2D2","#1E1E1E"])

        self.terminalFrame = ctk.CTkFrame(self.downFrame, corner_radius=0, height=122,
                                      border_color="#5e5e5e", border_width=1,
                                      fg_color=["#D2D2D2","#1E1E1E"])

        self.helpFrame = ctk.CTkFrame(self.downFrame, corner_radius=0, height=122,
                                      border_color="#5e5e5e", border_width=1,
                                      fg_color=["#D2D2D2","#1E1E1E"])

        BUTTON_CONFIG = {
            "height": 24,
            "fg_color": "#004073",
            "corner_radius": 0,
            "width": 80,
            "font": ("Segoe UI", 12)}

        menu_items = [
            ("HOME", self.homeFrame, "homeBtn"),
            ("TOOLS", self.toolsFrame, "toolsBtn"),
            ("DEBUG", self.debugFrame, "debugBtn"),
            ("TERMINAL", self.terminalFrame, "terminalBtn"),
            ("HELP", self.helpFrame, "helpBtn")]

        # Looping to create and pack standard buttons
        for text, frame, attr_name in menu_items:
            btn = ctk.CTkButton(
                self.topFrame,
                text=text,
                command=lambda f=frame, a=attr_name: self._show_menu_tab(f, getattr(self, a)),
                **BUTTON_CONFIG
            )
            btn.pack(side="left", anchor="w", padx=(8, 0))
            setattr(self, attr_name, btn)

        # ACCOUNT button
        self.accountBtn = ctk.CTkButton(
            self.topFrame,
            text="ACCOUNT",
            image=self.downArrow,
            width=100,
            height=20,
            fg_color="#004073",
            corner_radius=0,
            font=("Segoe UI", 12))
        self.accountBtn.pack(side="right", anchor="e", padx=(8, 8))

        ##############################
        # MENUS CONSTRUCTOR
        ##############################
        
        for _, name, _ in menu_items:
            name.pack(fill = "both", side = "top")
            name.pack_propagate(False)

        self.parent_color = self.homeFrame.cget("fg_color")

        home_toolbar = HomeToolbarBuilder(self.homeFrame, self.parent_color, self)
        tools_toolbar = ToolsBarBuilder(self.toolsFrame, self.parent_color, self)
        debug_toolbar = DebugBuilder(self.parent_color, self.debugFrame)
        terminal_toolbar = TerminalBuilder(self.terminalFrame, self.parent_color)
        help_toolbar = HelpBuilder(self.helpFrame, self.parent_color)

        self.allTabs = [
            self.homeFrame,
            self.toolsFrame,
            self.debugFrame,
            self.terminalFrame,
            self.helpFrame]
        self._show_menu_tab(self.homeFrame, self.homeBtn)

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
            command=self.open_current_file)
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
                                        fg_color=["#C8C8C8","#454545"],
                                        segmented_button_fg_color=["#FFFFFF","#1F1F1F"],
                                        segmented_button_selected_color=["#FFFFFF","#1F1F1F"],
                                        segmented_button_selected_hover_color=["#FFFFFF","#1F1F1F"],
                                        segmented_button_unselected_color=["#C8C8C8","#454545"])
        self.tabSwitch.pack(expand=0.9, fill='both')
        self.tabSwitch._segmented_button.configure(font = self.seg_font)
        self._add_new_text_tab()

        self.tabSwitch.newtab_btn.configure(command=self._add_new_text_tab)

        #################################################################################################
        # BINDINGS
        #################################################################################################
        self.window.bind("<Control-t>", self.open_terminal)
        self.window.bind("<Control-m>", self.open_shell)

    def _show_menu_tab(self, frame_to_show, active_button):
        for frame in self.allTabs:
            frame.pack_forget()

        if hasattr(frame_to_show, "initialize"):
            frame_to_show.initialize()

        frame_to_show.pack(fill="both", side="top")
        frame_to_show.pack_propagate(False)

        tabButtons = [
            self.homeBtn,
            self.toolsBtn,
            self.debugBtn,
            self.terminalBtn,
            self.helpBtn]

        for btn in tabButtons:
            btn.configure(fg_color="#004073")

    def _add_new_text_tab(self):
        if self.tab_count >= 10:
            messagebox.showerror("Tabs Construction Error", "Cannot create more than 10 tabs")
            return None
        
        self.tab_count += 1
        tab_name = f"    Untitled-{self.tab_count}    "
        self.tabSwitch.add(tab_name)

        new_editor = Editor(
            self.tabSwitch.tab(tab_name),
            language=Languages.C,
            font=("Consolas", 13),
            showpath=True,
            darkmode=(self.mode != "light"),
            uifont=("Segoe UI", 11))
        new_editor.pack(fill='both', expand=True)
        
        self.current_session_editors_open[tab_name] = new_editor
        
        self.tabSwitch.set(tab_name)
        return tab_name

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
        self._add_new_text_tab()

    def on_rename_tab_click(self, new_name):
        current_tab = self.tabSwitch.get()
        self._rename_tab_in_texteditor_tabs(current_tab, new_name)

    def customDropDownFrameChanger(self, frame_to_show):
        for f in [self.plots2d, self.plots3d, self.scientific]:
            f.place_forget()
        frame_to_show.place(x=2, y=2)

    def open_terminal(self, event=None):
        subprocess.Popen("start cmd", shell=True)

    def open_current_file(self):
        current_file = filedialog.askopenfilename(title="Select an existing file")
        if not current_file:
            return

        if self.status_button:
            self.status_button.configure(text="Opening file...")

        try:
            with open(current_file, "r", encoding="utf-8") as f:
                content = f.read()

            tab_name = self._add_new_text_tab()
            
            if tab_name:
                target_editor = self.current_session_editors_open.get(tab_name)

                if target_editor:
                    target_editor.content.delete("1.0", "end")
                    target_editor.content.insert("1.0", content)
                    
                    if self.status_button:
                        self.status_button.configure(text=f"Opened: {current_file}")
                        
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")
            if self.status_button:
                self.status_button.configure(text="Operation Failed")

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
