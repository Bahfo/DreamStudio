"""
Handles first layer: Graphical User Interface Layer (GUI Layer)
\nDreamStudio is now only supported for some languages:
\nLua, Python, and JavaScript
"""

CONFIG_FILE = r"themes\config\config.json"
REFRESH_INTERVAL_MINUTES = 2
REFRESH_INTERVAL_MS = REFRESH_INTERVAL_MINUTES * 60 * 1000

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

import json
import os
import threading
import subprocess
import CTkTable
from tkinter import filedialog, messagebox
from cupcake import Editor, Languages

import customtkinter as ctk
from PIL import Image
from functools import lru_cache
import widgets.universal_widgets as uniwidgets
import main_scripts.save_menu as save_menu
import main_scripts.serach_menu as search_menu

################################################################################################
# MAIN WINDOW
################################################################################################

class AppIcons:
    @staticmethod
    @lru_cache(maxsize=None)
    def create_padded_icon(ico_path, icon_size=(16, 16), padding=8):
        from PIL import ImageTk

        try:
            icon_img = Image.open(ico_path).convert("RGBA").resize(icon_size)
            img = Image.new(
                "RGBA", (icon_size[0] + padding, icon_size[1]), (0, 0, 0, 0)
            )
            img.paste(icon_img, (0, 0), icon_img)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Warning: Could not load icon {ico_path}: {e}")
            img = Image.new(
                "RGBA", (icon_size[0] + padding, icon_size[1]), (0, 0, 0, 0)
            )
            return ImageTk.PhotoImage(img)


def ctk_image_cache(func):
    """Decorator to cache CTkImage objects"""
    cached = {}

    def wrapper(path, size, dark_image=None):
        key = (path, size)
        if key not in cached:
            img = Image.open(path)
            if dark_image is None:
                cached[key] = ctk.CTkImage(light_image=img, size=size)
            else:
                dark_img = Image.open(dark_image)
                cached[key] = ctk.CTkImage(
                    light_image=img, dark_image=dark_img, size=size
                )
        return cached[key]

    return wrapper


@ctk_image_cache
def load_ctk_icon(path, size, dark_image=None):
    pass

ctk.set_appearance_mode("dark")

class App:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Dream Studio")
        self.window.geometry("1000x700")
        self.window.resizable(True, True)

        #################################################################################################
        # DEFINITIONS
        #################################################################################################

        self.workspace = {"path": None}

        self.font_size_var = ctk.IntVar(value=14)
        self.code_font_var = ctk.StringVar(value="Consolas")

        for attr, path in icon_paths.items():
            setattr(self, attr, AppIcons.create_padded_icon(path))

        for attr, (path, size) in ctk_icons.items():
            setattr(self, attr, ctk.CTkImage(light_image=Image.open(path), size=size))

        for attr, (path, size) in arrow_icons.items():
            setattr(self, attr, ctk.CTkImage(dark_image=Image.open(path), size=size))

        ################################################################################################
        # MENUS: Define showing menus, menubar, topframe, downframe, and their buttons
        ################################################################################################

        self.menubar = ctk.CTkFrame(self.window, height=110, corner_radius=0)
        self.menubar.pack(fill="x", side="top")
        self.menubar.pack_propagate(False)

        # Creating Holding Frames for the Menus
        self.topFrame = ctk.CTkFrame(
            self.menubar, height=18, fg_color="#004073", corner_radius=0
        )
        self.topFrame.pack(fill="x", side="top")

        # Services Buttons
        self.homeBtn = ctk.CTkButton(
            self.topFrame,
            height=24,
            fg_color="#004073",
            corner_radius=0,
            width=80,
            text="HOME",
            font=("Segoe UI", 12),
            command=lambda: self.show_tab(self.homeFrame, self.homeBtn),
        )

        self.homeBtn.pack(side="left", anchor="w", padx=(8, 0))

        self.toolsBtn = ctk.CTkButton(
            self.topFrame,
            height=24,
            fg_color="#004073",
            corner_radius=0,
            width=80,
            text="TOOLS",
            font=("Segoe UI", 12),
            command=lambda: self.show_tab(self.toolsFrame, self.toolsBtn),
        )

        self.toolsBtn.pack(side="left", anchor="w", padx=(8, 0))

        self.databasesBtn = ctk.CTkButton(
            self.topFrame,
            height=24,
            fg_color="#004073",
            corner_radius=0,
            width=80,
            text="DATABASES",
            font=("Segoe UI", 12),
            command=lambda: self.show_tab(self.databasesFrame, self.databasesBtn),
        )

        self.databasesBtn.pack(side="left", anchor="w", padx=(8, 0))

        self.plotsBtn = ctk.CTkButton(
            self.topFrame,
            height=24,
            fg_color="#004073",
            corner_radius=0,
            width=80,
            text="PLOTS",
            font=("Seoge UI", 12),
            command=lambda: self.show_tab(self.plotsFrame, self.plotsBtn),
        )

        self.plotsBtn.pack(side="left", anchor="w", padx=(8, 0))

        self.debugBtn = ctk.CTkButton(
            self.topFrame,
            height=24,
            fg_color="#004073",
            corner_radius=0,
            width=80,
            text="DEBUG",
            font=("Seoge UI", 12),
            command=lambda: self.show_tab(self.debugFrame, self.debugBtn),
        )

        self.debugBtn.pack(side="left", anchor="w", padx=(8, 0))

        self.terminalBtn = ctk.CTkButton(
            self.topFrame,
            height=24,
            fg_color="#004073",
            corner_radius=0,
            width=80,
            text="TERMINAL",
            font=("Segoe UI", 12),
            command=lambda: self.show_tab(self.terminalFrame, self.terminalBtn),
        )

        self.terminalBtn.pack(side="left", anchor="w", padx=(8, 0))

        self.helpBtn = ctk.CTkButton(
            self.topFrame,
            height=24,
            fg_color="#004073",
            corner_radius=0,
            width=80,
            text="HELP",
            font=("Seoge UI", 12),
            command=lambda: self.show_tab(self.helpFrame, self.helpBtn),
        )

        self.helpBtn.pack(side="left", anchor="w", padx=(8, 0))

        self.accountBtn = ctk.CTkButton(
            self.topFrame,
            height=20,
            fg_color="#004073",
            corner_radius=0,
            width=100,
            text="ACCOUNT",
            font=("Segoe UI", 12),
            image=self.downArrow,
        )

        self.accountBtn.pack(side="right", anchor="e", padx=(8, 8))

        # Menus Services
        self.downFrame = ctk.CTkFrame(self.menubar, height=100, corner_radius=0)
        self.downFrame.pack(fill="x", side="top")

        ################################################################################################
        # HOME MENU: Home menu buttons and their functionalities
        ################################################################################################

        self.homeFrame = ctk.CTkFrame(
            self.downFrame,
            corner_radius=0,
            height=122,
            border_color="#5e5e5e",
            border_width=1,
            fg_color=["#D2D2D2","#1E1E1E"],
        )
        self.homeFrame.pack(fill="both", side="top")
        self.homeFrame.pack_propagate(False)

        self.parent_color = self.homeFrame.cget("fg_color")

        home_toolbar = uniwidgets.HomeToolbarBuilder(
            self.homeFrame, self.parent_color, self
        )

        ################################################################################################
        # Tools MENU: Opens new windows that does a specific utility and their functionalities
        ################################################################################################

        self.toolsFrame = ctk.CTkFrame(
            self.downFrame,
            corner_radius=0,
            height=122,
            border_color="#5e5e5e",
            border_width=1,
            fg_color=["#D2D2D2","#1E1E1E"],
        )

        self.toolsFrame.pack(fill="both", side="top")
        self.toolsFrame.pack_propagate(False)

        tools_toolbar = uniwidgets.ToolsBarBuilder(
            self.toolsFrame, self.parent_color, self
        )

        ################################################################################################
        # DATABASES MENU
        ################################################################################################

        self.databasesFrame = ctk.CTkFrame(
            self.downFrame,
            corner_radius=0,
            height=122,
            border_color="#5e5e5e",
            border_width=1,
            fg_color=["#D2D2D2","#1E1E1E"],
        )

        self.databasesFrame.pack(fill="both", side="top")
        self.databasesFrame.pack_propagate(False)

        ################################################################################################
        # PLOTS MENU: Shows plots of variables, objects, any selected (if it has plot options)
        ################################################################################################

        self.plotsFrame = ctk.CTkFrame(
            self.downFrame,
            corner_radius=0,
            height=122,
            border_color="#5e5e5e",
            border_width=1,
            fg_color=["#D2D2D2","#1E1E1E"],
        )
        self.plotsFrame.pack(fill="both", side="top")
        self.plotsFrame.pack_propagate(False)

        self.plotMngBtn = uniwidgets.VerticalButton(
            self.plotsFrame,
            image_path=r"icons\system\graphsettings.png",
            text="Plot\nManager",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.plotMngBtn.place(x=5, y=3)

        self.inspectorBtn = uniwidgets.VerticalButton(
            self.plotsFrame,
            image_path=r"icons\system\inspector.png",
            text="Graph\nInspector",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.inspectorBtn.place(x=70, y=3)

        self.plotThemeBtn = uniwidgets.VerticalButton(
            self.plotsFrame,
            image_path=r"icons\system\theme.png",
            text="Plot\nThemes",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.plotThemeBtn.place(x=137, y=3)

        self.vertical_sep_7 = ctk.CTkFrame(
            self.plotsFrame,
            bg_color="transparent",
            fg_color=["#D2D2D2","#1E1E1E"],
            width=2,
            height=75,
            corner_radius=0,
        )
        self.vertical_sep_7.place(x=199, y=7)

        ########## CUSTOM DROPDOWN MENU ##########
        self.customUtilitiesFrame = ctk.CTkFrame(
            self.plotsFrame,
            width=400,
            height=77,
            fg_color=self.plotsFrame.cget("fg_color"),
            border_color=["#5E5E5E","#D6D6D6"],
            border_width=1,
            corner_radius=1,
        )
        self.customUtilitiesFrame.place(x=209, y=5)
        self.customUtilitiesFrame.pack_propagate(False)

        ######### PLOTS 2D #########
        self.plots2d = ctk.CTkFrame(
            self.customUtilitiesFrame,
            width=395,
            height=71,
            fg_color=self.plotsFrame.cget("fg_color"),
            corner_radius=0,
        )
        self.customUtilitiesFrame.pack_propagate(False)

        self.graphBtn = uniwidgets.VerticalButton(
            self.plots2d,
            image_path=r"icons\system\graph.png",
            text="GraphBox",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.graphBtn.place(x=5, y=2)

        self.chartBtn = uniwidgets.VerticalButton(
            self.plots2d,
            image_path=r"icons\system\chart.png",
            text="Chart Graph",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.chartBtn.place(x=75, y=2)

        self.chartBtn = uniwidgets.VerticalButton(
            self.plots2d,
            image_path=r"icons\system\bargraph.png",
            text="Bar Graph",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.chartBtn.place(x=157, y=2)

        self.histoBtn = uniwidgets.VerticalButton(
            self.plots2d,
            image_path=r"icons\system\histogram.png",
            text="Histogram",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.histoBtn.place(x=227, y=2)

        ######### PLOTS 3D #########
        self.plots3d = ctk.CTkFrame(
            self.customUtilitiesFrame,
            width=395,
            height=71,
            fg_color=self.plotsFrame.cget("fg_color"),
            corner_radius=0,
        )
        self.customUtilitiesFrame.pack_propagate(False)

        self.graph3DBtn = uniwidgets.VerticalButton(
            self.plots3d,
            image_path=r"icons\system\surface.png",
            text="3D Surface",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.graph3DBtn.place(x=5, y=2)

        self.scatterBtn = uniwidgets.VerticalButton(
            self.plots3d,
            image_path=r"icons\system\scatter.png",
            text="3D Scatter",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.scatterBtn.place(x=82, y=2)

        self.wireframeBtn = uniwidgets.VerticalButton(
            self.plots3d,
            image_path=r"icons\system\wireframe.png",
            text="3D Wireframe",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.wireframeBtn.place(x=157, y=2)

        self.contourBtn = uniwidgets.VerticalButton(
            self.plots3d,
            image_path=r"icons\system\contour.png",
            text="3D Contour",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.contourBtn.place(x=247, y=2)

        ######### scientific #########
        self.scientific = ctk.CTkFrame(
            self.customUtilitiesFrame,
            width=395,
            height=71,
            fg_color=self.plotsFrame.cget("fg_color"),
            corner_radius=0,
        )
        self.customUtilitiesFrame.pack_propagate(False)

        self.heatmapBtn = uniwidgets.VerticalButton(
            self.scientific,
            image_path=r"icons\system\heatmap.png",
            text="Heatmap",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.heatmapBtn.place(x=5, y=2)

        self.polarBtn = uniwidgets.VerticalButton(
            self.scientific,
            image_path=r"icons\system\polar.png",
            text="Polar Plan",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.polarBtn.place(x=80, y=2)

        self.corrMATBtn = uniwidgets.VerticalButton(
            self.scientific,
            image_path=r"icons\system\corrmat.png",
            text="Corr. Matrix",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.corrMATBtn.place(x=155, y=2)

        self.upBtn1 = ctk.CTkButton(
            self.plots2d,
            text="",
            image=self.upArrow,
            width=50,
            height=20,
            corner_radius=0,
            fg_color="#1e1e1e",
            state=ctk.DISABLED,
        )
        self.upBtn1.place(x=345, y=2)
        self.downBtn1 = ctk.CTkButton(
            self.plots2d,
            text="",
            image=self.downArrow,
            width=50,
            height=20,
            corner_radius=0,
            hover_color="#001F39",
            fg_color="#004073",
            command=lambda: self.customDropDownFrameChanger(self.plots3d),
        )
        self.downBtn1.place(x=345, y=25)
        lab1Show = ctk.CTkLabel(
            self.plots2d,
            text="2D PLOTS",
            font=("Segoe UI", 10),
            fg_color="#004073",
            corner_radius=0,
            width=50,
            height=20,
            text_color="#CDCDCD",
        )
        lab1Show.place(x=345, y=48)
        self.upBtn2 = ctk.CTkButton(
            self.plots3d,
            text="",
            image=self.upArrow,
            width=50,
            height=20,
            corner_radius=0,
            hover_color="#001F39",
            fg_color="#004073",
            command=lambda: self.customDropDownFrameChanger(self.plots2d),
        )
        self.upBtn2.place(x=345, y=2)
        self.downBtn2 = ctk.CTkButton(
            self.plots3d,
            text="",
            image=self.downArrow,
            width=50,
            height=20,
            corner_radius=0,
            hover_color="#001F39",
            fg_color="#004073",
            command=lambda: self.customDropDownFrameChanger(self.scientific),
        )
        self.downBtn2.place(x=345, y=25)
        self.lab2Show = ctk.CTkLabel(
            self.plots3d,
            text="3D PLOTS",
            font=("Segoe UI", 10),
            fg_color="#004073",
            corner_radius=0,
            width=50,
            height=20,
            text_color="#CDCDCD",
        )
        self.lab2Show.place(x=345, y=48)
        self.upBtn3 = ctk.CTkButton(
            self.scientific,
            text="",
            image=self.upArrow,
            width=50,
            height=20,
            corner_radius=0,
            hover_color="#001F39",
            fg_color="#004073",
            command=lambda: self.customDropDownFrameChanger(self.plots3d),
        )
        self.upBtn3.place(x=345, y=2)
        self.downBtn3 = ctk.CTkButton(
            self.scientific,
            text="",
            image=self.downArrow,
            width=50,
            height=20,
            corner_radius=0,
            fg_color="#1e1e1e",
            state=ctk.DISABLED,
        )
        self.downBtn3.place(x=345, y=25)
        self.lab3Show = ctk.CTkLabel(
            self.scientific,
            text="SCI.",
            font=("Segoe UI", 10),
            fg_color="#004073",
            corner_radius=0,
            width=50,
            height=20,
            text_color="#CDCDCD",
        )
        self.lab3Show.place(x=345, y=48)
        self.customDropDownFrameChanger(self.plots2d)

        self.statsOverLayBtn = uniwidgets.HorizontalButton(
            self.plotsFrame,
            image_path=r"icons\system\stats.png",
            text="Stats Overlay",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.statsOverLayBtn.place(x=614, y=7)

        self.trashGraphBtn = uniwidgets.HorizontalButton(
            self.plotsFrame,
            image_path=r"icons\system\trash.png",
            text="Delete Graph",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.trashGraphBtn.place(x=614, y=37)

        ################################################################################################
        # DEBUG MENU: Debugging configuration settings
        ################################################################################################

        self.debugFrame = ctk.CTkFrame(
            self.downFrame,
            corner_radius=0,
            height=122,
            border_color="#5e5e5e",
            border_width=1,
            fg_color=["#D2D2D2","#1E1E1E"],
        )
        self.debugFrame.pack(fill="both", side="top")
        self.debugFrame.pack_propagate(False)

        self.debuggingBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\bug.png",
            text="Start\nDebugging",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.debuggingBtn.place(x=5, y=3)

        self.runNoBugBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\start.png",
            text="Run without\nDebugging",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.runNoBugBtn.place(x=82, y=5)

        self.attachBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\attach.png",
            text="Attach to\nSome Process",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.attachBtn.place(x=162, y=5)

        self.compileBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\compile.png",
            text="Compile\nCode",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.compileBtn.place(x=253, y=5)

        self.stopBugBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\stop.png",
            text="Stop\nDebugging",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.stopBugBtn.place(x=315, y=5)

        self.restartBugBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\restart.png",
            text="Restart\nDebugging",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.restartBugBtn.place(x=392, y=5)

        self.deatBugBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\deattach.png",
            text="Detach\nDebugger",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.deatBugBtn.place(x=470, y=5)

        self.vertical_sep_8 = ctk.CTkFrame(
            self.debugFrame,
            bg_color="transparent",
            fg_color=["#727272","#3E3E3E"],
            width=2,
            height=75,
            corner_radius=0,
        )
        self.vertical_sep_8.place(x=543, y=7)

        ######### UPON DEBUGGING TOOLS #########
        self.debuggingToolsFrame = ctk.CTkFrame(
            self.debugFrame,
            fg_color=self.debugFrame.cget("fg_color"),
            width=162,
            height=35,
            border_color="#5e5e5e",
            border_width=1,
            corner_radius=2,
        )
        self.debuggingToolsFrame.place(x=553, y=7)
        self.stepToBtn = ctk.CTkButton(
            self.debuggingToolsFrame,
            text="",
            image=self.stepTo,
            width=20,
            height=20,
            fg_color=self.debuggingToolsFrame.cget("fg_color"),
            corner_radius=0,
        )
        self.stepToBtn.place(x=2, y=2)

        self.stepOutBtn = ctk.CTkButton(
            self.debuggingToolsFrame,
            text="",
            image=self.stepOut,
            width=20,
            height=20,
            fg_color=self.debuggingToolsFrame.cget("fg_color"),
            corner_radius=0,
        )
        self.stepOutBtn.place(x=34, y=2)

        self.stepOverBtn = ctk.CTkButton(
            self.debuggingToolsFrame,
            text="",
            image=self.stepOver,
            width=20,
            height=20,
            fg_color=self.debuggingToolsFrame.cget("fg_color"),
            corner_radius=0,
        )
        self.stepOverBtn.place(x=66, y=2)

        self.runToCursorBtn = ctk.CTkButton(
            self.debuggingToolsFrame,
            text="",
            image=self.toggleCursor,
            width=20,
            height=20,
            fg_color=self.debuggingToolsFrame.cget("fg_color"),
            corner_radius=0,
        )
        self.runToCursorBtn.place(x=130, y=2)

        self.runToCursorBtn = ctk.CTkButton(
            self.debuggingToolsFrame,
            text="",
            image=self.runToCursor,
            width=20,
            height=20,
            fg_color=self.debuggingToolsFrame.cget("fg_color"),
            corner_radius=0,
        )
        self.runToCursorBtn.place(x=98, y=2)

        self.watchBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\watch.png",
            text="Watch\nWindow",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.watchBtn.place(x=730, y=5)

        self.performanceBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\cpu.png",
            text="Performance\nOptimization",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.performanceBtn.place(x=790, y=5)

        self.memoryBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\memory.png",
            text="Memory\nProfiler",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.memoryBtn.place(x=875, y=5)

        self.vertical_sep_9 = ctk.CTkFrame(
            self.debugFrame,
            bg_color="transparent",
            fg_color=["#727272","#3F3F3F"],
            width=2,
            height=75,
            corner_radius=0,
        )
        self.vertical_sep_9.place(x=938, y=7)

        self.verifyBtn = uniwidgets.VerticalButton(
            self.debugFrame,
            image_path=r"icons\system\verify.png",
            text="Verify Code\nSafety",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.verifyBtn.place(x=948, y=5)

        ################################################################################################
        # TERMINAL MENU
        ################################################################################################

        self.terminalFrame = ctk.CTkFrame(
            self.downFrame,
            corner_radius=0,
            height=122,
            border_color="#5e5e5e",
            border_width=1,
            fg_color=["#D2D2D2","#1E1E1E"],
        )
        self.terminalFrame.pack(fill="both", side="top")
        self.terminalFrame.pack_propagate(False)

        self.runTaskBtn = uniwidgets.VerticalButton(
            self.terminalFrame,
            image_path=r"icons\system\task.png",
            text="Run Task",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.runTaskBtn.place(x=5, y=5)

        self.buildBtn = uniwidgets.VerticalButton(
            self.terminalFrame,
            image_path=r"icons\system\build.png",
            text="Build Task",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.buildBtn.place(x=75, y=5)

        self.fileMngBtn = uniwidgets.VerticalButton(
            self.terminalFrame,
            image_path=r"icons\system\fileMng.png",
            text="Run File\nManager",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.fileMngBtn.place(x=150, y=5)

        self.dayDreamBtn = uniwidgets.VerticalButton(
            self.terminalFrame,
            image_path=r"icons\system\daydream.png",
            text="DayDream\nTerminal",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.dayDreamBtn.place(x=220, y=5)

        ################################################################################################
        # HELP MENU
        ################################################################################################

        self.helpFrame = ctk.CTkFrame(
            self.downFrame,
            corner_radius=0,
            height=122,
            border_color="#5e5e5e",
            border_width=1,
            fg_color=["#D2D2D2","#1E1E1E"],
        )
        self.helpFrame.pack(fill="both", side="top")
        self.helpFrame.pack_propagate(False)

        self.docBtn = uniwidgets.VerticalButton(
            self.helpFrame,
            image_path=r"icons\system\documentation.png",
            text="Documentation",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.docBtn.place(x=5, y=5)

        self.feedBtn = uniwidgets.VerticalButton(
            self.helpFrame,
            image_path=r"icons\system\feedback.png",
            text="Feedback",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.feedBtn.place(x=106, y=5)

        self.hBtn = uniwidgets.VerticalButton(
            self.helpFrame,
            image_path=r"icons\system\help.png",
            text="Show Help",
            font=("Segoe UI", 12),
            fg_color=self.parent_color,
            hover_color="#3a3a3a",
        )
        self.hBtn.place(x=176, y=5)

        self.allTabs = [
            self.homeFrame,
            self.toolsFrame,
            self.databasesFrame,
            self.plotsFrame,
            self.debugFrame,
            self.terminalFrame,
            self.helpFrame,
        ]

        self.show_tab(self.homeFrame, self.homeBtn)

        #################################################################################################
        # STATUS BAR
        #################################################################################################

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

        #################################################################################################
        # SERVICES LEFTMOST BAR
        #################################################################################################
        self.shell_frame = None

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
            command=self.open_current_file,
        )
        self.open_button.pack(pady=5)
        uniwidgets.ToolTip(self.open_button, "Opens a file")

        self.search_button = ctk.CTkButton(
            self.services_bar,
            text="",
            image=self.search_photo,
            width=36,
            height=36,
            corner_radius=5,
            fg_color=self.services_bar.cget("fg_color"),
            command=self.open_search,
        )
        self.search_button.pack(pady=5)
        uniwidgets.ToolTip(
            self.search_button, "Searches inside the file for a specific key"
        )

        self.save_button = ctk.CTkButton(
            self.services_bar,
            text="",
            image=self.save_photo,
            width=36,
            height=36,
            corner_radius=5,
            fg_color=self.services_bar.cget("fg_color"),
            command=self.save_file,
        )
        self.save_button.pack(pady=5)
        uniwidgets.ToolTip(self.save_button, "Saves the current loaded workspace file")

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
        uniwidgets.ToolTip(self.user_button, "Show user's account")

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
        uniwidgets.ToolTip(self.settings_button, "Show IDE settings and preferences")

        #################################################################################################
        # LEFT SIDEBAR FRAME
        #################################################################################################

        self.sidebar = ctk.CTkTabview(
            self.window,
            fg_color=["#EBEBEB","#292929"],
            width=360,
            corner_radius=1,
            anchor="nw",
            border_width=1,
            border_color="#5E5E5E",
            segmented_button_selected_color=["#C2C2C2","#1E1E1E"],
            segmented_button_selected_hover_color=["#696969","#1E1E1E"],
            segmented_button_padx=7,
            text_color=["#1E1E1E","#C2C2C2"]
        )
        self.sidebar.pack_propagate(False)
        self.sidebar.pack(side="left", fill="y")

        self.fileExplorer = self.sidebar.add("Solution Explorer")
        self.properties = self.sidebar.add("Properties")
        self.solution = self.sidebar.add("Debugger")

        #################################################################################################
        # MAIN EDITOR AREA
        #################################################################################################
        self.editor_frame = ctk.CTkFrame(self.window, corner_radius=0)
        self.editor_frame.pack(fill="both", expand=True)

        # --- FRAMES ---
        self.upper_frame = ctk.CTkFrame(self.editor_frame, corner_radius=0)
        self.upper_frame.pack(fill="both", expand = True)

        self.middle_frame = ctk.CTkFrame(self.editor_frame, corner_radius=0)
        self.middle_frame.place_forget()

        # --- CURRENT PATH ---
        thisCurrentWd = os.getcwd()
        objectLabel = thisCurrentWd.split("\\")
        showObject = "  "
        for obj in objectLabel:
            showObject = showObject + obj + "> "

        showObjectLabel = ctk.CTkLabel(self.upper_frame,
                                       corner_radius=0,
                                       text="",
                                       compound="left",
                                       anchor="w",
                                       height=28,
                                       bg_color=["#FFFFFF","#1F1F1F"],
                                       font=("Consolas",13),
                                       text_color=["#1F1F1F","#FFFFFF"])
        showObjectLabel.pack(fill='x',side="top")
        showObjectLabel.configure(text=showObject)

        # --- TEXTBOX ---
        self.text_editor = Editor(self.upper_frame,
                              language=Languages.C,
                              font=("Consolas",13),
                              showpath=True,
                              darkmode=True,
                              uifont=("Segoe UI",14))
        self.text_editor.pack(expand=0.9, fill='both')

        #################################################################################################
        # FILE EXPLORER TREEVIEW
        #################################################################################################
        self.label_workspace = ctk.CTkLabel(
            self.fileExplorer,
            text="CURRENT WORKSPACE",
            font=("Segoe UI", 12),
            fg_color=self.fileExplorer.cget("fg_color"),
            width=40,
        )
        self.label_workspace.place(x=10, y=10)

        self.loadWorkspaceBtn = ctk.CTkButton(
            self.fileExplorer,
            text="",
            image=AppIcons.create_padded_icon(r"icons\system\load.png"),
            width=20,
            fg_color="transparent",
            corner_radius=3,
            anchor="center",
        )
        self.loadWorkspaceBtn.place(x=310,y=9)

        self.refreshWorkspaceBtn = ctk.CTkButton(
            self.fileExplorer,
            text="",
            image=AppIcons.create_padded_icon(r"icons\system\refresh.png"),
            width=8,
            height=8,
            fg_color="transparent",
            corner_radius=3,
            anchor="center",
        )
        self.refreshWorkspaceBtn.place(x=280,y=9)

        self.horizontal_line = ctk.CTkFrame(
            self.fileExplorer,
            width=340,
            height=1,
            border_width=1,
            fg_color=["#292929","#ADADAD"],
        )
        self.horizontal_line.place(x=8, y=40)

        #################################################################################################
        # PROPERTIES EXPLORER
        #################################################################################################
        self.codePropertiesLabel = ctk.CTkLabel(
            self.properties,
            text="Code Properties",
            width=60,
            font=("Segoe UI",12),
            justify="left",
            anchor="w"
        )
        self.codePropertiesLabel.pack(padx=20,pady=(3,0),anchor="w")
        self.properties_table = CTkTable.CTkTable(self.properties,
                                                  row=9,
                                                  column=2,
                                                  padx=0,
                                                  pady=0,
                                                  border_width=1,
                                                  border_color="#808080",
                                                  corner_radius=0,
                                                  font=("Segoe UI",12),
                                                  header_color=["#C3C3C3","#2D2D2D"],
                                                  colors=[self.properties.cget("fg_color"),
                                                          self.properties.cget("fg_color")],
                                                  width=160)
        self.properties_table.pack(padx=10,pady=5)
        self.properties_table.insert(row=0,column=0,value="Property")
        self.properties_table.insert(row=0,column=1,value="Value")
        self.properties_table.insert(row=1,column=0,value="Classes")
        self.properties_table.insert(row=2,column=0,value="Functions")
        self.properties_table.insert(row=3,column=0,value="Variables")
        self.properties_table.insert(row=4,column=0,value="Decorations")
        self.properties_table.insert(row=5,column=0,value="Imports")
        self.properties_table.insert(row=6,column=0,value="Exceptions")
        self.properties_table.insert(row=7,column=0,value="Magic Methods")
        self.properties_table.insert(row=8,column=0,value="Awaitables")

        self.solutionPropertiesLabel = ctk.CTkLabel(
            self.properties,
            text="Solution Properties",
            width=60,
            font=("Segoe UI",12),
            justify="left",
            anchor="w"
        )
        self.solutionPropertiesLabel.pack(padx=20,pady=(3,0),anchor="w")
        self.solution_table = CTkTable.CTkTable(self.properties,
                                                  row=5,
                                                  column=2,
                                                  padx=0,
                                                  pady=0,
                                                  border_width=1,
                                                  border_color="#808080",
                                                  corner_radius=0,
                                                  font=("Segoe UI",12),
                                                  header_color=["#C3C3C3","#2D2D2D"],
                                                  colors=[self.properties.cget("fg_color"),
                                                          self.properties.cget("fg_color")],
                                                  width=160)
        self.solution_table.pack(padx=10,pady=5)
        self.solution_table.insert(row=0,column=0,value="Solution Name")
        self.solution_table.insert(row=1,column=0,value="Output Type")
        self.solution_table.insert(row=2,column=0,value="Architecture")
        self.solution_table.insert(row=3,column=0,value="Operating System")
        self.solution_table.insert(row=4,column=0,value="Dependencies")

        #################################################################################################
        # BINDINGS
        #################################################################################################
        self.window.bind("<Control-t>", self.open_terminal)
        self.window.bind("<Control-m>", self.open_shell)

    def show_tab(self, frame_to_show, active_button):
        for frame in self.allTabs:
            frame.pack_forget()

        if hasattr(frame_to_show, "initialize"):
            frame_to_show.initialize()

        frame_to_show.pack(fill="both", side="top")
        frame_to_show.pack_propagate(False)

        tabButtons = [
            self.homeBtn,
            self.toolsBtn,
            self.plotsBtn,
            self.databasesBtn,
            self.debugBtn,
            self.terminalBtn,
            self.helpBtn,
        ]

        for btn in tabButtons:
            btn.configure(fg_color="#004073")

    def customDropDownFrameChanger(self, frame_to_show):
        for f in [self.plots2d, self.plots3d, self.scientific]:
            f.place_forget()
        frame_to_show.place(x=2, y=2)

    def open_terminal(self, event=None):
        subprocess.Popen("start cmd", shell=True)

    def open_search(self, event=None):
        search_window = search_menu.KeywordSearch(
            self, self.text_editor, status_button=self.status_button
        )
        search_window.show()

    def save_file(self, event=None):
        save_file = save_menu.SaveFile(
            self, workspace_container=self.workspace, status_button=self.status_button
        )
        save_file.show()

    def open_current_file(main_app):
        if main_app.status_button:
            main_app.status_button.configure(text="Opening file")

        current_file = filedialog.askopenfilename(title="Select an existing file")
        if not current_file:
            return

        try:
            with open(current_file, "r", encoding="utf-8") as f:
                content = f.read()

            main_app.text_editor.content.delete("1.0", "end")
            main_app.text_editor.content.insert("1.0", content)
            if main_app.status_button:
                main_app.status_button.configure(text=f"File {current_file} opened")

        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")
            if main_app.status_button:
                main_app.status_button.configure(text="Operation Failed")

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
        import widgets.command_window as command_window

        if self.shell_frame is None:
            self.upper_frame.place(relx=0, rely=0, relwidth=1, relheight=0.70)
            self.middle_frame.place(relx=0, rely=0.70, relwidth=1, relheight=0.30)

            self.shell_frame = command_window.PromptXShell(main_app=self.middle_frame)
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

#####################################################################################################
# RUN AND MODIFY
#####################################################################################################
if __name__ == "__main__":
    app = App()
    threading.Thread(target=app.run()).start()
