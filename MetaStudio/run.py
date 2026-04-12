from editor.ui_build import App
from startup import Initialize
import customtkinter as ctk

ctk.set_appearance_mode("dark")

if __name__ == "__main__":
    app = App(None, path=rf"/home/bahaa/Desktop/apps/test_dir")
    app.run()

# welcome_window = Initialize()
# welcome_window.start_loading_screen()
