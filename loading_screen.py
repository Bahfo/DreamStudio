import customtkinter as ctk
from PIL import Image
import time

def loading_screen():
    splash = ctk.CTk()
    splash.resizable(False, False)
    splash.anchor('center')
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)
    # transparent_color = "#010101"
    # splash.config(bg=transparent_color)
    # splash.attributes("-transparentcolor", transparent_color)

    window_width = 600
    window_height = 450

    splash.update_idletasks()

    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)

    splash.geometry(f"{window_width}x{window_height}+{x}+{y}")

    logo_image = ctk.CTkImage(
        light_image=Image.open(r"icons\types\logo.png"),
        dark_image=Image.open(r"icons\types\logo.png"),
        size=(220, 220))

    image_label = ctk.CTkLabel(splash, image=logo_image, text="")
    image_label.place(x=30,y=20)

    progress_bar = ctk.CTkProgressBar(splash, width=270)
    progress_bar.place()
    progress_bar.set(0)

    loading_label = ctk.CTkLabel(splash, text="Loading ...", font=("Segoe UI", 12))
    loading_label.pack(pady=10)

    for i in range(101): 
        progress_bar.set(i / 100) 
        if i == 25: loading_label.configure(text="Loading Modules ...") 
        elif i == 50: loading_label.configure(text="Setting up Interface ...") 
        elif i == 75: loading_label.configure(text="Initializing Components ...") 
        elif i == 90: loading_label.configure(text="Finalizing ...") 
        splash.update() 
        time.sleep(0.05)

    splash.destroy()

loading_screen()