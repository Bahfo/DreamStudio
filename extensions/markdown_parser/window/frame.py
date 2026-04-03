import customtkinter as ctk
from tkinterweb import HtmlFrame


class MarkDownParser(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(self, fg_color=["#F5F5F5", "#1E1E1E"], corner_radius=0)

        self.markdown_frame = HtmlFrame(master, messages_enabled=True)
        self.markdown_frame.load_website("")
        self.markdown_frame.pack(expand=True, padx=3, pady=3, fill="both")

    def show(self):
        self.pack()
