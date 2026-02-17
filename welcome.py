from dreamstudio.utils.largeButton import LargeButton
from dreamstudio.utils.linkLabel import LinkLabel
from dreamstudio.utils.verticalButton import VerticalButton
from CTkMenuBar import CTkMenuBar
import customtkinter as ctk
from PIL import Image
import ctypes

SW_MINIMIZE = 6

user32 = ctypes.windll.user32

patch_notes = """For full patch notes, see the website's\nPatch Notes in Detail.
● First version of DreamStudio ALPHA is here!
● You can start a new project by clicking\non (New Build).
● Access built-in templates by clicking\non (Open Build).
● Builds are project templates which\ncontains Python Virtual Environment,\nplus all the needs for full Python project.
"""

ctk.set_appearance_mode("system")

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
            border_width=0,
            corner_radius=0,
            width=20,
            command=self.close,
            fg_color=["#EBEBEB","#1E1E1E"],
            text_color=["#1E1E1E","#EBEBEB"])

        self.exitBtn.pack(side="right", padx=1)

        self.minBtn = ctk.CTkButton(
            self.titleBar,
            text="—",
            border_width=0,
            corner_radius=0,
            width=20,
            command=self.minimize_window,
            fg_color=["#EBEBEB","#1E1E1E"],
            text_color=["#1E1E1E","#EBEBEB"])

        self.minBtn.pack(side="right", padx=1)

        self.minBtn.bind("<Enter>", lambda e: self.on_enter(self.minBtn))
        self.minBtn.bind("<Leave>", lambda e: self.on_leave(self.minBtn))
        self.exitBtn.bind("<Enter>", lambda e: self.on_enter(self.exitBtn))
        self.exitBtn.bind("<Leave>", lambda e: self.on_leave(self.exitBtn))

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

        self.newProjectBtn = VerticalButton(
            self.rightFrame,
            image_path=r"icons\system\newvar.png",
            text="New Build",
            command=self.select_project
        )
        self.newProjectBtn.place(x=195,y=230)

        self.newProjectBtn = VerticalButton(
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

        self.feedbackLink = LinkLabel(
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

    def select_project(self):
        self.withdraw()
        projectSelection = ChoosingBuild(self)

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

    def on_enter(self, btn: ctk.CTkButton):
        btn.configure(border_width=1, border_color="#818181")

    def on_leave(self, btn: ctk.CTkButton):
        btn.configure(border_width=0)

    def close(self):
        self.deiconify
        self.destroy()

    def minimize_window(self):
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        ctypes.windll.user32.ShowWindow(hwnd, 11)

    def run(self, event=None):
        self.mainloop()

class ChoosingBuild(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Choose Project")
        self.geometry("1000x600")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.state("zoomed")

        self.leftFrame = ctk.CTkFrame(self,
                                      width=300,
                                      height=600,
                                      corner_radius=0,
                                      fg_color=["#DBDBDB","#2B2B2B"],
                                      border_width=1,
                                      border_color=["#989898","#767676"])
        self.leftFrame.place(x=0, y=0, relheight=1)

        self.explnBtn1 = ctk.CTkLabel(self.leftFrame,
                                      text="Create a New Project",
                                      corner_radius=0,
                                      font=("Segoe UI",20),
                                      fg_color=["#DBDBDB","#2B2B2B"],
                                      anchor="w",
                                      justify="left",
                                      width=280,
                                      height=30)
        self.explnBtn1.place(x=10, y=20)

        self.explnBtn2 = ctk.CTkLabel(self.leftFrame,
                                      text="""Select one of the following supported languages.
Not finding what you are looking for? Go to
extensions tab and download from the marketplace.""",
                                      corner_radius=0,
                                      anchor="w",
                                      font=("Segoe UI",11),
                                      fg_color=["#DBDBDB","#2B2B2B"],
                                      text_color=["#1E1E1E","#F1F1F1"],
                                      width=280,
                                      justify="left",
                                      height=60)
        self.explnBtn2.place(x=10, y=65)

        self.PythonProjectBtn = ctk.CTkButton(self.leftFrame,
                                              text="Python Project Types",
                                              corner_radius=0,
                                              font=("Segoe UI", 13),
                                              text_color=["#1E1E1E","#F1F1F1"],
                                              width=284,
                                              anchor="w",
                                              height=30,
                                              border_width=1,
                                              fg_color=["#F1F1F1","#2B2B2B"])
        self.PythonProjectBtn.place(x=8, y=130)

        self.CProjectBtn = ctk.CTkButton(self.leftFrame,
                                         text="C Project Types",
                                         corner_radius=0,
                                         text_color=["#1E1E1E","#F1F1F1"],
                                         width=284,
                                         height=30,
                                         anchor="w",
                                         font=("Segoe UI", 13),
                                         border_width=1,
                                         fg_color=["#F1F1F1","#2B2B2B"])
        self.CProjectBtn.place(x=8, y=168)

        self.PythonProjectChoose = ctk.CTkFrame(self,
                                                corner_radius=0,
                                                border_width=0,
                                                fg_color=["#F1F1F1","#2B2B2B"])
        self.CProjectChoose = ctk.CTkFrame(self,
                                           corner_radius=0,
                                           border_width=0,
                                           fg_color=["#F1F1F1","#2B2B2B"])

        self.holdingFrame = ctk.CTkFrame(self, width=500, height=600, corner_radius=0, border_width=0)

        ############################################################
        # Python Language Support
        ############################################################

        self.explnlabel0 = ctk.CTkLabel(self.PythonProjectChoose,
                                       text="Python Development Kit Projects",
                                       corner_radius=0,
                                       text_color=["#1E1E1E","#F1F1F1"],
                                       anchor="w",
                                       font=("Segoe UI", 18))
        self.explnlabel0.place(x=15, y=20)

        self.explnlabel1 = ctk.CTkLabel(self.PythonProjectChoose,
                                        text="""Select a template to build up the project. Or start with a completely blank project and build up.
Python Projects come with predefined language support and intellisense, as well as a configured virtual environment to start up right away.""",
                                        corner_radius=0,
                                        text_color=["#1E1E1E","#F1F1F1"],
                                        anchor="w",
                                        font=("Segoe UI", 12),
                                        wraplength=760,
                                        justify="left")
        self.explnlabel1.place(x=15, y=60)

        self.projectType1 = LargeButton(self.PythonProjectChoose,
                                                   text="Python Console Application",
                                                   explainText="Start with an empty python script and scale along the way.",
                                                   image_path=r"icons\language_support\pythonConsole.png")
        self.projectType1.place(x=15,y=130)

        self.projectType2 = LargeButton(self.PythonProjectChoose,
                                                   text="Python Package/Library Project",
                                                   explainText="Develop a reusable python module that can be shared.",
                                                   image_path=r"icons\language_support\package.png")
        self.projectType2.place(x=15,y=220)

        self.projectType3 = LargeButton(self.PythonProjectChoose,
                                                   text="Web Project",
                                                   explainText="A project for creating a generic web application using Python.",
                                                   image_path=r"icons\language_support\web.png")
        self.projectType3.place(x=15,y=310)

        self.projectType4 = LargeButton(self.PythonProjectChoose,
                                                   text="Data Science and Machine Learning Project",
                                                   explainText="A project for creating a data science / artificial intelligence Project.",
                                                   image_path=r"icons\language_support\artificial.png")
        self.projectType4.place(x=15,y=400)

        self.projectType5 = LargeButton(self.PythonProjectChoose,
                                                   text="Pure Data Science Project",
                                                   explainText="A pure data science and visualization project using Python.",
                                                   image_path=r"icons\language_support\dataScience.png")
        self.projectType5.place(x=15,y=490)

        self.projectType6 = LargeButton(self.PythonProjectChoose,
                                                   text="Scientific Simulation Project",
                                                   explainText="A project designed for simulations, graphing, and simulating data using Python.",
                                                   image_path=r"icons\language_support\science.png")
        self.projectType6.place(x=15,y=580)

        self.projectType7 = LargeButton(self.PythonProjectChoose,
                                                   text="Automation and Testing",
                                                   explainText="Write script to automate tasks and test using Python.",
                                                   image_path=r"icons\language_support\test.png")
        self.projectType7.place(x=15,y=580)

        ############################################################
        # C Language Support
        ############################################################
        self.Cexplnlabel0 = ctk.CTkLabel(self.CProjectChoose,
                                       text="C Development Kit Projects",
                                       corner_radius=0,
                                       text_color=["#1E1E1E","#F1F1F1"],
                                       anchor="w",
                                       font=("Segoe UI", 18))
        self.Cexplnlabel0.place(x=15, y=20)

        self.Cexplnlabel1 = ctk.CTkLabel(self.CProjectChoose,
                                        text="""Enjoy and wide range of support for creating high quality C-applications.
C projects come with all the needed intellisense, language packages, and support so you start working right away.""",
                                        corner_radius=0,
                                        text_color=["#1E1E1E","#F1F1F1"],
                                        anchor="w",
                                        font=("Segoe UI", 12),
                                        wraplength=760,
                                        justify="left")
        self.Cexplnlabel1.place(x=15, y=60)

        self.projectTypeC1 = LargeButton(self.CProjectChoose,
                                                   text="C Console Application",
                                                   explainText="Start with an empty C-File and scale along the way.",
                                                   image_path=r"icons\language_support\CConsole.png",
                                                   command=lambda: self.showFrame("C Console Application",
                                                                                  r"icons\code_snippets\CConsole.png",
                                                                                  ""))
        self.projectTypeC1.place(x=15,y=130)

        self.projectTypeC2 = LargeButton(self.CProjectChoose,
                                                   text="Device Drivers Project",
                                                   explainText="Write a C code that interfaces with the hardware or OS kerel modules.",
                                                   image_path=r"icons\language_support\driver.png")
        self.projectTypeC2.place(x=15,y=220)

        self.projectTypeC3 = LargeButton(self.CProjectChoose,
                                                   text="System Level and Kernel Project",
                                                   explainText="Develop operating systems, kernels, and core system components.",
                                                   image_path=r"icons\language_support\os.png")
        self.projectTypeC3.place(x=15,y=310)

        self.projectTypeC4 = LargeButton(self.CProjectChoose,
                                                   text="Langauge and Architecture Tooling",
                                                   explainText="Build compilers, interpreters, and low-level toolchains using C support.",
                                                   image_path=r"icons\language_support\toolchain.png")
        self.projectTypeC4.place(x=15,y=400)

        self.projectTypeC5 = LargeButton(self.CProjectChoose,
                                                   text="Architecture Simulation Project",
                                                   explainText="A simulation and testing model in a contained environment built using C.",
                                                   image_path=r"icons\language_support\hardware.png")
        self.projectTypeC5.place(x=15,y=490)

        self.projectTypeC6 = LargeButton(self.CProjectChoose,
                                                   text="System BoolLoader Project",
                                                   explainText="Write a fully supported assembly/C project for creating a bootloader application.",
                                                   image_path=r"icons\language_support\bootloader.png")
        self.projectTypeC6.place(x=15,y=580)

        self.projectTypeC7 = LargeButton(self.CProjectChoose,
                                                   text="Shared Low-Level System Library",
                                                   explainText="Write a reusable C library abstracting low-level hardware or OS features.",
                                                   image_path=r"icons\language_support\library.png")
        self.projectTypeC7.place(x=15,y=580)

        self.PythonProjectBtn.configure(command=lambda: self.showProjectType(self.PythonProjectChoose))
        self.CProjectBtn.configure(command=lambda: self.showProjectType(self.CProjectChoose))

    def showProjectType(self, frame: ctk.CTkFrame):
        for widget in self.holdingFrame.winfo_children():
            widget.destroy()
        self.PythonProjectChoose.place_forget()
        self.CProjectChoose.place_forget()

        frame.configure(
            width=self.winfo_width(),
            height=self.winfo_height())
        frame.place(x=300, y=0)

    def showFrame(self, title, image_path, description):
        for widget in self.holdingFrame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.holdingFrame, text=title, font=("Segoe UI", 26)).pack(pady=30, padx=10)

        img = ctk.CTkImage(light_image=Image.open(image_path),
                             dark_image =Image.open(image_path),
                             size=(300,220))
        ctk.CTkLabel(self.holdingFrame, image=img, text="").pack(padx=30)

        ctk.CTkLabel(self.holdingFrame,
                     text=description,
                     wraplength=360,
                     font=("Segoe UI",13),
                     justify="left",).pack(padx=20, pady=10)
        
        ctk.CTkButton(self.holdingFrame,
                      width=100,
                      height=30,
                      corner_radius=4,
                      font=("Segoe UI",12),
                      hover_color=("#30283F"),
                      text="Create Project",
                      fg_color="#423856").pack(padx=(20,0), pady=0, side="left", anchor="s")

        ctk.CTkButton(self.holdingFrame,
                      width=100,
                      height=30,
                      corner_radius=4,
                      font=("Segoe UI",12),
                      hover_color=("#4D4D4D"),
                      text="Cancel Creation",
                      command=self.animate_out,
                      fg_color="#828282").pack(padx=10, pady=0, side="left", anchor="s")

        self.animate_in()

    def animate_in(self):
        x = self.winfo_width()
        target = x - 800

        def slide():
            nonlocal x
            x -= 20
            if x <= target:
                self.holdingFrame.place(x=target, y=0)
                return

            self.holdingFrame.place(x=x, y=0)
            self.after(5, slide)

        slide()

    def animate_out(self):
        x = self.holdingFrame.winfo_x()
        max_x = self.winfo_width()

        def slide():
            nonlocal x
            x += 20
            if x >= max_x:
                self.holdingFrame.place(x=max_x, y=0)
                return
            self.holdingFrame.place(x=x, y=0)
            self.after(10, slide)

        slide()

    def read_text_file(self, path, line_number):
        with open(path, 'r') as file:
            for number, line in enumerate(file):
                if line_number == number:
                    return line
            return None

    def on_close(self):
        self.master.deiconify()
        self.destroy()

class TemplateBuilds(ctk.CTkToplevel):
    def __init__(self):
        pass

    def show(self):
        pass

if __name__ == "__main__":
    app = WelcomeWindow()
    app.run()
