"""
Handles first layer: Graphical User Interface Layer (GUI Layer)
\nDreamStudio is now only supported for some languages:
\nLua, Python, and JavaScript
"""

license_text = """
Copyright 2026 EX Technologies
An Integrated Development Environment (IDE) designed to be light, professional, and user-friendly.

Proprietary Freeware License:
Softdream is free to download and use, but the user is restricted to the following keypoints:

    - The software is free to use (gratis).
    - Users cannot modify the software.
    - Users cannot sell or distribute it.
    - You may not modify, reverse engineer, or create derivative works.
    - You may not redistribute, sell, or sublicense this software.

For more info, download the full documentation.
"""
import widgets.menus.home as home
import widgets.universal_widgets as uniwidgets
from intellisense.highlighter import PythonHighlighter as pylight
from intellisense.dreamintellisense import PythonIntellisense as pysense
from tkinter import ttk, messagebox
from tkinter import filedialog
from PIL import Image, ImageTk
from pathlib import Path
import customtkinter as ctk
import tkinter as tk
import re
import os
import json
import ctypes
import pyperclip
import subprocess
import consoles.file_manager as file_manager
import consoles.command_window as command_window

################################################################################################
# MAIN WINDOW
################################################################################################

class App:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Dream Studio")
        self.window.iconbitmap(r"")
        self.window.geometry("1000x700")
        self.window.resizable(True, True)

        self.CONFIG_FILE = r"themes\config\config.json"
        ctk.set_default_color_theme(r"themes\metal.json")
        self.mode = self.load_theme()
        ctk.set_appearance_mode(self.mode)

        ######################################################
        # HIGH DPI AWARENESS ENABLED
        ######################################################
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

#################################################################################################
# DEFINITIONS
#################################################################################################

        self.version = "0.0.1 BETA"
        self.workspace = {"path": None}

        self.REFRESH_INTERVAL_MINUTES = 2
        self.REFRESH_INTERVAL_MS = self.REFRESH_INTERVAL_MINUTES * 60 * 1000  # milliseconds

        self.font_size_var = ctk.IntVar(value=14)
        self.code_font_var = ctk.StringVar(value="Consolas")
        self.mode = ctk.get_appearance_mode()

        def create_padded_icon(ico_path, icon_size=(16, 16), padding=8):
            try:
                icon_img = Image.open(ico_path).convert("RGBA").resize(icon_size)
                img = Image.new('RGBA', (icon_size[0] + padding, icon_size[1]), (0, 0, 0, 0))
                img.paste(icon_img, (0, 0), icon_img)
                return ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Warning: Could not load icon {ico_path}: {e}")
                img = Image.new('RGBA', (icon_size[0] + padding, icon_size[1]), (0, 0, 0, 0))
                return ImageTk.PhotoImage(img)

        self.folder_img = create_padded_icon(r"icons\types\folder.ico")
        self.file_img = create_padded_icon(r"icons\types\file.ico")
        self.txt_img = create_padded_icon(r"icons\types\txt.ico")
        self.c_files = create_padded_icon(r"icons\types\c.ico")
        self.json_files = create_padded_icon(r"icons\types\json.ico")
        self.docx_files = create_padded_icon(r"icons\types\docx.ico")
        self.ppt_files = create_padded_icon(r"icons\types\ppt.ico")
        self.pptx_files = create_padded_icon(r"icons\types\pptx.ico")
        self.apk_files = create_padded_icon(r"icons\types\apk.ico")
        self.cs_files = create_padded_icon(r"icons\types\csharp.ico")
        self.html_files = create_padded_icon(r"icons\types\html.ico")
        self.js_files = create_padded_icon(r"icons\types\javascript.ico")
        self.java_files = create_padded_icon(r"icons\types\java.ico")
        self.swift_files = create_padded_icon(r"icons\types\swift.ico")
        self.rb_files = create_padded_icon(r"icons\types\ruby.ico")
        self.ts_files = create_padded_icon(r"icons\types\typescript.ico")
        self.jsx_files = create_padded_icon(r"icons\types\javascript.ico")
        self.py_files = create_padded_icon(r"icons\types\python.ico")
        self.h_files = create_padded_icon(r"icons\types\c.ico")

        self.load_ico = create_padded_icon(r"icons\system\load.png")
        self.refresh_ico = create_padded_icon(r"icons\system\refresh.png")
        self.console = create_padded_icon(r"icons\system\console.png")
        self.debug = create_padded_icon(r"icons\system\debug.png")
        self.manage = create_padded_icon(r"icons\system\manager.png")
        self.problem = create_padded_icon(r"icons\system\problem.png")
        self.ver = create_padded_icon(r"icons\system\version.png")
        self.warning = create_padded_icon(r"icons\system\warning.png")

        self.search_photo   = ctk.CTkImage(light_image=Image.open(r"icons\system\search.png"), size=(24, 24))
        self.open_photo     = ctk.CTkImage(light_image=Image.open(r"icons\system\open_folder.png"), size=(24, 24))
        self.settings_photo = ctk.CTkImage(light_image=Image.open(r"icons\system\settings.png"), size=(24, 24))
        self.save_photo     = ctk.CTkImage(light_image=Image.open(r"icons\system\save_file.png"), size=(24,24))
        self.user_photo     = ctk.CTkImage(light_image=Image.open(r"icons\system\user.png"), size=(24,24))
        self.sleeping       = ctk.CTkImage(light_image=Image.open(r"icons\types\sleeping.ico"),size=(80,80))

        self.downArrow = ctk.CTkImage(dark_image=Image.open(r"icons\system\down_arrow.png"), size=(8,8))
        self.upArrow = ctk.CTkImage(dark_image=Image.open(r"icons\system\up_arrow.png"), size=(8,8))
        self.rightArrow = ctk.CTkImage(dark_image=Image.open(r"icons\system\right_arrow.png"), size=(8,8))
        self.stepTo = ctk.CTkImage(dark_image=Image.open(r"icons\system\stepTo.png"), size=(20,20))
        self.stepOut = ctk.CTkImage(dark_image=Image.open(r"icons\system\stepOut.png"), size=(20,20))
        self.stepOver = ctk.CTkImage(dark_image=Image.open(r"icons\system\stepOver.png"), size=(20,20))
        self.runToCursor = ctk.CTkImage(dark_image=Image.open(r"icons\system\runToCursor.png"), size=(20,20))
        self.toggleCursor = ctk.CTkImage(dark_image=Image.open(r"icons\system\toggle.png"), size=(20,20))

        self.icons = {
        "folder": self.folder_img,
        "file": self.file_img,
        ".txt": self.txt_img,
        ".c": self.c_files,
        ".json": self.json_files,
        ".docx": self.docx_files,
        ".ppt": self.ppt_files,
        ".pptx": self.pptx_files,
        ".apk": self.apk_files,
        ".cs": self.cs_files,
        ".html": self.html_files,
        ".js": self.js_files,
        ".java": self.java_files,
        ".swift": self.swift_files,
        ".rb": self.rb_files,
        ".ts": self.ts_files,
        ".jsx": self.jsx_files,
        ".py": self.py_files,
        ".h": self.h_files}

        self.allowed_extensions = {".py", ".txt", ".c", ".cpp", ".json",".docx",".ppt",".pptx",
                                ".apk",".cpp",".cs",".cc",".cxx",".html",".js",".java",
                                ".swift",".rb",".ts",".jsx",".py",".h"}
        
        self.window.bind("<Control-t>",self.open_terminal)
        self.window.bind("<Control-m>",self.open_file_manager)

        ################################################################################################
        # MENUS: Define showing menus, menubar, topframe, downframe, and their buttons
        ################################################################################################

        self.menus = {"DebugInfo": ["Any CPU","x86 Architecture","x64 Architecture","ARM/ARM64"],
                "Kit Manager": ["Manage Kits","Install New Kits","Reload Kits","Deactivate all Kits"]}

        self.menubar = CTkFrameVeryDark(self.window, height=110, corner_radius=0)
        self.menubar.pack(fill="x", side="top")
        self.menubar.pack_propagate(False)

        # Creating Holding Frames for the Menus
        self.topFrame = ctk.CTkFrame(self.menubar,height=18,fg_color="#004073",corner_radius=0)
        self.topFrame.pack(fill='x',side='top')

        # Services Buttons
        self.homeBtn = ctk.CTkButton(self.topFrame,height=24,fg_color="#004073",corner_radius=0,
                                width=80,text="HOME",font=("Segoe UI",12),
                                command=lambda: self.show_tab(self.homeFrame))
        self.homeBtn.pack(side='left',anchor='w',padx=(8,0))

        self.toolsBtn = ctk.CTkButton(self.topFrame,height=24,fg_color="#004073",corner_radius=0,
                                width=80,text="TOOLS",font=("Segoe UI",12),
                                command=lambda: self.show_tab(self.toolsFrame))
        self.toolsBtn.pack(side='left',anchor='w',padx=(8,0))

        self.plotsBtn = ctk.CTkButton(self.topFrame,height=24,fg_color="#004073",corner_radius=0,
                                width=80,text="PLOTS",font=("Seoge UI",12),
                                command=lambda: self.show_tab(self.plotsFrame))
        self.plotsBtn.pack(side='left',anchor='w',padx=(8,0))

        self.debugBtn = ctk.CTkButton(self.topFrame,height=24,fg_color="#004073",corner_radius=0,
                                width=80,text="DEBUG",font=("Seoge UI",12),
                                command=lambda: self.show_tab(self.debugFrame))
        self.debugBtn.pack(side='left',anchor='w',padx=(8,0))

        self.terminalBtn = ctk.CTkButton(self.topFrame,height=24,fg_color="#004073",corner_radius=0,
                                width=80,text="TERMINAL",font=("Segoe UI",12),
                                command=lambda: self.show_tab(self.terminalFrame))
        self.terminalBtn.pack(side='left',anchor='w',padx=(8,0))

        self.helpBtn = ctk.CTkButton(self.topFrame,height=24,fg_color="#004073",corner_radius=0,
                                width=80,text="HELP",font=("Seoge UI",12),
                                command=lambda: self.show_tab(self.helpFrame))
        self.helpBtn.pack(side='left',anchor='w',padx=(8,0))

        self.accountBtn = ctk.CTkButton(self.topFrame,height=20,fg_color="#004073",corner_radius=0,
                                width=100,text="ACCOUNT",font=("Segoe UI",12),
                                image=self.downArrow)
        self.accountBtn.pack(side='right',anchor='e',padx=(8,8))

        # Menus Services
        self.downFrame = ctk.CTkFrame(self.menubar,height=100,corner_radius=0)
        self.downFrame.pack(fill='x',side='top')

        ################################################################################################
        # HOME MENU: Home menu buttons and their functionalities
        ################################################################################################

        self.homeFrame = ctk.CTkFrame(self.downFrame,corner_radius=0,height=122,border_color="#5e5e5e",
                                border_width=1,fg_color="#696969" if self.mode == 'Light' else "#1e1e1e")
        self.homeFrame.pack(fill='both',side='top')
        self.homeFrame.pack_propagate(False)

        self.parent_color = self.homeFrame.cget("fg_color")

        self.newFile = uniwidgets.VerticalButton(
            self.homeFrame,
            image_path=r"icons\system\new_file.png",
            text=" New Tab ",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.newFile.place(x=5,y=5)

        self.newMacro = uniwidgets.VerticalButton(
            self.homeFrame,
            image_path=r"icons\system\new_macro.png",
            text=" New Code",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.newMacro.place(x=75,y=5)

        self.openCode = uniwidgets.VerticalButton(
            self.homeFrame,
            image_path=r"icons\system\open_code.png",
            text="Open Code",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.openCode.place(x=152,y=5)

        self.refreshWorkspace = uniwidgets.HorizontalButton(
            self.homeFrame,
            image_path=r"icons\system\refresh_workspace.png",
            text="Refresh Files",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a"
        )
        self.refreshWorkspace.place(x=230,y=7)

        self.saveAll = uniwidgets.HorizontalButton(
            self.homeFrame,
            image_path=r"icons\system\save_all.png",
            text="Save All Files",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a"
        )
        self.saveAll.place(x=230,y=37)

        self.vertical_sep_1 = ctk.CTkFrame(self.homeFrame,bg_color='transparent',
                                    fg_color="#727272" if self.mode=='Dark' else "#3E3E3E",
                                    width=2,height=75,corner_radius=0)
        self.vertical_sep_1.place(x=340,y=7)

        self.pasteBtn = uniwidgets.VerticalButton(
            self.homeFrame,
            image_path=r"icons\system\paste.png",
            text="Paste Code",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.pasteBtn.place(x=350,y=5)

        self.cutBtn = uniwidgets.HorizontalButton(
            self.homeFrame,
            image_path=r"icons\system\cut.png",
            text=" Cut Codes",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a"
        )
        self.cutBtn.place(x=428,y=7)

        self.copyBtn = uniwidgets.HorizontalButton(
            self.homeFrame,
            image_path=r"icons\system\copy.png",
            text=" Copy Codes",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a"
        )
        self.copyBtn.place(x=428,y=37)

        self.undoBtn = uniwidgets.HorizontalButton(
            self.homeFrame,
            image_path=r"icons\system\undo.png",
            text="Undo Action",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a"
        )
        self.undoBtn.place(x=538,y=7)

        self.redoBtn = uniwidgets.HorizontalButton(
            self.homeFrame,
            image_path=r"icons\system\redo.png",
            text="Redo Action",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a"
        )
        self.redoBtn.place(x=538,y=37)

        self.deleteBtn = uniwidgets.HorizontalButton(
            self.homeFrame,
            image_path=r"icons\system\delete.png",
            text="Delete Codes",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a"
        )
        self.deleteBtn.place(x=648,y=7)

        self.replaceBtn = uniwidgets.HorizontalButton(
            self.homeFrame,
            image_path=r"icons\system\replace.png",
            text="Find/Replace",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a"
        )
        self.replaceBtn.place(x=648,y=37)

        self.vertical_sep_2 = ctk.CTkFrame(self.homeFrame,bg_color='transparent',
                                    fg_color="#727272" if self.mode=='Dark' else "#3E3E3E",
                                    width=2,height=75,corner_radius=0)
        self.vertical_sep_2.place(x=760,y=7)

        self.syntaxBtn = uniwidgets.VerticalButton(
            self.homeFrame,
            image_path=r"icons\system\syntax.png",
            text="Configure \nSyntax",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
            command= self.onOpenSyntax)
        self.syntaxBtn.place(x=770,y=5)


        ################################################################################################
        # Tools MENU: Opens new windows that does a specific utility and their functionalities
        ################################################################################################

        self.toolsFrame = ctk.CTkFrame(self.downFrame,corner_radius=0,height=122,border_color="#5e5e5e",
                                border_width=1,fg_color="#696969" if self.mode == 'Light' else "#1e1e1e")
        self.toolsFrame.pack(fill='both',side='top')
        self.toolsFrame.pack_propagate(False)

        self.explorBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\solution.png",
            text=" Solution\nExplorer",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.explorBtn.place(x=5,y=5)

        self.toolsBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\tools.png",
            text="Open\n ToolBox ",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.toolsBtn.place(x=75,y=5)

        self.managerBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\manager.png",
            text="Workspace\nManager",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.managerBtn.place(x=148,y=5)

        self.propertiesBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\properties.png",
            text="Properties\nWindow",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.propertiesBtn.place(x=228,y=5)

        self.vertical_sep_3 = ctk.CTkFrame(self.toolsFrame,bg_color='transparent',
                                    fg_color="#727272" if self.mode=='Dark' else "#3E3E3E",
                                    width=2,height=75,corner_radius=0)
        self.vertical_sep_3.place(x=304,y=7)

        self.terminalBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\terminal.png",
            text="Open\nTerminal",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.terminalBtn.place(x=314,y=5)

        self.cmdWindowBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\command.png",
            text="Command\nWindow",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.cmdWindowBtn.place(x=382,y=5)

        self.resourcesBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\resources.png",
            text="Manage\nResources",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.resourcesBtn.place(x=457,y=5)

        self.containerBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\container.png",
            text="Container\nWindow",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.containerBtn.place(x=529,y=5)

        self.tasksBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\tasks.png",
            text="Manage\nTasks",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.tasksBtn.place(x=600,y=5)

        self.vertical_sep_4 = ctk.CTkFrame(self.toolsFrame,bg_color='transparent',
                                    fg_color="#727272" if self.mode=='Dark' else "#3E3E3E",
                                    width=2,height=75,corner_radius=0)
        self.vertical_sep_4.place(x=664,y=7)

        self.databaseBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\database.png",
            text="Manage\nDatabases",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.databaseBtn.place(x=674,y=5)

        self.sourcesBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\datasources.png",
            text="Data\nSources",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.sourcesBtn.place(x=748,y=5)

        self.impDataBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\importdata.png",
            text="Import\nData",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.impDataBtn.place(x=806,y=5)

        self.cleanDataBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\cleandata.png",
            text="Clean\nData",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.cleanDataBtn.place(x=863,y=5)

        self.newVarBtn = uniwidgets.HorizontalButton(
            self.toolsFrame,
            image_path=r"icons\system\newvar.png",
            text="New Macro",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.newVarBtn.place(x=914,y=7)
        
        self.openVarBtn = uniwidgets.HorizontalButton(
            self.toolsFrame,
            image_path=r"icons\system\openvar.png",
            text="Open Macro",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.openVarBtn.place(x=914,y=37)

        self.vertical_sep_5 = ctk.CTkFrame(self.toolsFrame,bg_color='transparent',
                                    fg_color="#727272" if self.mode=='Dark' else "#3E3E3E",
                                    width=2,height=75,corner_radius=0)
        self.vertical_sep_5.place(x=1027,y=7)

        self.gitBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\git.png",
            text="Repository\nManager",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.gitBtn.place(x=1037,y=5)

        self.gitChangesBtn = uniwidgets.HorizontalButton(
            self.toolsFrame,
            image_path=r"icons\system\gitchanges.png",
            text="Git Changes",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.gitChangesBtn.place(x=1110,y=7)

        self.githubBtn = uniwidgets.HorizontalButton(
            self.toolsFrame,
            image_path=r"icons\system\github.png",
            text="View Github",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.githubBtn.place(x=1110,y=37)

        self.vertical_sep_6 = ctk.CTkFrame(self.toolsFrame,bg_color='transparent',
                                    fg_color="#727272" if self.mode=='Dark' else "#3E3E3E",
                                    width=2,height=75,corner_radius=0)
        self.vertical_sep_6.place(x=1225,y=7)

        self.sqlBtn = uniwidgets.VerticalButton(
            self.toolsFrame,
            image_path=r"icons\system\sql.png",
            text="SQL\nServices",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.sqlBtn.place(x=1235,y=5)

        self.jsonBtn = uniwidgets.HorizontalButton(
            self.toolsFrame,
            image_path=r"icons\system\json.png",
            text="Open JSON",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.jsonBtn.place(x=1295,y=7)

        self.xamlBtn = uniwidgets.HorizontalButton(
            self.toolsFrame,
            image_path=r"icons\system\xaml.png",
            text="Open XAML",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.xamlBtn.place(x=1295,y=37)

        self.htmlBtn = uniwidgets.HorizontalButton(
            self.toolsFrame,
            image_path=r"icons\system\html.png",
            text="Open HTML",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.htmlBtn.place(x=1405,y=7)

        self.webBtn = uniwidgets.HorizontalButton(
            self.toolsFrame,
            image_path=r"icons\system\web.png",
            text="Manage Web",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.webBtn.place(x=1405,y=37)

        ################################################################################################
        # PLOTS MENU: Shows plots of variables, objects, any selected (if it has plot options)
        ################################################################################################

        self.plotsFrame = ctk.CTkFrame(self.downFrame,corner_radius=0,height=122,border_color="#5e5e5e",
                                border_width=1,fg_color="#696969" if self.mode == 'Light' else "#1e1e1e")
        self.plotsFrame.pack(fill='both',side='top')
        self.plotsFrame.pack_propagate(False)

        self.plotMngBtn = uniwidgets.VerticalButton(
            self.plotsFrame,
            image_path=r"icons\system\graphsettings.png",
            text="Plot\nManager",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.plotMngBtn.place(x=5,y=3)

        self.inspectorBtn = uniwidgets.VerticalButton(
            self.plotsFrame,
            image_path=r"icons\system\inspector.png",
            text="Graph\nInspector",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.inspectorBtn.place(x=70,y=3)

        self.plotThemeBtn = uniwidgets.VerticalButton(
            self.plotsFrame,
            image_path=r"icons\system\theme.png",
            text="Plot\nThemes",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.plotThemeBtn.place(x=137,y=3)

        self.vertical_sep_7 = ctk.CTkFrame(self.plotsFrame,bg_color='transparent',
                                    fg_color="#727272" if self.mode=='Dark' else "#3E3E3E",
                                    width=2,height=75,corner_radius=0)
        self.vertical_sep_7.place(x=199,y=7)

        ########## CUSTOM DROPDOWN MENU ##########
        self.customUtilitiesFrame = ctk.CTkFrame(
            self.plotsFrame,
            width=400,
            height=77,
            fg_color=self.plotsFrame.cget("fg_color"),
            border_color="#5e5e5e" if self.mode == "Dark" else "#D6D6D6",
            border_width=1,
            corner_radius=1)
        self.customUtilitiesFrame.place(x=209,y=5)
        self.customUtilitiesFrame.pack_propagate(False)

        ######### PLOTS 2D #########
        self.plots2d = ctk.CTkFrame(self.customUtilitiesFrame,
                            width=395,
                            height=71,
                            fg_color=self.plotsFrame.cget("fg_color"),
                            corner_radius=0)
        self.customUtilitiesFrame.pack_propagate(False)

        self.graphBtn = uniwidgets.VerticalButton(
            self.plots2d,
            image_path=r"icons\system\graph.png",
            text="GraphBox",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.graphBtn.place(x=5,y=2)

        self.chartBtn = uniwidgets.VerticalButton(
            self.plots2d,
            image_path=r"icons\system\chart.png",
            text="Chart Graph",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.chartBtn.place(x=75,y=2)

        self.chartBtn = uniwidgets.VerticalButton(
            self.plots2d,
            image_path=r"icons\system\bargraph.png",
            text="Bar Graph",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.chartBtn.place(x=157,y=2)

        self.histoBtn = uniwidgets.VerticalButton(
            self.plots2d,
            image_path=r"icons\system\histogram.png",
            text="Histogram",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.histoBtn.place(x=227,y=2)

        ######### PLOTS 3D #########
        self.plots3d = ctk.CTkFrame(self.customUtilitiesFrame,
                            width=395,
                            height=71,
                            fg_color=self.plotsFrame.cget("fg_color"),
                            corner_radius=0)
        self.customUtilitiesFrame.pack_propagate(False)

        self.graph3DBtn = uniwidgets.VerticalButton(
            self.plots3d,
            image_path=r"icons\system\surface.png",
            text="3D Surface",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.graph3DBtn.place(x=5,y=2)

        self.scatterBtn = uniwidgets.VerticalButton(
            self.plots3d,
            image_path=r"icons\system\scatter.png",
            text="3D Scatter",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.scatterBtn.place(x=82,y=2)

        self.wireframeBtn = uniwidgets.VerticalButton(
            self.plots3d,
            image_path=r"icons\system\wireframe.png",
            text="3D Wireframe",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.wireframeBtn.place(x=157,y=2)

        self.contourBtn = uniwidgets.VerticalButton(
            self.plots3d,
            image_path=r"icons\system\contour.png",
            text="3D Contour",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.contourBtn.place(x=247,y=2)

        ######### scientific #########
        self.scientific = ctk.CTkFrame(self.customUtilitiesFrame,
                            width=395,
                            height=71,
                            fg_color=self.plotsFrame.cget("fg_color"),
                            corner_radius=0)
        self.customUtilitiesFrame.pack_propagate(False)

        self.heatmapBtn = uniwidgets.VerticalButton(
            self.scientific,
            image_path=r"icons\system\heatmap.png",
            text="Heatmap",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.heatmapBtn.place(x=5,y=2)

        self.polarBtn = uniwidgets.VerticalButton(
            self.scientific,
            image_path=r"icons\system\polar.png",
            text="Polar Plan",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.polarBtn.place(x=80,y=2)

        self.corrMATBtn = uniwidgets.VerticalButton(
            self.scientific,
            image_path=r"icons\system\corrmat.png",
            text="Corr. Matrix",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.corrMATBtn.place(x=155,y=2)

        ######### MOVEMENT #########
        if self.mode == 'Dark':
            self.text_color="#CDCDCD"
        else:
            self.text_color="#1E1E1E"

        self.upBtn1 = ctk.CTkButton(self.plots2d,text="",image=self.upArrow,width=50,height=20,
                                corner_radius=0,fg_color="#1e1e1e",text_color=self.text_color,
                                state=ctk.DISABLED)
        self.upBtn1.place(x=345,y=2)
        self.downBtn1 = ctk.CTkButton(self.plots2d,text="",image=self.downArrow,width=50,height=20,
                                        text_color=self.text_color,
                                corner_radius=0,hover_color="#001F39",fg_color="#004073",
                                command=lambda:self.customDropDownFrameChanger(self.plots3d))
        self.downBtn1.place(x=345,y=25)
        lab1Show = ctk.CTkLabel(self.plots2d,text="2D PLOTS",font=("Segoe UI",10),fg_color="#004073",
                                corner_radius=0,width=50,height=20,text_color="#CDCDCD")
        lab1Show.place(x=345,y=48)
        self.upBtn2 = ctk.CTkButton(self.plots3d,text="",image=self.upArrow,width=50,height=20,
                                text_color=self.text_color,
                                corner_radius=0,hover_color="#001F39",fg_color="#004073",
                                command=lambda:self.customDropDownFrameChanger(self.plots2d))
        self.upBtn2.place(x=345,y=2)
        self.downBtn2 = ctk.CTkButton(self.plots3d,text="",image=self.downArrow,width=50,height=20,
                                        text_color=self.text_color,
                                corner_radius=0,hover_color="#001F39",fg_color="#004073",
                                command=lambda:self.customDropDownFrameChanger(self.scientific))
        self.downBtn2.place(x=345,y=25)
        self.lab2Show = ctk.CTkLabel(self.plots3d,text="3D PLOTS",font=("Segoe UI",10),fg_color="#004073",
                                corner_radius=0,width=50,height=20,text_color="#CDCDCD")
        self.lab2Show.place(x=345,y=48)
        self.upBtn3 = ctk.CTkButton(self.scientific,text="",image=self.upArrow,width=50,height=20,
                                    text_color=self.text_color,
                                corner_radius=0,hover_color="#001F39",fg_color="#004073",
                                command=lambda:self.customDropDownFrameChanger(self.plots3d))
        self.upBtn3.place(x=345,y=2)
        self.downBtn3 = ctk.CTkButton(self.scientific,text="",image=self.downArrow,width=50,height=20,
                                corner_radius=0,fg_color="#1e1e1e",text_color=self.text_color
                                ,state=ctk.DISABLED)
        self.downBtn3.place(x=345,y=25)
        self.lab3Show = ctk.CTkLabel(self.scientific,text="SCI.",font=("Segoe UI",10),fg_color="#004073",
                                corner_radius=0,width=50,height=20,text_color="#CDCDCD")
        self.lab3Show.place(x=345,y=48)
        self.customDropDownFrameChanger(self.plots2d)

        self.statsOverLayBtn = uniwidgets.HorizontalButton(
            self.plotsFrame,
            image_path=r"icons\system\stats.png",
            text="Stats Overlay",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.statsOverLayBtn.place(x=614,y=7)

        self.trashGraphBtn = uniwidgets.HorizontalButton(
            self.plotsFrame,
            image_path=r"icons\system\trash.png",
            text="Delete Graph",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.trashGraphBtn.place(x=614,y=37)

        ################################################################################################
        # DEBUG MENU: Debugging configuration settings
        ################################################################################################

        self.debugFrame = ctk.CTkFrame(self.downFrame,corner_radius=0,height=122,border_color="#5e5e5e",
                                border_width=1,fg_color="#696969" if self.mode == 'Light' else "#1e1e1e")
        self.debugFrame.pack(fill='both',side='top')
        self.debugFrame.pack_propagate(False)

        self.debuggingBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\bug.png",
            text="Start\nDebugging",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.debuggingBtn.place(x=5,y=3)

        self.runNoBugBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\start.png",
            text="Run without\nDebugging",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.runNoBugBtn.place(x=82,y=5)

        self.attachBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\attach.png",
            text="Attach to\nSome Process",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.attachBtn.place(x=162,y=5)

        self.compileBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\compile.png",
            text="Compile\nCode",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.compileBtn.place(x=253,y=5)

        self.stopBugBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\stop.png",
            text="Stop\nDebugging",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.stopBugBtn.place(x=315,y=5)

        self.restartBugBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\restart.png",
            text="Restart\nDebugging",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.restartBugBtn.place(x=392,y=5)

        self.deatBugBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\deattach.png",
            text="Detach\nDebugger",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.deatBugBtn.place(x=470,y=5)

        self.vertical_sep_8 = ctk.CTkFrame(self.debugFrame,bg_color='transparent',
                                    fg_color="#727272" if self.mode=='Dark' else "#3E3E3E",
                                    width=2,height=75,corner_radius=0)
        self.vertical_sep_8.place(x=543,y=7)

        ######### UPON DEBUGGING TOOLS #########
        self.debuggingToolsFrame = ctk.CTkFrame(self.debugFrame, fg_color=self.debugFrame.cget("fg_color"),
                                        width = 162, height=35, border_color="#5e5e5e",
                                        border_width=1,corner_radius=2)
        self.debuggingToolsFrame.place(x=553,y=7)
        self.stepToBtn = ctk.CTkButton(self.debuggingToolsFrame, text="", image=self.stepTo,width=20,height=20,
                                fg_color=self.debuggingToolsFrame.cget("fg_color"),corner_radius=0)
        self.stepToBtn.place(x=2,y=2)

        self.stepOutBtn = ctk.CTkButton(self.debuggingToolsFrame, text="", image=self.stepOut,width=20,height=20,
                                fg_color=self.debuggingToolsFrame.cget("fg_color"),corner_radius=0)
        self.stepOutBtn.place(x=34,y=2)

        self.stepOverBtn = ctk.CTkButton(self.debuggingToolsFrame, text="", image=self.stepOver,width=20,height=20,
                                fg_color=self.debuggingToolsFrame.cget("fg_color"),corner_radius=0)
        self.stepOverBtn.place(x=66,y=2)

        self.runToCursorBtn = ctk.CTkButton(self.debuggingToolsFrame, text="", image=self.toggleCursor,width=20,height=20,
                                fg_color=self.debuggingToolsFrame.cget("fg_color"),corner_radius=0)
        self.runToCursorBtn.place(x=130,y=2)

        self.runToCursorBtn = ctk.CTkButton(self.debuggingToolsFrame, text="", image=self.runToCursor,width=20,height=20,
                                fg_color=self.debuggingToolsFrame.cget("fg_color"),corner_radius=0)
        self.runToCursorBtn.place(x=98,y=2)

        ######### CPU CONFIGURATION DEBUGGING #########

        self.active_menu = {"menu": None}

        self.cpuInfo = ctk.CTkButton(
            self.debugFrame,
            corner_radius=0,
            width=75,
            height=26,
            image=self.rightArrow,
            text="Show Debugging Platforms",
            text_color="#b5b5b5" if self.mode=='Dark' else "#D1D1D1",
            font=("Segoe UI", 12),
            fg_color=self.debugFrame.cget("fg_color"),
            hover_color="#535353",
            command=self.debugging_menu
        )
        self.cpuInfo.place(x=553, y=47)

        self.watchBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\watch.png",
            text="Watch\nWindow",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.watchBtn.place(x=730,y=5)

        self.performanceBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\cpu.png",
            text="Performance\nOptimization",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.performanceBtn.place(x=790,y=5)

        self.memoryBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\memory.png",
            text="Memory\nProfiler",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.memoryBtn.place(x=875,y=5)

        self.vertical_sep_9 = ctk.CTkFrame(self.debugFrame,bg_color='transparent',
                                    fg_color="#727272" if self.mode=='Dark' else "#3E3E3E",
                                    width=2,height=75,corner_radius=0)
        self.vertical_sep_9.place(x=938,y=7)

        self.verifyBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\verify.png",
            text="Verify Code\nSafety",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.verifyBtn.place(x=948,y=5)

        ################################################################################################
        # TERMINAL MENU
        ################################################################################################

        self.terminalFrame = ctk.CTkFrame(self.downFrame,corner_radius=0,height=122,border_color="#5e5e5e",
                                border_width=1,fg_color="#696969" if self.mode == 'Light' else "#1e1e1e")
        self.terminalFrame.pack(fill='both',side='top')
        self.terminalFrame.pack_propagate(False)

        self.runTaskBtn = uniwidgets.VerticalButton(
            self.terminalFrame,
            image_path=r"icons\system\task.png",
            text="Run Task",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.runTaskBtn.place(x=5,y=5)

        self.buildBtn = uniwidgets.VerticalButton(
            self.terminalFrame,
            image_path=r"icons\system\build.png",
            text="Build Task",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.buildBtn.place(x=75,y=5)

        self.fileMngBtn = uniwidgets.VerticalButton(
            self.terminalFrame,
            image_path=r"icons\system\fileMng.png",
            text="Run File\nManager",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.fileMngBtn.place(x=150,y=5)

        self.dayDreamBtn = uniwidgets.VerticalButton(
            self.terminalFrame,
            image_path=r"icons\system\daydream.png",
            text="DayDream\nTerminal",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.dayDreamBtn.place(x=220,y=5)


        self.helpFrame = ctk.CTkFrame(self.downFrame,corner_radius=0,height=122,border_color="#5e5e5e",
                                border_width=1,fg_color="#696969" if self.mode == 'Light' else "#1e1e1e")
        self.helpFrame.pack(fill='both',side='top')
        self.helpFrame.pack_propagate(False)

        self.docBtn = uniwidgets.VerticalButton(
            self.helpFrame,
            image_path=r"icons\system\documentation.png",
            text="Documentation",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.docBtn.place(x=5,y=5)

        self.feedBtn = uniwidgets.VerticalButton(
            self.helpFrame,
            image_path=r"icons\system\feedback.png",
            text="Feedback",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.feedBtn.place(x=106,y=5)

        self.hBtn = uniwidgets.VerticalButton(
            self.helpFrame,
            image_path=r"icons\system\help.png",
            text="Show Help",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a")
        self.hBtn.place(x=176,y=5)

        self.allTabs = [self.homeFrame, self.toolsFrame, self.plotsFrame, self.debugFrame,
                    self.terminalFrame, self.helpFrame]
        self.show_tab(self.homeFrame)

        #################################################################################################
        # STATUS BAR
        #################################################################################################

        self.status_bar = CTkFrameVeryDark(self.window, height=28, corner_radius=0)
        self.status_bar.pack(fill="x", side="bottom")

        self.warnings_button = ctk.CTkButton(self.status_bar,text="Warnings",font=("Segoe UI",11),width=15,
                                        image=self.warning,
                                        height=8, corner_radius=0,fg_color=self.status_bar.cget("fg_color"))
        self.warnings_button.pack(padx=(2,2),side="left",pady=(2,2))
        uniwidgets.ToolTip(self.warnings_button,"Shows the number of warnings inside the file")

        self.problems_button = ctk.CTkButton(self.status_bar,text="Problems and Issues",font=("Segoe UI",11),
                                        image=self.problem,
                                        width=15,height=8, corner_radius=0,fg_color=self.status_bar.cget("fg_color"))
        self.problems_button.pack(padx=(2,2),side="left",pady=(2,2))
        uniwidgets.ToolTip(self.problems_button,"Shows the number of problems encountered inside the file")

        self.debug_configuration = ctk.CTkButton(self.status_bar,text="Select and Start Debug Configurations",
                                            image=self.debug,
                                            font=("Segoe UI",11),width=15, height=8, corner_radius=0,
                                            fg_color=self.status_bar.cget("fg_color"))
        self.debug_configuration.pack(padx=(2,2),side="left",pady=(2,2))
        uniwidgets.ToolTip(self.debug_configuration,"Shows automatic configuration for the selected language")

        self.Version_button = ctk.CTkButton(self.status_bar,text="Version 0.0.1 BETA",font=("Segoe UI",11),
                                    image=self.ver,
                                        fg_color=self.status_bar.cget("fg_color"),
                                        width=15,height=8, corner_radius=0,
                                        command=self.open_license)
        self.Version_button.pack(padx=(2,2),side="right",pady=(2,2))
        uniwidgets.ToolTip(self.Version_button, f"You are currently running on version {self.version}")

        self.Terminal_button = ctk.CTkButton(self.status_bar,text="Open Terminal",font=("Segoe UI",11),width=15,
                                        image=self.console,
                                        fg_color=self.status_bar.cget("fg_color"),
                                        height=8, corner_radius=0,
                                        command=self.ports_and_terminals_open)
        self.Terminal_button.pack(padx=(2,2),side="right",pady=(2,2))
        uniwidgets.ToolTip(self.Terminal_button, "Opens a new terminal, restricted by the device terminal type")

        self.file_manager_button = ctk.CTkButton(self.status_bar, text="Open File Manager", font=("Segoe UI", 11),
                                            image=self.manage,
                                            width=25, fg_color=self.status_bar.cget("fg_color"),
                                            height=8, corner_radius=0,
                                            command=self.open_command_window)
        self.file_manager_button.pack(padx=(2,2),side="right",pady=(2,2))
        uniwidgets.ToolTip(self.file_manager_button, "Opens file management terminal")

        self.status_button = ctk.CTkButton(self.status_bar,text="Ready", font=("Segoe UI",12), width=15,
                                    height=8, corner_radius=0,
                                    fg_color=self.status_bar.cget("fg_color"))
        self.status_button.pack(padx=(2,2),side="right",pady=(2,2))
        uniwidgets.ToolTip(self.status_button, "Follows the last successful option or command activated")


        #################################################################################################
        # SERVICES LEFTMOST BAR
        #################################################################################################

        self.services_bar = CTkFrameDarker(self.window, width=50, corner_radius=-1)
        self.services_bar.pack_propagate(False)
        self.services_bar.pack(side="left", fill="y")

        self.open_button = ctk.CTkButton(self.services_bar,text="",image=self.open_photo,width=36,height=36,
                                        corner_radius=5,fg_color=self.services_bar.cget("fg_color"),
                                        command= self.open_current_file)
        self.open_button.pack(pady=5)
        uniwidgets.ToolTip(self.open_button, "Opens a file")

        self.search_button = ctk.CTkButton(self.services_bar,text="",image=self.search_photo,width=36,height=36,
                                        corner_radius=5,
                                        fg_color=self.services_bar.cget("fg_color"),
                                        command=self.open_search)
        self.search_button.pack(pady=5)
        uniwidgets.ToolTip(self.search_button,"Searches inside the file for a specific key")

        self.save_button = ctk.CTkButton(self.services_bar,text="",image=self.save_photo,width=36,height=36,
                                    corner_radius=5,
                                    fg_color=self.services_bar.cget("fg_color"),
                                    command=self.save_file)
        self.save_button.pack(pady=5)
        uniwidgets.ToolTip(self.save_button,"Saves the current loaded workspace file")

        self.user_button = ctk.CTkButton(self.services_bar, text="", image=self.user_photo, width = 36, height=36, 
                                corner_radius=5, fg_color=self.services_bar.cget("fg_color"))
        self.user_button.pack(pady=5, side = 'bottom')
        uniwidgets.ToolTip(self.user_button, "Show user's account")

        self.settings_button = ctk.CTkButton(self.services_bar,text="",image=self.settings_photo,width=36,height=36,
                                        corner_radius=5,
                                        fg_color=self.services_bar.cget("fg_color"),
                                        command = self.open_settings)
        self.settings_button.pack(pady=5,side='bottom')
        uniwidgets.ToolTip(self.settings_button, "Show IDE settings and preferences")

        #################################################################################################
        # LEFT SIDEBAR FRAME
        #################################################################################################

        self.sidebar = ctk.CTkFrame(self.window,fg_color="#292929" if self.mode == "Dark" else "#ADADAD",
                                    width=360, corner_radius=0)
        self.sidebar.pack_propagate(False)
        self.sidebar.pack(side="left", fill="y")

        #################################################################################################
        # MAIN EDITOR AREA
        #################################################################################################
        # Divider frame between left sidebar and editor
        self.divider = ctk.CTkFrame(
            self.window,
            fg_color="gray40",
            width=3,
            cursor="sb_h_double_arrow",
            corner_radius=0)
        self.divider.pack(side="left", fill="y")

        # Container frame for tabs + editor
        self.editor_container = ctk.CTkFrame(self.window)
        self.editor_container.pack(side="right", fill="both", expand=True)

        # Editor Frame inside container
        self.editor_frame = CTkFrameVeryDark(self.editor_container)
        self.editor_frame.pack(side="top", fill="both", expand=True)

        # Fonts
        self.editor_font = ctk.CTkFont(family=self.code_font_var.get(), size=self.font_size_var.get())
        self.line_number_font = ctk.CTkFont(family=self.code_font_var.get(), size=self.font_size_var.get() + 2)

        # Background colors
        if self.mode == "Light": 
            self.bg_color_canvas = "#C3C3C3"
            self.number_col = "#232323"
        else:
            self.bg_color_canvas = "#232323"
            self.number_col = "#C3C3C3"

        # Line number canvas inside editor_frame
        self.line_number_canvas = ctk.CTkCanvas(
            self.editor_frame,
            width=60,
            bg=self.bg_color_canvas,
            highlightthickness=1,
            highlightbackground="#5e5e5e")

        # Text editor inside editor_frame
        self.text_editor = ctk.CTkTextbox(
            self.editor_frame,
            border_width=0,
            corner_radius=0,
            text_color="#c4c4c4" if self.mode == 'Dark' else "#3F3F3F",
            font=self.editor_font,
            fg_color="#1D1D1D" if self.mode == 'Dark' else "#E0E0E0",
            wrap=None)

        self.line_number_canvas.pack(side="left", fill="y")
        self.text_editor.pack(fill="both", expand=True)

        tabs_widget = uniwidgets.LayoutsTab(
            self.editor_container,
            textbox=self.text_editor,
            max_layouts=6,
            initial_layouts=2)
        tabs_widget.pack(side="top", fill="x")

        self.text_editor.bind("<MouseWheel>", self.on_mouse_wheel)
        self.line_number_canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        self.font_size_var.trace_add("write", self.update_text_font)
        self.code_font_var.trace_add("write", self.update_text_font)

        self.text_editor.bind("<KeyRelease>", self.update_number_of_lines)
        self.text_editor.bind("<Button-1>", self.update_number_of_lines)
        self.text_editor.bind("<Control-c>", self.copy_text_event)
        self.text_editor.bind("<Control-x>", self.cut_text_event)
        self.text_editor.bind("<Control-v>", self.paste_text_event)
        self.text_editor.bind("<Control-s>", self.save_file)
        self.text_editor.bind("<Control-a>", self.select_all)
        self.text_editor.bind("<Control-f>", self.open_search)
        self.text_editor.bind("<BackSpace>", self.delete_selected_text)
        self.text_editor.bind("<Delete>"   , self.delete_selected_text)

        self.text_editor.tag_config("function_name", foreground="orange")
        self.text_editor.tag_config("class_name", foreground="purple")
        self.text_editor.tag_config("variable_name", foreground="teal")

        self.divider.bind("<Button-1>", self.start_drag)
        self.divider.bind("<B1-Motion>", self.on_drag)

        helper = pylight(self.text_editor)
        intellisense = pysense(widget=self.window, text_box=self.text_editor, path=None)
        intellisense.bindings()

        #################################################################################################
        # FILE EXPLORER TREEVIEW
        #################################################################################################

        self.file_explorer_frame = ctk.CTkFrame(self.sidebar,
                                                fg_color="#292929" if self.mode=="Dark" else "#ADADAD")
        self.file_explorer_frame.pack(fill="both", expand=True)

        self.window.after(self.REFRESH_INTERVAL_MS, self.auto_refresh_workspace)

        self.top_frame = ctk.CTkFrame(self.file_explorer_frame, fg_color="transparent")
        self.top_frame.pack(fill="x", pady=(4,0), padx=8)

        self.load_workspace_btn = ctk.CTkButton(self.top_frame, text="Load",image=self.load_ico,
                                        fg_color=self.file_explorer_frame.cget("fg_color"),
                                        width=15, height=15,
                                        text_color="#ADADAD" if self.mode == 'Dark' else "#292929",
                                        command=self.load_workspace)
        self.load_workspace_btn.pack(side="right",padx=(0,10))

        self.refresh_workspace_btn = ctk.CTkButton(self.top_frame, text="Refresh", image=self.refresh_ico,
                                            fg_color=self.file_explorer_frame.cget("fg_color"),
                                            width=15,height=15,state=ctk.DISABLED,
                                            text_color="#ADADAD" if self.mode == 'Dark' else "#292929",
                                            command=self.refresh_current_workspace)
        self.refresh_workspace_btn.pack(side="right")

        self.label_workspace = ctk.CTkLabel(self.top_frame, text="CURRENT WORKSPACE",
                                    font=("Segoe UI Semibold",13),
                                    fg_color=self.file_explorer_frame.cget("fg_color"))
        self.label_workspace.pack(side="left",padx=(4,0))

        self.horizontal_line = ctk.CTkFrame(self.file_explorer_frame, 
                                    fg_color="#ADADAD" if self.mode=="Dark" else "#292929",
                                    height=2)
        self.horizontal_line.pack(padx=8,fill="x")

        self.tree_frame = ctk.CTkFrame(self.file_explorer_frame, 
                                       fg_color="#292929" if self.mode=="Dark" else "#ADADAD")
        self.tree_frame.pack(fill="both",expand=True, padx=8, pady=(0,4))

        self.no_workspace = ctk.CTkLabel(self.tree_frame, text="",image=self.sleeping)
        self.no_workspace.pack(anchor="center",pady=(30,0))
        self.current_workspace_name = ctk.CTkLabel(self.tree_frame, 
                                                   fg_color=self.file_explorer_frame.cget("fg_color"),
                                                   text="No Current Workspace Active", font=("Segoe UI",13))
        self.current_workspace_name.pack(padx=8,anchor="center",pady=5)

        self.tree_scrollbar = ctk.CTkScrollbar(self.tree_frame, orientation="vertical")

        self.down_frame = ctk.CTkFrame(self.file_explorer_frame, fg_color="transparent")
        self.down_frame.pack(fill="x", pady=(4,0), padx=8)

        self.debug_label = ctk.CTkLabel(self.down_frame, text="RUN AND DEBUG",
                                font=("Segoe UI Semibold",13),
                                fg_color=self.file_explorer_frame.cget("fg_color"))
        self.debug_label.pack(side="left", padx=(0,4))

        self.debug_hor_line = ctk.CTkFrame(self.file_explorer_frame, fg_color=self.number_col,height=2)
        self.debug_hor_line.pack(padx=8,fill="x")

        self.debugging_frame = ctk.CTkFrame(self.file_explorer_frame, fg_color="transparent")
        self.debugging_frame.pack(fill="both", expand=True, padx=8, pady=(0,4))

        self.debug_info = ctk.CTkLabel(self.debugging_frame, fg_color=self.file_explorer_frame.cget("fg_color"),
                                            text="No Current Debugging Configuration Available",
                                            font=("Segoe UI",13))
        self.debug_info.pack(padx=4,anchor="w")
        self.mode = ctk.get_appearance_mode()
        bg_color = "#292929" if self.mode=="Dark" else "#ADADAD"
        fg_color = "#ADADAD" if self.mode=="Dark" else "#292929"
        selected_color = "#0e639c"

        self.file_tree = ttk.Treeview(self.tree_frame,show="tree", yscrollcommand=self.tree_scrollbar.set)
        self.file_tree.pack(fill="both", expand=True, side="left")

        self.file_tree.tag_configure("normal", background=bg_color, foreground=fg_color)
        self.file_tree.tag_configure("hover", background="#6D6D6D" if self.mode == 'Light' else "#BEBEBE", 
                                foreground= "#2B2B2B" if self.mode == 'Light' else "#CCCCCC")

        self.window.bind("<Button-1>", self.click_outside)
        self.file_tree.bind("<Double-1>", self.open_tree_selected_file)
        self.file_tree.bind("<Button-1>", self.on_tree_click)
        self.file_tree.bind("<Motion>", self.on_tree_hover)

        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure("Treeview",
                        background=bg_color,
                        foreground=fg_color,
                        fieldbackground=bg_color,
                        font=("Segoe UI", 11),
                        borderwidth=0,
                        lightcolor=bg_color,
                        darkcolor=bg_color,
                        rowheight=28)
        self.style.map("Treeview", background=[('selected', selected_color)])
        self.style.configure("Treeview.Heading",
                        background=bg_color,
                        foreground=fg_color,
                        relief="flat",
                        borderwidth=0)
        self.style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        self.tree_scrollbar.configure(command=self.file_tree.yview)

    def remove_hover_effects(self):
        for item in self.file_tree.get_children():
            self.file_tree.item(item, tags=("normal",))

    def clear_tree_selection(self):
        for item in self.file_tree.selection():
            self.file_tree.selection_remove(item)

    def on_tree_hover(self,event):
        row_id = self.file_tree.identify_row(event.y)
        for item in self.file_tree.get_children():
            tag = "hover" if item == row_id else "normal"
            self.file_tree.item(item, tags=(tag,))

    def on_tree_click(self,event):
        row_id = self.file_tree.identify_row(event.y)
        if not row_id:
            self.clear_tree_selection()
            self.remove_hover_effects()
    
    def click_outside(self,event):
        x,y = event.x_root, event.y_root
        if not self.file_explorer_frame.winfo_containing(x,y):
            self.remove_hover_effects()
            self.clear_tree_selection()

    def populate_tree(self, path, parent=""):
        """Recursively populate the file_tree with folders/files."""
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    node = self.file_tree.insert(parent, "end",
                                                text=item,
                                                image=self.icons["folder"],
                                                values=(item_path,))
                    self.populate_tree(item_path, parent=node)
                    self.no_workspace.pack_forget()
                    self.current_workspace_name.pack_forget()
                    self.tree_scrollbar.pack(fill="y", side="right")
                else:
                    ext = os.path.splitext(item)[1].lower()
                    if ext in self.allowed_extensions:
                        icon = self.icons.get(ext, self.icons["file"])
                        self.file_tree.insert(parent, "end",
                                            text=item,
                                            image=icon,
                                            values=(item_path,))
        except PermissionError:
            pass

    def load_workspace(self):
        """Open a directory selection dialog and load the workspace."""
        self.selected_path = filedialog.askdirectory()
        if self.selected_path:
            self.workspace_path = Path(self.selected_path)
            self.workspace["path"] = self.workspace_path
            self.file_tree.delete(*self.file_tree.get_children())
            self.populate_tree(self.workspace_path)
            self.current_workspace_name.configure(text=f"{self.workspace_path}")
            self.refresh_workspace_btn.configure(state=ctk.NORMAL)
            self.status_button.configure(text="Workspace loaded successfully")

    def refresh_current_workspace(self):
        """Refresh the currently loaded workspace."""
        if not getattr(self, "workspace_path", None):
            self.refresh_workspace_btn.configure(state=ctk.DISABLED)
            self.status_button.configure(text="Failed to refresh workspace")
            return
        self.file_tree.delete(*self.file_tree.get_children())
        self.populate_tree(self.workspace_path)
        self.status_button.configure(text="Workspace refreshed successfully")
        self.refresh_workspace_btn.configure(state=ctk.NORMAL)

    def auto_refresh_workspace(self):
        """Automatically refresh workspace every REFRESH_INTERVAL_MS milliseconds."""
        if getattr(self, "workspace_path", None):
            self.status_button.configure(text="Refreshing ...")
            self.file_tree.delete(*self.file_tree.get_children())
            self.populate_tree(self.workspace_path)
            self.status_button.configure(text="Refreshing finished")
        # Schedule the next refresh
        self.window.after(self.REFRESH_INTERVAL_MS, self.auto_refresh_workspace)

    def open_tree_selected_file(self, event=None):
        """Open the file currently selected in the tree."""
        self.selected_item = self.file_tree.focus()
        if not self.selected_item:
            return

        self.file_path_tuple = self.file_tree.item(self.selected_item, "values")
        if not self.file_path_tuple:
            return

        self.file_path = self.file_path_tuple[0]

        if not os.path.isfile(self.file_path):
            return  # ignore folders

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.text_editor.delete("1.0","end")
            self.text_editor.insert("1.0",content)
            self.status_button.configure(text=f"File {self.file_path} opened")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")
            self.status_button.configure(text="Operation Failed")

    def copy_text_event(self, event=None):
        try:
            selected_text = self.text_editor.selection_get()
            pyperclip.copy(selected_text)
            self.status_button.configure(text="Text copied")
        except tk.TclError:
            pass
        return "break"

    def cut_text_event(self, event=None):
        try:
            selected_text = self.text_editor.selection_get()
            pyperclip.copy(selected_text)
            self.text_editor.delete("sel.first", "sel.last")
            self.status_button.configure(text="Text cut")
        except tk.TclError:
            pass
        return "break"

    def paste_text_event(self, event=None):
        content = pyperclip.paste()
        self.text_editor.insert(tk.INSERT, content)
        self.status_button.configure(text="Text pasted")
        return "break"

    def select_all(self, event=None):
        last_index = self.text_editor.index("end-1c")
        number_of_lines = int(last_index.split(".")[0])

        for i in range(1, number_of_lines + 1):
            self.text_editor.tag_add("sel", f"{i}.0", f"{i}.end")
        
        self.text_editor.mark_set(tk.INSERT, "1.0")
        self.text_editor.see(tk.INSERT)
        return "break"

    def delete_selected_text(self,event=None):
        self.text_editor.selection_clear()

    
    def update_text_font(self,*args):
        self.editor_font.configure(family=self.code_font_var.get(), size=self.font_size_var.get())
        self.line_number_font.configure(family=self.code_font_var.get(), size=self.font_size_var.get() + 2)
        self.text_editor.configure(font=self.editor_font)
        self.update_number_of_lines()

    def start_drag(self,event):
        self.divider.start_x = event.x

    def on_drag(self,event):
        dx = event.x - self.divider.start_x
        new_width = self.sidebar.winfo_width() + dx
        if 5 <= new_width <= 360: 
            self.sidebar.configure(width=new_width)
            self.sidebar.pack_propagate(False)
            self.sidebar.pack(side="left", fill="y")
            self.editor_frame.pack(side="left", fill="both", expand=True)

    def update_number_of_lines(self,event=None):
        self.line_number_canvas.delete("all")
        total_lines = int(self.text_editor.index("end-1c").split(".")[0])
        canvas_height = 0

        for i in range(1, total_lines + 1):
            bbox = self.text_editor.bbox(f"{i}.0")
            if bbox:
                y = bbox[1] 
                height = bbox[3]
                canvas_height = max(canvas_height, y + height)
                self.line_number_canvas.create_text(
                    50, y, anchor="ne", text=str(i),
                    font=self.line_number_font,
                    fill= self.number_col)

        self.canvas_widget_height = self.line_number_canvas.winfo_height()
        if canvas_height <= self.canvas_widget_height:
            self.line_number_canvas.configure(scrollregion=(0, 0, 40, self.canvas_widget_height))
        else:
            self.line_number_canvas.configure(scrollregion=(0, 0, 40, canvas_height))

    def on_mouse_wheel(self,event):
        scroll_units = int(-1 * (event.delta / 120))
        self.text_editor.yview_scroll(scroll_units, "units")
        self.line_number_canvas.yview_scroll(scroll_units, "units")
        return "break"
    
    def click_outside(self, event):
        widget = event.widget
        # check if widget is inside editor_frame
        if not self.is_child_of(widget, self.editor_frame) and widget != self.cpuInfo:
            self.hide_debug_menu()
            self.window.unbind("<Button-1>")
            self.cpuInfo.configure(image=self.rightArrow)

    def is_child_of(self, widget, parent):
        while widget:
            if widget == parent:
                return True
            widget = widget.master
        return False

    def hide_debug_menu(self,event=None):
            """Hide the active debug menu if it exists."""
            if self.active_menu["menu"] is not None:
                self.active_menu["menu"].destroy()
                self.active_menu["menu"] = None

    def debugging_menu(self):
        """Toggle the debug info menu visibility."""
        # If menu is already open → close it
        if self.active_menu["menu"] is not None:
            self.hide_debug_menu()
            self.cpuInfo.configure(image=self.rightArrow)
            return

        # Otherwise, open the menu
        self.cpuInfo.configure(image=self.downArrow)
        self.frame = ctk.CTkFrame(
            self,
            fg_color="#1e1e1e" if self.mode == 'Dark' else "#5e5e5e",
            bg_color="#1e1e1e" if self.mode == 'Dark' else "#5e5e5e",
            border_color="#bcbcbc" if self.mode == 'Dark' else "#292929",
            border_width=1,
            corner_radius=10)
        self.frame.place(x=553, y=100)
        self.active_menu["menu"] = self.frame

        for option in self.menus["DebugInfo"]:
            btn = ctk.CTkButton(
                self.frame,
                text=option,
                text_color="#e8e8e8" if self.mode == 'Dark' else "#2D2D2D",
                fg_color="#1e1e1e" if self.mode == 'Dark' else "#757575",
                corner_radius=2,
                width=190,
                height=25,
                anchor="w",
                border_color="#bcbcbc" if self.mode == 'Dark' else "#292929",
                border_width=1,
                font=("Segoe UI", 13))
            btn.pack()

        self.window.bind("<Button-1>", lambda e: self.click_outside(e))

    def show_tab(self,frame_to_show):
        for frame in self.allTabs:
            frame.pack_forget()  # Hide every frame
        frame_to_show.pack(fill="both", side="top")
        frame_to_show.pack_propagate(False)

    def customDropDownFrameChanger(self,frame_to_show):
        # Hide all frames first
        for f in [self.plots2d, self.plots3d, self.scientific]:
            f.place_forget()
        # Show the requested frame
        frame_to_show.place(x=2, y=2)

    def open_terminal(self,event=None):
        subprocess.Popen("start cmd",shell=True)

    def open_file_manager(self,event=None):
        file_manager.main_terminal()

    def open_command_window(self):
        shell = command_window.PromptXShell(self.window)
        shell.grab_set() 

    def open_settings(self,event=None):
        settings_window = SettingsWindow(self, status_button=self.status_button)
        settings_window.show()

    def open_search(self, event=None):
        search_window = KeywordSearch(self, self.text_editor, status_button=self.status_button)
        search_window.show()

    def save_file(self,event=None):
        save_file = SaveFile(self, workspace_container= self.workspace, status_button=self.status_button)
        save_file.show()

    def open_license(self,event=None):
        license_window = LicenseOpen(self, status_button=self.status_button)
        license_window.show()

    def ports_and_terminals_open(self, event=None):
        terminals = DebugAndTerminal(self, status_button=self.status_button)
        terminals.show_terminal()

    def open_current_file(main_app):
        if main_app.status_button:
            main_app.status_button.configure(text="Opening file")

        current_file = filedialog.askopenfilename(title="Select an existing file")
        if not current_file:
            return

        try:
            with open(current_file, "r", encoding="utf-8") as f:
                content = f.read()

            main_app.text_editor.delete("1.0","end")
            main_app.text_editor.insert("1.0", content)
            if main_app.status_button:
                main_app.status_button.configure(text=f"File {current_file} opened")

        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")
            if main_app.status_button:
                main_app.status_button.configure(text="Operation Failed")

    def onOpenSyntax(self, event=None):
        syntaxTab = home.ConfigureSyntax(self, master=self.window, text_editor=self.text_editor)
        syntaxTab.run()

    def load_theme(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    theme = config.get("theme")
                    if theme in ["Light", "Dark"]:
                        return theme
            except json.JSONDecodeError:
                pass
        return "Dark"

    def run(self):
        self.window.mainloop()

def darken_color(hex_color, factor=0.8):
    """
    Darken a hex color by multiplying its RGB channels by `factor` (0 < factor < 1).
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = max(min(int(r * factor), 255), 0)
    g = max(min(int(g * factor), 255), 0)
    b = max(min(int(b * factor), 255), 0)
    return f"#{r:02X}{g:02X}{b:02X}"

class CTkFrameDarker(ctk.CTkFrame):
    def __init__(self, master,**kwargs):
        theme_colors = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        self.mode_index = 0 if ctk.get_appearance_mode() == "Light" else 1
        color = darken_color(theme_colors[self.mode_index], factor=0.75)  # Slightly darker
        super().__init__(master, fg_color=color,border_color="#5e5e5e",border_width=1,**kwargs)

class CTkFrameVeryDark(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        theme_colors = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        self.mode_index = 0 if ctk.get_appearance_mode() == "Light" else 1
        color = darken_color(theme_colors[self.mode_index], factor=0.55)  # Much darker
        super().__init__(master, fg_color=color,border_color="#5e5e5e",border_width=1, **kwargs)

class KeywordSearch(ctk.CTkToplevel):
    def __init__(self, main_app, text_frame, status_button=None):
        super().__init__(main_app.window)
        self.main_app = main_app
        self.text_frame = text_frame
        self.status_button = status_button
        self.matches = []
        self.current_match_index = 0

        if self.status_button:
            self.status_button.configure(text="search menu opened")

        self.title("Find and Search")
        self.geometry("350x150")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.withdraw()
        self.transient(main_app.window)

        label = ctk.CTkLabel(self, text="Enter Keyword/Sentence/etc", font=("Segoe UI", 12))
        label.pack(pady=(20,5))

        self.file_naming_box = ctk.CTkEntry(self, width=250)
        self.file_naming_box.place(x=350/2, y=150/2, anchor='center')

        confirm_button = ctk.CTkButton(self, text="Search", width=100, corner_radius=6, command=self.searching)
        confirm_button.place(x=100/2, y=100)
        confirm_button.focus_set()
        self.bind("<Return>", lambda e: confirm_button.invoke())

        self.next_search_btn = ctk.CTkButton(self, text="\u2B9F", width=40, corner_radius=6, state=ctk.DISABLED,
                                             command=self.next_search_match)
        self.next_search_btn.place(x=260, y=100)

        self.previous_search_btn = ctk.CTkButton(self, text="\u2B9D", width=40, corner_radius=6, state=ctk.DISABLED,
                                                 command=self.previous_search_match)
        self.previous_search_btn.place(x=210, y=100)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def show(self):
        self.deiconify()
        self.lift()

    def searching(self):
        text_to_search = self.file_naming_box.get()
        full_text = self.text_frame.get("1.0", "end-1c")

        self.main_app.text_editor.tag_remove("highlight", "1.0", "end-1c")
        self.matches = list(re.finditer(re.escape(text_to_search), full_text))
        if self.matches:
            self.current_match_index = 0
            first_match = self.matches[self.current_match_index]
            start_index = f"1.0+{first_match.start()}c"
            self.main_app.text_editor.mark_set("insert", start_index)
            self.main_app.text_editor.see(start_index)
            for match in self.matches:
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.main_app.text_editor.tag_add("highlight", start, end)
            self.main_app.text_editor.tag_config("highlight", background="#633B24", foreground="#FFFFFF")
            if self.status_button:
                self.status_button.configure(text="Search found successfully!")
            self.next_search_btn.configure(state=ctk.NORMAL)
            self.previous_search_btn.configure(state=ctk.NORMAL)
        else:
            if self.status_button:
                self.status_button.configure(text="No matches found!")

    def next_search_match(self):
        if not self.matches:
            return
        self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        index = f"1.0+{self.matches[self.current_match_index].start()}c"
        self.main_app.text_editor.mark_set("insert", index)
        self.main_app.text_editor.see(index)

    def previous_search_match(self):
        if not self.matches:
            return
        self.current_match_index = (self.current_match_index - 1) % len(self.matches)
        index = f"1.0+{self.matches[self.current_match_index].start()}c"
        self.main_app.text_editor.mark_set("insert", index)
        self.main_app.text_editor.see(index)

    def on_close(self):
        self.main_app.text_editor.tag_remove("highlight", "1.0", "end-1c")
        self.destroy()

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, main_app, status_button=None):
        super().__init__(main_app.window)
        self.main_app = main_app
        self.status_button = status_button

        if self.status_button:
            self.status_button.configure(text="Settings Opened")

        self.settings_and_preferences = self
        self.title("Settings and Preferences")
        self.geometry("900x700")
        self.resizable(True, True)
        self.withdraw()
        self.transient(main_app.window)

        scrollable_frame = ctk.CTkScrollableFrame(
            self.settings_and_preferences,
            fg_color="transparent"
        )
        scrollable_frame.pack(fill="both", expand=True, padx=20, pady=20)
        scrollable_frame.grid_columnconfigure(0, weight=1)

        # --- Accessibility Section ---
        accessibility_label = ctk.CTkLabel(
            scrollable_frame,
            text="Accessibility",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        )
        accessibility_label.grid(row=0, column=0, padx=0, pady=(0, 15), sticky='w')

        accessibility_frame = CTkFrameDarker(
            scrollable_frame,
            corner_radius=8
        )
        accessibility_frame.grid(row=1, column=0, padx=0, pady=(0, 20), sticky='ew')
        accessibility_frame.grid_columnconfigure(0, weight=1)
        accessibility_frame.grid_columnconfigure(1, weight=0)

        # Font Size
        settings_font_label = ctk.CTkLabel(
            accessibility_frame,
            text="Font Size",
            font=ctk.CTkFont(family="Segoe UI", size=14)
        )
        settings_font_label.grid(row=0, column=0, padx=(20, 10), pady=(15, 10), sticky="w")

        font_number_changer = ctk.CTkLabel(
            accessibility_frame,
            text=str(main_app.font_size_var.get()),
            font=ctk.CTkFont(family="Segoe UI", size=14)
        )
        font_number_changer.grid(row=0, column=1, padx=(0, 20), pady=(15, 10), sticky="e")

        def on_font_slider_change(value):
            main_app.font_size_var.set(int(float(value)))
            font_number_changer.configure(text=str(main_app.font_size_var.get()))
            if status_button:
                status_button.configure(text="Font size changed")

        font_change_slider = ctk.CTkSlider(
            accessibility_frame,
            from_=8,
            to=24,
            number_of_steps=16,
            command=on_font_slider_change,
            width=300
        )
        font_change_slider.set(main_app.font_size_var.get())
        font_change_slider.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")

        # --- Appearance Section ---
        appearance_label = ctk.CTkLabel(
            scrollable_frame,
            text="Appearance",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        )
        appearance_label.grid(row=2, column=0, padx=0, pady=(0, 15), sticky='w')

        appearance_frame = CTkFrameDarker(
            scrollable_frame,
            corner_radius=8
        )
        appearance_frame.grid(row=3, column=0, padx=0, pady=(0, 20), sticky='ew')
        appearance_frame.grid_columnconfigure(0, weight=1)
        appearance_frame.grid_columnconfigure(1, weight=0)

        # Font Family
        font_family_label = ctk.CTkLabel(
            appearance_frame,
            text="Font Family",
            font=ctk.CTkFont(family="Segoe UI", size=14)
        )
        font_family_label.grid(row=1, column=0, padx=(20,10), pady=(20, 10), sticky="w")

        def on_font_family_changer(value):
            main_app.code_font_var.set(str(value))
            if status_button:
                status_button.configure(text="Font changed")

        font_family_var = ctk.StringVar(value=main_app.code_font_var.get())
        font_family_combo = ctk.CTkComboBox(
            appearance_frame,
            values=[
                "Cascadia Code","Consolas","Courier","Courier New",
                "DejaVu Sans Mono","Fira Code","Liberation Mono",
                "Lucida Console","Menlo","Monaco","Source Code Pro",
                "Roboto Mono","Ubuntu Mono"
            ],
            variable=font_family_var,
            width=150,
            command=on_font_family_changer
        )
        font_family_combo.grid(row=1, column=1, padx=(0, 20), pady=(20, 10), sticky="e")

        text_editor_theme_label = ctk.CTkLabel(
            appearance_frame,
            text="Text Editor Theme",
            font=ctk.CTkFont(family="Segoe UI", size=14))
        text_editor_theme_label.grid(row=2, column=0, padx=(20, 10), pady=(0, 10), sticky="w")

        editor_themes_var = ctk.StringVar(value="Dark")
        def theme_changer(selected_theme):
            textbox = main_app.text_editor
            if selected_theme == "Blue":
                textbox.configure(fg_color="#2B3036", text_color="white")
            elif selected_theme == "Red":
                textbox.configure(fg_color="#393C3E", text_color="white")
            elif selected_theme == "Dark":
                textbox.configure(fg_color="#1e1e1e", text_color="#d4d4d4")
            elif selected_theme == "Light":
                textbox.configure(fg_color="white", text_color="black")

        frame_theme_changer_combo = ctk.CTkComboBox(
            appearance_frame,
            values=["Blue","Red","Dark","Light"],
            variable=editor_themes_var,
            width=150,
            command=theme_changer)
        frame_theme_changer_combo.grid(row=2, column=1, padx=(0, 20), pady=(0, 10), sticky="e")

    def show(self):
        self.deiconify()
        self.lift()


class SaveFile(ctk.CTkToplevel):
    def __init__(self, main_app, workspace_container, status_button=None):
        """
        main_app: reference to your main App() instance
        workspace_container: dict/object containing current workspace path
        status_button: optional, for updating status
        """
        super().__init__(main_app.window)
        self.main_app = main_app
        self.workspace_container = workspace_container
        self.status_button = status_button

        if self.status_button:
            self.status_button.configure(text="Waiting to save file")

        self.title("Save File")
        self.geometry("360x160")
        self.resizable(False, False)
        self.withdraw()
        self.transient(main_app.window)

        label = ctk.CTkLabel(self, text="Enter file name:", font=("Segoe UI", 12))
        label.pack(pady=(20, 5))

        file_naming_box = ctk.CTkEntry(self, width=250, placeholder_text="untitled.txt")
        file_naming_box.place(x=55, y=50)

        def save_file():
            filename = file_naming_box.get().strip()
            file_content = main_app.text_editor.get("1.0", "end-1c")

            if not filename:
                uniwidgets.ScreenShakeAnimation(file_naming_box, orig_x=55, orig_y=50)
                file_naming_box.configure(
                    placeholder_text="Please enter a file name",
                    placeholder_text_color="#ffb2b2")
                return

            if self.workspace_container.get("path") is None:
                uniwidgets.ScreenShakeAnimation(confirm_button, orig_x=130, orig_y=100)
                if self.status_button:
                    self.status_button.configure(text="No workspace active to save file!")
                return

            if '.' not in filename:
                filename += ".txt"

            file_path = self.workspace_container["path"] / filename
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file_content)
                messagebox.showinfo("Success", f"File saved successfully as {filename}")
                if self.status_button:
                    self.status_button.configure(text=f"{filename} saved")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{e}")
                if self.status_button:
                    self.status_button.configure(text=f"{filename} could not be saved")
            self.destroy()

        confirm_button = ctk.CTkButton(self, font=("Segoe UI", 12), text="Save",
                                       width=100, corner_radius=6, command=save_file)
        confirm_button.place(x=130, y=100)

    def show(self):
        self.deiconify()
        self.lift()


class LicenseOpen(ctk.CTkToplevel):
    def __init__(self, main_app, status_button=None):
        """
        main_app: reference to your main App() instance
        status_button: optional, for updating status
        """
        super().__init__(main_app.window)
        self.main_app = main_app
        self.status_button = status_button

        if self.status_button:
            self.status_button.configure(text="License opened")

        self.license_window = self
        self.title("Software License")
        self.geometry("500x350")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.withdraw()
        self.transient(main_app.window)

        license_label = ctk.CTkLabel(
            self.license_window,
            text=license_text,  # make sure license_text is defined
            font=("Segoe UI", main_app.font_size_var.get()),
            wraplength=480,
            justify="left"
        )
        license_label.pack(padx=10, pady=10)

    def show(self):
        self.deiconify()
        self.lift()

class DebugAndTerminal(ctk.CTkToplevel):
    def __init__(self, main_app, status_button=None):
        super().__init__(main_app.window)
        self.main_app = main_app
        self.status_button = status_button

        self.mode = ctk.get_appearance_mode()

        self.configure(fg_color="#1C1C1C" if self.mode == 'Dark' else "#BDBDBD")

        if self.status_button:
            self.status_button.configure(text="Terminal Opened")

        self.overrideredirect(True)
        self.geometry("1000x250")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.withdraw()
        self.transient(main_app.window)

        self.terminal_box = ctk.CTkTextbox(
            self, corner_radius=0, font=("Consolas", 14), width=990, height=205,
            bg_color="#0F0F0F" if self.mode == 'Dark' else "#ACACAC",
            fg_color="#0F0F0F" if self.mode == 'Dark' else "#ACACAC")
        self.terminal_box.place(x=5, y=40)
        btn_size = 20

        self.title = ctk.CTkLabel(self, width=40, height=20, corner_radius=0, 
                                  text="TERMINALS AND DEBUGGING", font=("Segoe UI",13))
        self.title.place(x=20, y=10)

        self.closeBtn = ctk.CTkButton(self, width=btn_size, height=btn_size, corner_radius=0,
                                      border_color="#5E5E5E", border_width=1, text="✕",
                                      command=self.exitTerminal)
        self.closeBtn.place(x=965, y=10)

        self.minimizeBtn = ctk.CTkButton(self, width=btn_size, height=btn_size, corner_radius=0,
                                         border_color="#5E5E5E", border_width=1, text="─")
        self.minimizeBtn.place(x=940, y=10)

        self.moreActionsBtn = ctk.CTkButton(self, width=btn_size, height=btn_size, corner_radius=0,
                                            border_color="#5E5E5E", border_width=1, text="...")
        self.moreActionsBtn.place(x=915, y=10)

    def exitTerminal(self):
        self.destroy()

    def showInitialText(self):
        self.terminal_box.insert("1.0",f"{os.getcwd()} >>> ")

    def show_terminal(self):
        self.showInitialText()
        self.deiconify()
        self.lift()

#####################################################################################################
# RUN AND MODIFY
#####################################################################################################
if __name__ == '__main__':
    app = App()
    app.run()