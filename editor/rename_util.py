import customtkinter as ctk


class RenameDialog(ctk.CTkToplevel):
    """Dialog for renaming tabs with validation and cancellation support"""

    def __init__(self, master, current_name="", on_confirm=None, on_cancel=None):
        super().__init__(master)

        self.current_name = current_name
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.result = None

        self.title("Rename Tab")
        self.geometry("360x150")
        self.resizable(False, False)

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
            command=self._on_cancel
        )
        cancel_btn.pack(side="right", padx=(10, 0))

        ok_btn = ctk.CTkButton(
            buttons,
            text="Rename",
            width=100,
            command=self._on_confirm
        )
        ok_btn.pack(side="right")

        self.entry.focus()
        self.entry.select_range(0, "end")  # Select all text for quick replacement
        self.bind("<Return>", lambda e: self._on_confirm())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)  # Handle window close button
        
        # Defer grab_set() with a small delay to ensure window is fully rendered
        self.after(100, self._try_grab)

    def _try_grab(self):
        """Try to set grab with error handling"""
        try:
            self.grab_set()
        except:
            # If grab fails, try again after update
            self.update_idletasks()
            try:
                self.grab_set()
            except:
                # If still fails, continue without grab
                pass

    def _on_confirm(self):
        """Handle confirm action"""
        new_name = "   " + self.entry.get().strip() + "   "
        # Only proceed if name is not empty and different from current
        if new_name and new_name != self.current_name:
            self.result = new_name
            if self.on_confirm:
                self.on_confirm(new_name)
        self.destroy()

    def _on_cancel(self):
        """Handle cancel action - preserves original name"""
        self.result = None
        if self.on_cancel:
            self.on_cancel()
        self.destroy()
