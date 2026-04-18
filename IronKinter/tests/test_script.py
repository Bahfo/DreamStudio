import customtkinter as ctk
import tkinter as tk

ctk.set_appearance_mode("System")


class EditorApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Textbox Color Change Example")
        self.geometry("600x400")

        self.dark_mode = True
        self.textboxes = {}

        # Tab system
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Control buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=5)

        add_tab_btn = ctk.CTkButton(button_frame, text="Add Tab", command=self.add_tab)
        add_tab_btn.pack(side="left", padx=5)

        toggle_btn = ctk.CTkButton(
            button_frame, text="Toggle Theme", command=self.toggle_theme
        )
        toggle_btn.pack(side="left", padx=5)

        # First tab
        self.add_tab()

    def add_tab(self):
        tab_name = f"Tab {len(self.textboxes)+1}"
        self.tabview.add(tab_name)

        frame = self.tabview.tab(tab_name)

        text = tk.Text(frame, font=("Consolas", 12))
        text.pack(fill="both", expand=True)

        self.textboxes[tab_name] = text

        self.apply_color(text)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode

        current_tab = self.tabview.get()
        text_widget = self.textboxes[current_tab]

        self.apply_color(text_widget)

    def apply_color(self, widget):

        if self.dark_mode:
            widget.configure(bg="#1e1e1e", fg="#ffffff", insertbackground="#ffffff")
        else:
            widget.configure(bg="#ffffff", fg="#000000", insertbackground="#000000")


if __name__ == "__main__":
    app = EditorApp()
    app.mainloop()
