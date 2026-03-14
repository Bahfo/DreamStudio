import customtkinter as ctk
from typing import List, Dict
from typing import List, Dict, Any
from tkinter import messagebox as mb

class LayoutsTab(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        textbox: ctk.CTkTextbox,
        foreground_color,
        text_color,
        placeholder_color = ["#CCCCCC","#1E1E1E"],
        max_layouts: int = 16,
        initial_layouts: int = 1,
        *args,
        **kwargs,
    ):
        super().__init__(parent, *args, **kwargs)
        self.textbox = textbox
        self.max_layouts = max_layouts
        self.foreground_color = foreground_color
        self.text_color = text_color
        self.placeholder_color = placeholder_color

        self.layouts: List[Dict[str, Any]] = []
        self.tab_widgets: List[Dict[str, Any]] = []
        self.active_index: int = 0

        # Top frame
        self.top_frame = ctk.CTkFrame(
            self, corner_radius=0, height=40, fg_color=self.foreground_color
        )
        self.top_frame.pack(side="top", fill="x")
        self.top_frame.pack_propagate(False)

        # Frame that holds tabs
        self.tabs_container = ctk.CTkFrame(
            self.top_frame, corner_radius=0, fg_color=self.foreground_color
        )
        self.tabs_container.pack(side="left", fill="x", expand=True)

        # Add button on the right
        self.status_frame = ctk.CTkFrame(
            self.top_frame, corner_radius=0, fg_color=self.foreground_color
        )
        self.status_frame.pack(side="right")
        self.add_button = ctk.CTkButton(
            self.status_frame,
            text="+",
            width=30,
            border_color="#5E5E5E",
            border_width=1,
            text_color=self.text_color,
            fg_color=self.foreground_color,
            corner_radius=0,
            command=self.add_layout,
        )
        self.add_button.pack(side="left", padx=2)

        # Initialize tabs
        for _ in range(initial_layouts):
            self._create_tab()
        self._reconfigure_tab_indices()
        self.switch_layout(0)

    # ---------------- TAB MANAGEMENT ----------------
    def _create_tab(self):
        idx = len(self.layouts) + 1
        title = f"New Tab {idx}"
        self.layouts.append({"title": title, "text": "", "saved": True})

        tab_frame = ctk.CTkFrame(
            self.tabs_container,
            corner_radius=0,
            border_color="#5E5E5E",
            border_width=1,
            width=120,
            height=30,
            fg_color=self.foreground_color,
        )
        tab_frame.pack(side="left", padx=(5, 2), pady=0)
        tab_frame.pack_propagate(False)

        title_btn = ctk.CTkButton(
            tab_frame,
            text=title,
            corner_radius=0,
            width=90,
            fg_color=self.foreground_color,
            text_color=self.text_color,
            font=("Segoe UI", 12, "normal"),
            height=20,
        )
        title_btn.pack(side="left", padx=(2, 0))

        close_btn = ctk.CTkButton(
            tab_frame,
            text="×",
            width=24,
            height=20,
            fg_color=self.foreground_color,
            text_color=self.text_color,
            font=("Segoe UI", 12, "bold"),
            corner_radius=0,
        )
        close_btn.pack(side="right", padx=(0, 2))

        self.tab_widgets.append(
            {"frame": tab_frame, "title_btn": title_btn, "close_btn": close_btn}
        )

    def add_layout(self):
        if len(self.layouts) >= self.max_layouts:
            mb.showwarning("Maximum Tabs", "Cannot add more tabs.")
            self.add_button.configure(state="disabled")
            return
        self._create_tab()
        self._reconfigure_tab_indices()
        self.switch_layout(len(self.layouts) - 1)
        self.add_button.configure(state="normal")

    def _reconfigure_tab_indices(self):
        for i, tab in enumerate(self.tab_widgets):
            tab["title_btn"].configure(command=lambda idx=i: self.switch_layout(idx))
            tab["close_btn"].configure(command=lambda idx=i: self._close_layout(idx))
            tab["title_btn"].bind(
                "<Button-3>", lambda e, idx=i: self._rename_layout(idx)
            )

    # ---------------- TAB CONTENT ----------------
    def _save_current_text(self):
        if not self.layouts:
            return
        current_layout = self.layouts[self.active_index]
        text = self.textbox.get("1.0", "end-1c")
        current_layout["saved"] = text == current_layout["text"]
        current_layout["text"] = text

        base_title = current_layout["title"].rstrip(" *")
        display_title = f"{base_title} *" if not current_layout["saved"] else base_title
        self.tab_widgets[self.active_index]["title_btn"].configure(text=display_title)

    def switch_layout(self, index: int):
        if index < 0 or index >= len(self.layouts):
            return
        self._save_current_text()
        self.active_index = index
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", self.layouts[index]["text"])
        self._highlight_active_tab()

    def _highlight_active_tab(self):
        for i, tab in enumerate(self.tab_widgets):
            if i == self.active_index:
                tab["title_btn"].configure(font=("Segoe UI Italic", 12))
                tab["title_btn"].configure(text_color=self.placeholder_color)
            else:
                tab["title_btn"].configure(font=("Segoe UI", 12, "normal"))
                tab["title_btn"].configure(text_color=self.text_color)

    # ---------------- CLOSE / RENAME ----------------
    def _close_layout(self, index: int):
        if len(self.layouts) <= 1:
            mb.showwarning("Warning", "Cannot close the last tab.")
            return
        self._save_current_text()
        layout = self.layouts[index]
        if not layout["saved"]:
            confirm = mb.askyesno(
                "Unsaved Changes",
                f"Layout '{layout['title']}' has unsaved changes. Close anyway?",
            )
            if not confirm:
                return
        self.layouts.pop(index)
        tab_widget = self.tab_widgets.pop(index)
        tab_widget["frame"].destroy()
        if self.active_index >= len(self.layouts):
            self.active_index = len(self.layouts) - 1
        self._reconfigure_tab_indices()
        self.add_button.configure(state="normal")
        self.switch_layout(self.active_index)

    def _rename_layout(self, index: int):
        popup = ctk.CTkToplevel(self)
        popup.title("Rename Layout")
        popup.geometry("300x120")
        popup.grab_set()
        lbl = ctk.CTkLabel(popup, text="New title:")
        lbl.pack(pady=(10, 4))
        entry = ctk.CTkEntry(popup)
        entry.insert(0, self.layouts[index]["title"])
        entry.pack(padx=10)

        def apply_and_close():
            new_title = entry.get().strip()
            if new_title:
                self.layouts[index]["title"] = new_title
                self._save_current_text()
            popup.destroy()

        btn = ctk.CTkButton(popup, text="Apply", command=apply_and_close)
        btn.pack(pady=8)

