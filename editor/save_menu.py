import customtkinter as ctk
from tkinter import messagebox
import editor.menu_builders as uniwidgets


class SaveFile(ctk.CTkToplevel):
    def __init__(self, main_app, workspace_container, status_button=None):
        super().__init__(main_app.window)
        self.main_app = main_app
        self.workspace_container = workspace_container
        self.status_button = status_button

        if self.status_button:
            self.status_button.configure(text="Waiting to save file")

        self.title("Save File")
        self.geometry("360x160")
        self.resizable(False, False)
        self.withdraw()
        self.transient(main_app.window)

        label = ctk.CTkLabel(self, text="Enter file name:", font=("Arial", 12))
        label.pack(pady=(20, 5))

        file_naming_box = ctk.CTkEntry(self, width=250, placeholder_text="untitled.txt")
        file_naming_box.place(x=55, y=50)

        def save_file():
            filename = file_naming_box.get().strip()
            file_content = main_app.text_editor.get("1.0", "end-1c")

            if not filename:
                uniwidgets.ScreenShakeAnimation(file_naming_box, orig_x=55, orig_y=50)
                file_naming_box.configure(
                    placeholder_text="Please enter a file name",
                    placeholder_text_color="#ffb2b2",
                )
                return

            if self.workspace_container.get("path") is None:
                uniwidgets.ScreenShakeAnimation(confirm_button, orig_x=130, orig_y=100)
                if self.status_button:
                    self.status_button.configure(
                        text="No workspace active to save file!"
                    )
                return

            if "." not in filename:
                filename += ".txt"

            file_path = self.workspace_container["path"] / filename
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file_content)
                messagebox.showinfo("Success", f"File saved successfully as {filename}")
                if self.status_button:
                    self.status_button.configure(text=f"{filename} saved")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{e}")
                if self.status_button:
                    self.status_button.configure(text=f"{filename} could not be saved")
            self.destroy()

        confirm_button = ctk.CTkButton(
            self,
            font=("Arial", 12),
            text="Save",
            width=100,
            corner_radius=6,
            command=save_file,
        )
        confirm_button.place(x=130, y=100)

    def show(self):
        self.deiconify()
        self.lift()
