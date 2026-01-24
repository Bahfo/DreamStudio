import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import customtkinter as ctk
from PIL import Image
import main


def loading_screen():
    splash = ctk.CTk()
    splash.resizable(False, False)
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)
    window_width = 700
    window_height = 400

    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2) + 90
    y = (screen_height // 2) - (window_height // 2) + 50
    splash.geometry(f"{window_width}x{window_height}+{x}+{y}")

    logo_image = ctk.CTkImage(
        light_image=Image.open(r"icons\logos\logo.png"),
        dark_image=Image.open(r"icons\logos\logo.png"),
        size=(700, 400),
    )

    image_label = ctk.CTkLabel(splash, image=logo_image, text="")
    image_label.place(x=0, y=0)

    def start_main_app():
        splash.destroy()
        mainApp = main.App()
        mainApp.run()

    splash.after(7000, start_main_app)

    splash.mainloop()


loading_screen()
