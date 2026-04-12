import customtkinter as ctk
from customtkinter import filedialog
from tkinter import messagebox
import os

class SaveFile(ctk.CTkToplevel):
    def __init__(self, main_app, workspace_container, status_button=None):
        super().__init__(main_app) 
        
        self.attributes("-topmost", True)
        self.main_app = main_app
        self.workspace_container = workspace_container
        self.status_button = status_button
        
        # We will dynamically set these when show() is called from the save function
        self.target_editor = None
        self.tab_switch = None

        self.title("Save File")
        self.geometry("360x160")
        self.resizable(False, False)
        
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.withdraw()

        label = ctk.CTkLabel(self, text="Enter file name:", font=("Arial", 12))
        label.pack(pady=(20, 5))

        self.file_naming_box = ctk.CTkEntry(self, width=250, placeholder_text="untitled.txt")
        self.file_naming_box.place(x=55, y=50)

        self.confirm_button = ctk.CTkButton(
            self,
            font=("Arial", 12),
            text="Save",
            width=100,
            corner_radius=6,
            command=self.save_file,
        )
        self.confirm_button.place(x=130, y=100)

    def save_file(self):
        file_name = self.file_naming_box.get().strip()

        if not file_name:
            messagebox.showwarning("Invalid Name", "Please enter a valid file name.")
            # Lift the window back up since messagebox might push it behind
            self.lift()
            return

        # Ask the user WHERE to save this new file. 
        # (Note: If your `workspace_container` tracks the active project path, 
        # you could just use that path here and skip the askdirectory prompt!)
        save_directory = filedialog.askdirectory(title="Select Save Location")

        if not save_directory:
            self.lift()
            return  # User cancelled the directory prompt

        full_path = os.path.join(save_directory, file_name)

        if not hasattr(self, 'target_editor') or not self.target_editor:
            messagebox.showerror("Error", "No active editor found to save.")
            return

        try:
            # 1. Grab content and write to the new file
            content = self.target_editor.content.get("1.0", "end-1c")
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            # 2. Update editor attributes so future saves trigger Scenario 1 (Overwrite)
            self.target_editor.file_path = full_path

            # 3. Rename the tab to match the new file name (keeping your spacing convention)
            old_tab_name = self.target_editor._tab_name
            new_tab_name = f"   {file_name}   "

            if self.tab_switch:
                self.tab_switch.rename(old_tab_name, new_tab_name)
                self.target_editor._tab_name = new_tab_name
                self.tab_switch.set(new_tab_name)

            # 4. Update status, clear the entry box, and hide the popup
            if self.status_button:
                self.status_button.configure(text=f"Saved: {file_name}")

            self.file_naming_box.delete(0, 'end')
            self.hide()

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save file:\n{str(e)}")
            self.lift()

    def hide(self):
        self.withdraw()

    def show(self):
        if self.winfo_exists():
            self.deiconify()
            self.lift()
            self.focus_force()