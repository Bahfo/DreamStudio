icon_paths = {
    "load_ico": r"icons\system\load.png",
    "refresh_ico": r"icons\system\refresh.png",
    "console": r"icons\system\console.png",
    "debug": r"icons\system\debug.png",
    "manage": r"icons\system\manager.png",
    "problem": r"icons\system\problem.png",
    "ver": r"icons\system\version.png",
    "warning": r"icons\system\warning.png",
}

ctk_icons = {
    "search_photo": (r"icons\system\search.png", (24, 24)),
    "open_photo": (r"icons\system\open_folder.png", (24, 24)),
    "settings_photo": (r"icons\system\settings.png", (24, 24)),
    "save_photo": (r"icons\system\save_file.png", (24, 24)),
    "user_photo": (r"icons\system\user.png", (24, 24)),
    "sleeping": (r"icons\types\sleeping.ico", (80, 80)),
}

arrow_icons = {
    "downArrow": (r"icons\system\down_arrow.png", (8, 8)),
    "upArrow": (r"icons\system\up_arrow.png", (8, 8)),
    "rightArrow": (r"icons\system\right_arrow.png", (8, 8)),
    "stepTo": (r"icons\system\stepTo.png", (20, 20)),
    "stepOut": (r"icons\system\stepOut.png", (20, 20)),
    "stepOver": (r"icons\system\stepOver.png", (20, 20)),
    "runToCursor": (r"icons\system\runToCursor.png", (20, 20)),
    "toggleCursor": (r"icons\system\toggle.png", (20, 20)),
}

allowed_extensions = {
    ".py",".txt",".c",".cpp",".json",".docx",".ppt",".pptx",".apk",
    ".cpp",".cs",".cc",".cxx",".html",".js",".java",".swift",".rb",
    ".ts",".jsx",".py",".h"}

import os
import time
import json
import subprocess
import customtkinter as ctk
from tkinter import filedialog, messagebox

from widgets.imageload import *
from functools import lru_cache
from widgets.texteditor import Editor, Languages

import widgets.TabView as TabView
import widgets.search_menu as search_menu
from widgets.universal_widgets import *
from widgets.ctk_tabview import *

ctk.set_appearance_mode('system')

class App:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.geometry("1000x700")
        self.window.resizable(True, True)
        self.window.title("Dream Studio")
        self.window.iconbitmap(r"icons/dreamstudio_icon.ico")
        
        ########################
        # DEFINITIONS
        ########################
        self.tab_count = 0
        self.mode = ctk.get_appearance_mode()
        self.current_session_editors_open = {}
        self.workspace = dict[str, ctk.CTkButton]
        
        self.seg_font = ctk.CTkFont(family="Segoe UI", size=12, weight="normal")

        self.font_size_var = ctk.IntVar(value=14)
        self.code_font_var = ctk.StringVar(value="Consolas")

        for attr, path in icon_paths.items():
            setattr(self, attr, AppIcons.padded_icon(path))

        for attr, (path, size) in ctk_icons.items():
            setattr(self, attr, load_ctk_icon(path, size))

        for attr, (path, size) in arrow_icons.items():
            setattr(self, attr, load_ctk_icon(path, size, dark_path=path))

        ########################
        # MENUS LOOP ITERATION
        ########################
        self.menubar = ctk.CTkFrame(self.window, height=110, corner_radius=0)
        self.menubar.pack(fill="x", side="top")
        self.menubar.pack_propagate(False)

        # Creating Holding Frames for the Menus
        self.topFrame = ctk.CTkFrame(
            self.menubar, height=18, fg_color="#004073", corner_radius=0)
        self.topFrame.pack(fill="x", side="top")

        BUTTON_CONFIG = {
            "height": 24,
            "fg_color": "#004073",
            "corner_radius": 0,
            "width": 80,
            "font": ("Segoe UI", 12)}

        # Defining the menu structure
        menu_items = [
            ("HOME",      self.topFrame, "homeBtn"),
            ("TOOLS",     self.topFrame, "toolsBtn"),
            ("DATABASES", self.topFrame, "databasesBtn"),
            ("PLOTS",     self.topFrame, "plotsBtn"),
            ("DEBUG",     self.topFrame, "debugBtn"),
            ("TERMINAL",  self.topFrame, "terminalBtn"),
            ("HELP",      self.topFrame, "helpBtn")]

        # Looping to create and pack standard buttons
        for text, frame, attr_name in menu_items:
            btn = ctk.CTkButton(
                self.topFrame,
                text=text,
                command=lambda f=frame, a=attr_name: self._show_menu_tab(f, getattr(self, a)),
                **BUTTON_CONFIG
            )
            btn.pack(side="left", anchor="w", padx=(8, 0))
            setattr(self, attr_name, btn) # Saves reference to self.homeBtn, etc.

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

        # Menus Services
        self.downFrame = ctk.CTkFrame(self.menubar, height=100, corner_radius=0)
        self.downFrame.pack(fill="x", side="top")

        home_toolbar = HomeFrame()
    
    def show(self):
        self.window.mainloop()


class HomeFrame:
    def __init__(self):
        self.homeFrame = ctk.CTkFrame(
            self.downFrame,
            corner_radius=0,
            height=122,
            border_color="#5e5e5e",
            border_width=1,
            fg_color=["#D2D2D2","#1E1E1E"])
        self.homeFrame.pack(fill="both", side="top")
        self.homeFrame.pack_propagate(False)

        self.parent_color = self.homeFrame.cget("fg_color")

        self._icon_cache = {}
        self._create_buttons()
        self._create_separators()

    def _load_icon(self, path):
        """Cache image paths (do not open CTkImage here)"""
        if path not in self._icon_cache:
            self._icon_cache[path] = path
        return self._icon_cache[path]

    def _create_buttons(self):
        """Defines and creates all buttons using a single loop."""

        style = {
            "font": ("Segoe UI", 12),
            "fg_color": self.parent_color,
            "hover_color": "#3a3a3a"}

        # Configuration: (Attribute, Class, Icon, Text, X, Y, Optional Method Name)
        button_defs = [
            ("newFile", VerticalButton, "new_file.png", " New Tab ", 5, 5, "new_file"),
            ("newMacro", VerticalButton, "new_macro.png", " New Code", 75, 5, "new_macro"),
            ("openCode", VerticalButton, "open_code.png", "Open Code", 152, 5, "open_code"),
            ("refreshWorkspace", HorizontalButton, "refresh_workspace.png", "Refresh Files", 230, 7, "refresh"),
            ("saveAll", HorizontalButton, "save_all.png", "Save All Files", 230, 37, "save_all"),
            ("pasteBtn", VerticalButton, "paste.png", "Paste Code", 350, 5, "paste"),
            ("cutBtn", HorizontalButton, "cut.png", " Cut Codes", 428, 7, "cut"),
            ("copyBtn", HorizontalButton, "copy.png", " Copy Codes", 428, 37, "copy"),
            ("undoBtn", HorizontalButton, "undo.png", "Undo Action", 538, 7, "undo"),
            ("redoBtn", HorizontalButton, "redo.png", "Redo Action", 538, 37, "redo"),
            ("deleteBtn", HorizontalButton, "delete.png", "Delete Codes", 648, 7,  "delete"),
            ("replaceBtn", HorizontalButton, "replace.png", "Find/Replace", 648, 37, "replace"),
            ("syntaxBtn", VerticalButton,   "syntax.png", "Configure \nSyntax", 770, 5)]

        for data in button_defs:
            attr, widget, icon, text, x, y, *method = data
            cmd = getattr(self.logic, method[0]) if method else None

            btn = widget(
                self.parent,
                image_path=self._load_icon(rf"icons\system\{icon}"),
                text=text,
                command=cmd,
                **style)
            btn.place(x=x, y=y)
            setattr(self, attr, btn)

    def _create_separators(self):
        """Separators also created automatically."""
        separators = [("vertical_sep_1", 340, 7), ("vertical_sep_2", 760, 7)]
        for name, x, y in separators:
            sep = ctk.CTkFrame(
                self.parent,
                bg_color="transparent",
                width=2,
                height=75,
                corner_radius=0,
            )
            setattr(self, name, sep)
            sep.place(x=x, y=y)

if __name__ == '__main__':
    app = App()
    app.show()