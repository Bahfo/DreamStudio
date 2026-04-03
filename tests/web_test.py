import tkinter as tk
from tkinterweb import HtmlFrame  # import the HtmlFrame widget

root = tk.Tk()  # create the Tkinter window
frame = HtmlFrame(root, messages_enabled=True)  # create the HTML widget
frame.load_website("https://tkinterweb.readthedocs.io/en/latest/")  # load a website
frame.pack(fill="both", expand=True)  # attach the HtmlFrame widget to the window
root.mainloop()
