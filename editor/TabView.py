import os
import pathlib
from PIL import Image
import customtkinter as ctk
from backend.run import run_config
import editor.menu_builders as uniwidgets
from editor.utils.treeview import FileTree


# --- Global Configuration ---
number_of_files: int = 4

project_image = ctk.CTkImage(
    light_image=Image.open(r"assets/system/projectType.png"),
    dark_image=Image.open(r"assets/system/projectType.png"),
    size=(16, 16),
)


class TabView:

    def __init__(
        self,
        master,
        path,
        width: int = 370,
        height: int = 500,
        corner_radius=0,
        border_width=1,
        border_color=None,
        background_corner_colors=None,
        overwrite_preferred_drawing_method=None,
        **kwargs,
    ):

        # --- Main Frame ---
        self.mainFrame = ctk.CTkFrame(
            master=master,
            width=width,
            height=height,
            corner_radius=corner_radius,
            bg_color=["#F5F5F5", "#1E1E1E"],
            fg_color=["#F5F5F5", "#1E1E1E"],
            border_width=border_width,
            border_color=border_color,
            background_corner_colors=background_corner_colors,
            overwrite_preferred_drawing_method=overwrite_preferred_drawing_method,
        )
        self.mainFrame.pack_propagate(False)

        # ==============================
        # Solution Explorer Frame
        # ==============================

        self.solutionExplorerFrame = ctk.CTkFrame(
            self.mainFrame,
            width=width,
            height=height,
            border_color=border_color,
            border_width=1,
            fg_color=["#F5F5F5", "#1E1E1E"],
            corner_radius=0,
        )

        self.explnLabel = ctk.CTkLabel(
            self.solutionExplorerFrame,
            text=f"  Solution: {number_of_files} files found",
            font=("inter", 12),
            fg_color=["#F5F5F5", "#1E1E1E"],
            width=width - 30,
            image=project_image,
            compound="left",
            height=18,
            justify="left",
            anchor="w",
            text_color=["#1E1E1E", "#F5F5F5"],
        )
        self.explnLabel.place(x=5, y=5)

        self.gadgetsFrame = ctk.CTkFrame(
            self.solutionExplorerFrame,
            width=width,
            height=26,
            fg_color=["#F5F5F5", "#1E1E1E"],
            border_width=1,
            corner_radius=0,
            border_color=["#C8C8C8", "#444444"],
        )
        self.gadgetsFrame.place(x=0, y=26)

        # --- Gadget Buttons ---
        self.newFileBtn = uniwidgets.SmallButton(
            self.gadgetsFrame, image_path=r"assets/system/newvar.png"
        )
        self.newFileBtn.place(x=2, y=2)

        self.newDirBtn = uniwidgets.SmallButton(
            self.gadgetsFrame, image_path=r"assets/system/newDir.png"
        )
        self.newDirBtn.place(x=26, y=2)

        self.refreshBtn = uniwidgets.SmallButton(
            self.gadgetsFrame, image_path=r"assets/system/refreshDir.png"
        )
        self.refreshBtn.place(x=50, y=2)

        self.collapseBtn = uniwidgets.SmallButton(
            self.gadgetsFrame, image_path=r"assets/system/collapse.png"
        )
        self.collapseBtn.place(x=74, y=2)

        self.searchBar = ctk.CTkEntry(
            self.gadgetsFrame,
            fg_color=["#F5F5F5", "#1E1E1E"],
            border_color=["#C8C8C8", "#444444"],
            border_width=1,
            height=20,
            font=("inter", 12),
            width=250,
            corner_radius=0,
            placeholder_text="🔍    Search Solution Explorer",
        )
        self.searchBar.place(x=(width - 252), y=2)

        self.treeView = FileTree(
            master=self.solutionExplorerFrame,
            width=350,
            height=530,
            root_path=path,
        )
        self.treeView.place(x=5, y=60)

        # ==============================
        # Properties Frame
        # ==============================

        self.propertiesFrame = ctk.CTkFrame(
            self.mainFrame,
            width=width,
            height=height,
            border_width=border_width,
            border_color=border_color,
            fg_color=["#F5F5F5", "#1E1E1E"],
            corner_radius=0,
        )
        self.propertiesFrame.pack_propagate(False)

        # ==============================
        # Run and Debug Frame
        # ==============================

        self.runDebug = ctk.CTkFrame(
            self.mainFrame,
            width=width,
            height=height,
            border_width=border_width,
            border_color=border_color,
            fg_color=["#F5F5F5", "#1E1E1E"],
            corner_radius=0,
        )
        self.runDebug.pack_propagate(False)

        label1 = ctk.CTkLabel(
            self.runDebug,
            width=100,
            height=30,
            corner_radius=0,
            fg_color=self.runDebug.cget("fg_color"),
            text_color=["#1E1E1E", "#FFFFFF"],
            text="Run Options",
            font=("inter", 12),
            anchor="w",
        )
        label1.place(x=15, y=10)

        runBtn = ctk.CTkButton(
            self.runDebug,
            width=340,
            height=25,
            corner_radius=5,
            fg_color=["#005BA5", "#004073"],
            text_color="#FFFFFF",
            text="Start Running Code",
            font=("inter", 13),
            hover_color="#005398",
            border_width=0,
            command=self.run_script,
        )
        runBtn.place(x=15, y=40)

        configBtn = ctk.CTkButton(
            self.runDebug,
            width=340,
            height=25,
            corner_radius=5,
            fg_color=["#005BA5", "#004073"],
            text_color="#FFFFFF",
            text="Show Run Configurations",
            font=("inter", 13),
            hover_color="#005398",
            border_width=0,
        )
        configBtn.place(x=15, y=75)

        label2 = ctk.CTkLabel(
            self.runDebug,
            width=100,
            height=30,
            corner_radius=0,
            fg_color=self.runDebug.cget("fg_color"),
            text_color=["#1E1E1E", "#FFFFFF"],
            text="Debug Options",
            font=("inter", 12),
            anchor="w",
        )
        label2.place(x=15, y=110)

        debugBtn = ctk.CTkButton(
            self.runDebug,
            width=340,
            height=25,
            corner_radius=5,
            fg_color=["#005BA5", "#004073"],
            text_color="#FFFFFF",
            text="Debug Current Code File",
            font=("inter", 13),
            hover_color="#005398",
            border_width=0,
        )
        debugBtn.place(x=15, y=140)

        # ==============================
        # Tab Changer
        # ==============================

        self.tabChanger = ctk.CTkFrame(
            master=self.mainFrame,
            width=width,
            height=(height / 16),
            corner_radius=0,
            border_width=0,
            fg_color=["#E3E3E3", "#2B2B2B"],
            bg_color=["#E3E3E3", "#2B2B2B"],
        )
        self.tabChanger.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0)

        self.slnExplrBtn = ctk.CTkButton(
            master=self.tabChanger,
            width=45,
            height=(height / 17),
            text="Solution Explorer ",
            text_color=["#262626", "#E3E3E3"],
            corner_radius=6,
            hover=False,
            border_width=0,
            font=("inter", 12),
            fg_color=["#F5F5F5", "#1E1E1E"],
        )
        self.slnExplrBtn.place(x=8, y=-5)

        self.propertiesBtn = ctk.CTkButton(
            master=self.tabChanger,
            width=45,
            height=(height / 17),
            text="    Properties    ",
            text_color=["#262626", "#E3E3E3"],
            corner_radius=6,
            hover=False,
            border_width=0,
            font=("inter", 12),
            fg_color=["#F5F5F5", "#1E1E1E"],
        )
        self.propertiesBtn.place(x=125, y=-5)

        self.runDebugBtn = ctk.CTkButton(
            master=self.tabChanger,
            width=45,
            height=(height / 17),
            text="  Run and Debug   ",
            text_color=["#262626", "#E3E3E3"],
            corner_radius=6,
            hover=False,
            border_width=0,
            font=("inter", 12),
            fg_color=["#F5F5F5", "#1E1E1E"],
        )
        self.runDebugBtn.place(x=229, y=-5)

        # --- Button Commands ---
        self.slnExplrBtn.configure(
            command=lambda: self.show_side_frame(
                self.solutionExplorerFrame, self.slnExplrBtn
            )
        )

        self.propertiesBtn.configure(
            command=lambda: self.show_side_frame(
                self.propertiesFrame, self.propertiesBtn
            )
        )

        self.runDebugBtn.configure(
            command=lambda: self.show_side_frame(self.runDebug, self.runDebugBtn)
        )

        # --- Initial State ---
        self.show_side_frame(self.solutionExplorerFrame, self.slnExplrBtn)
        self.mainFrame.place(x=0, y=0)

    def show_side_frame(self, frame, active_btn):

        for f in (self.solutionExplorerFrame, self.propertiesFrame, self.runDebug):
            f.pack_forget()

        for b in (self.slnExplrBtn, self.propertiesBtn, self.runDebugBtn):
            b.configure(fg_color=["#E3E3E3", "#2B2B2B"])
            b.configure(border_color=["#E3E3E3", "#2B2B2B"])

        frame.pack(fill="both", expand=True)

        active_btn.configure(fg_color=["#F5F5F5", "#1E1E1E"])
        active_btn.configure(border_color=["#A8A8A8", "#555555"])

    def run_script(self):
        shell_window = run_config.ShellWindow()
        run_class = run_config.RunFile(
            code_to_run="""print("Hello")""",
            arguments=["python", r"C:/Users/Bahaa/Desktop"],
            ShellWindow=shell_window,
        ).run()
