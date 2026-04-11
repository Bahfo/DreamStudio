import customtkinter as ctk
import threading
import platform
import time

from PIL import Image


class AboutWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)

        self.title("About")
        self.geometry("600x460")
        self.resizable(False, False)

        bg_img = Image.open("assets/themes/theme2.png")
        ctkbgimg = ctk.CTkImage(bg_img, bg_img, (600, 460))

        #### BACKGROUND
        self.imgbg = ctk.CTkLabel(
            self, corner_radius=0, bg_color="transparent", image=ctkbgimg, text=""
        ).pack(expand=True, side="left", fill="both", pady=(30, 0))

        self.label1 = ctk.CTkLabel(
            self,
            corner_radius=0,
            text="DreamStudio IDE",
            text_color="#004073",
            font=("inter", 40),
        ).place(x=10, y=10)

        self.label2 = ctk.CTkLabel(
            self,
            corner_radius=0,
            text="Copyright 2026 - DreamStudio Team",
            text_color=["#1E1E1E", "#FFFFFF"],
            font=("inter", 12),
        ).place(x=10, y=60)

        self.versionLabel = ctk.CTkLabel(
            self, corner_radius=0, text="Version: 1.0.0", font=("inter", 12)
        ).place(x=10, y=110)
        self.osLabel = ctk.CTkLabel(
            self,
            corner_radius=0,
            text=f"Operating System: {platform.system()}",
            font=("inter", 12),
        ).place(x=10, y=130)
        self.label3 = ctk.CTkLabel(
            self,
            corner_radius=0,
            text="Current Snapshot: Y26B01",
            font=("inter", 12),
        ).place(x=10, y=150)
        self.label3 = ctk.CTkLabel(
            self,
            corner_radius=0,
            text="All rights reserved - DreamStudio 2026",
            font=("inter", 12),
        ).place(x=370, y=430)


class CheckForUpdates(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)

        self.geometry("300x100")
        self.resizable(False, False)
        self.title("Updates Checker")

        self.label1 = ctk.CTkLabel(
            self, font=("inter", 12), text="Click to Start Checking for Updates"
        )
        self.label1.pack(anchor="center", pady=10)

        self.btn1 = ctk.CTkButton(
            self,
            text="Check for Updates",
            corner_radius=0,
            fg_color="#004073",
            command=self.showNoUpdates,
        )
        self.btn1.pack(pady=10)

    def showNoUpdates(self):
        def delayed_task():
            time.sleep(5)
            self.label1.configure(text="No Updates Available Now!")

        threading.Thread(target=delayed_task).start()


class License(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Software License")
        self.geometry("500x350")
        self.resizable(False, False)

        license_text = """
Copyright 2026 DreamStudio

Proprietary Freeware License:
DreamStudio is free to download and use, but the user is restricted to the following keypoints:

    - The software is free to use (gratis).
    - Users cannot modify the software.
    - Users cannot sell or distribute it.
    - You may use this software for personal or internal purposes only.
    - You may not modify, reverse engineer, or create derivative works.
    - You may not redistribute, sell, or sublicense this software.

For more info, download the full documentation.
    """

        license_label = ctk.CTkLabel(
            self,
            text=license_text,
            font=("inter", 13),
            wraplength=480,
            justify="left",
        )
        license_label.pack(padx=10, pady=10)
