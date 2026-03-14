import customtkinter as ctk

tab_name = None

class RenameDialog(ctk.CTkToplevel):

    def __init__(self, master, current_name="", callback=None):
        super().__init__(master)

        self.callback = callback

        self.title("Rename Tab")
        self.geometry("360x150")
        self.resizable(False, False)

        self.grab_set()  # modal behavior

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        self.label = ctk.CTkLabel(
            container,
            text="Enter new name",
            font=("Segoe UI", 14, "bold")
        )
        self.label.pack(anchor="w", pady=(0, 8))

        self.entry = ctk.CTkEntry(
            container,
            height=34,
            font=("Segoe UI", 13)
        )
        self.entry.insert(0, current_name)
        self.entry.pack(fill="x", pady=(0, 15))

        buttons = ctk.CTkFrame(container, fg_color="transparent")
        buttons.pack(fill="x")

        cancel_btn = ctk.CTkButton(
            buttons,
            text="Cancel",
            width=100,
            fg_color="gray30",
            command=self.destroy
        )
        cancel_btn.pack(side="right", padx=(10, 0))

        ok_btn = ctk.CTkButton(
            buttons,
            text="Rename",
            width=100,
            command=self._confirm
        )
        ok_btn.pack(side="right")

        self.entry.focus()
        self.bind("<Return>", lambda e: self._confirm())

    def _confirm(self):
        new_name = self.entry.get().strip()
        if self.callback and new_name:
            self.callback(new_name)
        self.destroy()
