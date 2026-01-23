import tkinter as tk
from tkinterweb import HtmlFrame

root = tk.Tk()
root.geometry("1000x700")

frame = HtmlFrame(root)
frame.pack(fill="both", expand=True)

frame.load_website("https://www.google.com")

root.mainloop()
