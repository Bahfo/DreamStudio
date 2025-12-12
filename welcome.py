import widgets.universal_widgets as uniwidgets
from CTkMenuBar import CTkMenuBar
from PIL import Image, ImageTk
import customtkinter as ctk
import tkinter as tk
import ctypes
import json

SW_MINIMIZE = 6

user32 = ctypes.windll.user32

patch_notes = """For full patch notes, see the website's\nPatch Notes in Detail.
● First version of DreamStudio ALPHA is here!
● You can start a new project by clicking\non (New Build).
● Access built-in templates by clicking\non (Open Build).
● Builds are project templates which\ncontains Python Virtual Environment,\nplus all the needs for full Python project.
"""


class WelcomeWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.iconbitmap("")
        self.title("Welcome to DreamStudio")
        self.geometry("800x500+420+200")
        self.attributes("-topmost", True)
        self.state("withdrawn")
        self.resizable(False, False)
        self.overrideredirect(True)

        self.mode = ctk.get_appearance_mode()

        ###############################
        # TITLE BAR
        ###############################
        self.titleBar = ctk.CTkFrame(
            self, border_width=0, corner_radius=0, height=40, fg_color="transparent"
        )
        self.titleBar.pack(fill="x", side="top")

        self.icon = ctk.CTkLabel(self.titleBar, corner_radius=0, text="DS", width=14,
                                 font=("Segoe UI Bold",13),text_color="#0062B1",justify="center")
        self.icon.pack(side="left", padx=(10,0))

        self.title_label = ctk.CTkLabel(
            self.titleBar,
            text="Welcome to DreamStudio",
            font=("Arial", 12),
        )
        self.title_label.pack(side="left", padx=10)

        # Buttons
        self.exitBtn = ctk.CTkButton(
            self.titleBar,
            text="✕",
            border_color="#5E5E5E",
            border_width=1,
            corner_radius=0,
            width=20,
            command=self.close,
            fg_color=self.titleBar.cget("fg_color"),
            hover_color="#EB0000"
        )
        self.exitBtn.pack(side="right", padx=1)

        self.minBtn = ctk.CTkButton(
            self.titleBar,
            text="—",
            border_color="#5E5E5E",
            border_width=1,
            corner_radius=0,
            width=20,
            command=self.minimize_window,
            fg_color=self.titleBar.cget("fg_color"),
            hover_color="#00316D"
        )
        self.minBtn.pack(side="right", padx=1)

        # Drag
        self.offset_x = 0
        self.offset_y = 0

        for area in (self.titleBar, self.title_label):
            area.bind("<Button-1>", self.click_titleBar)
            area.bind("<B1-Motion>", self.drag_window)

        ###############################
        # LEFT FRAME
        ###############################
        self.leftFrame = ctk.CTkFrame(
            self,
            border_color="#5E5E5E",
            border_width=1,
            width=250,
            corner_radius=0,
        )
        self.leftFrame.pack(side="left", fill="y")
        self.leftFrame.pack_propagate(False)

        menubar = CTkMenuBar(self,)

        file_menu = menubar.add_cascade("File")
        builds_menu = menubar.add_cascade("Builds")
        extensions_menu = menubar.add_cascade("Extensions")
        Repositories_menu = menubar.add_cascade("Repositories")
        Help_menu = menubar.add_cascade("Help")

        file_menu.configure(corner_radius=0)
        builds_menu.configure(corner_radius=0)
        extensions_menu.configure(corner_radius=0)
        Repositories_menu.configure(corner_radius=0)
        Help_menu.configure(corner_radius=0)

        self.newsTitle = ctk.CTkLabel(
            self.leftFrame,
            text="What's New?",
            font=("Segoe UI",18),
            justify="left",
            text_color="#0062B1"
        )
        self.newsTitle.pack(side="top",padx=10,pady=10,anchor="w")

        self.version = ctk.CTkLabel(
            self.leftFrame,
            text="Version 1.0.0",
            font=("Segoe UI",11),
            justify="left",
            anchor="nw"
        )
        self.version.pack(side="top",anchor="w",padx=10)

        self.newsLabel = ctk.CTkTextbox(
            self.leftFrame,
            font=("Segoe UI",12),
            fg_color=self.leftFrame.cget("fg_color"),
            width=230,
            height=300
        )
        self.newsLabel.insert("0.0", f"{patch_notes}")
        self.newsLabel.configure(state="disabled")

        self.newsLabel.configure(spacing1=2, spacing2=4, spacing3=2)
        self.newsLabel.pack(side="top",anchor="w",padx=10)

        ###############################
        # RIGHT FRAME
        ###############################
        self.rightFrame = ctk.CTkFrame(
            self,
            border_color="#5E5E5E",
            border_width=1,
            width=550,
            corner_radius=0,
        )
        self.rightFrame.pack(side="right", fill="y")

        self.welcomeLabel = ctk.CTkLabel(
            self.rightFrame, 
            text="Welcome to DreamStudio",
            font=("Segoe UI",20),
            width=100,
            justify="center"
        )
        self.welcomeLabel.place(x=160,y=120)

        self.explanationLabel = ctk.CTkLabel(
            self.rightFrame,
            text="""Click on 'New' to start a project from scratch,
or use a generated template by clicking on 'Template Builds'""",
            width=200,
            font=("Segoe UI",12),
            justify="center"
        )
        self.explanationLabel.place(x=115,y=160)

        self.newProjectBtn = uniwidgets.VerticalButton(
            self.rightFrame,
            image_path=r"icons\system\newvar.png",
            text="New Build",
        )
        self.newProjectBtn.place(x=195,y=230)

        self.newProjectBtn = uniwidgets.VerticalButton(
            self.rightFrame,
            image_path=r"icons\system\folder.ico",
            text=" Template "
        )
        self.newProjectBtn.place(x=275,y=230)

        self.feedbackLabel = ctk.CTkLabel(
            self.rightFrame,
            font=("Segoe UI",12),
            text="Got any questions?",
            width=50
        )
        self.feedbackLabel.place(x=10,y=410)

        self.feedbackLink = uniwidgets.LinkLabel(
            self.rightFrame,
            width=100,
            height=25,
            link_color="#386CBF",
            after_link_color="#814972",
            font=("Segoe UI",12),
            text="Visit our Website",
            border_width=0,
            corner_radius=0
        )
        self.feedbackLink.place(x=115,y=410)

    def click_titleBar(self, event):
        self.offset_x = event.x
        self.offset_y = event.y

    def drag_window(self, event):
        x = self.winfo_pointerx() - self.offset_x
        y = self.winfo_pointery() - self.offset_y
        self.geometry(f"+{x}+{y}")

    def minsize(self):
        hwnd = user32.GetForegroundWindow()
        user32.ShowWindow(hwnd, SW_MINIMIZE)

    def close(self):
        self.deiconify
        self.destroy()

    def minimize_window(self):
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        ctypes.windll.user32.ShowWindow(hwnd, 11)

    def run(self, event=None):
        self.mainloop()

class ChoosingBuild(ctk.CTkToplevel):
    def __init__(self):
        pass

    def show(self):
        pass

class TemplateBuilds(ctk.CTkToplevel):
    def __init__(self):
        pass

    def show(self):
        pass

if __name__ == "__main__":
    app = WelcomeWindow()
    app.run()
