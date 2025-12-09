from widgets.universal_widgets import *
import customtkinter as ctk

root = ctk.CTk()
root.geometry("300x300")


def pick_color():
    dialog = ColorDialog(root, "#00FF00")
    color = dialog.get_color()
    if color:
        print("User selected:", color)
    else:
        print("User cancelled")


button = ctk.CTkButton(root, text="Pick Color", command=pick_color)
button.pack(pady=50)

root.mainloop()
