import os

import customtkinter as ctk

from editor.utils.ctk_scrollable_frame import CTkScrollableFrame
from typing import Callable, Optional, List
from editor.utils.icons_utils import *

COLORS = {
    "light": {
        "bg": "#F5F5F5",
        "fg": "#323233",
        "selected_bg": "#E8E8E8",
        "hover_bg": "#F0F0F0",
        "arrow": "#4B4B4B"
    },
    "dark": {
        "bg": "#1E1E1E",
        "fg": "#CCCCCC",
        "selected_bg": "#2A2D2E",
        "hover_bg": "#2A2D2E",
        "arrow": "#CECECE"
    }
}

class FileTreeItem(ctk.CTkFrame):
    """
    Represents a single file or folder in the tree.
    Handles rendering, indentation, and selection state.
    """
    def __init__(self, master, parent_tree_ref, path: str, level: int = 0, is_folder: bool = False, **kwargs):
        super().__init__(master, **kwargs)

        self.parent_tree = parent_tree_ref 
        self.path = path
        self.level = level
        self.is_folder = is_folder
        self.is_expanded = False
        self.child_widgets: Optional[List['FileTreeItem']] = None
        
        self.name = os.path.basename(path)
        if not self.name:
            self.name = path
        
        self.ext = os.path.splitext(self.name)[1].replace(".", "") if not is_folder else "folder"

        self.configure(fg_color="transparent", height=25, corner_radius=0)
        self.pack(fill="x", padx=(level * 10 + 5, 0), pady=(1, 1)) # Indentation logic

        # --- UI ELEMENTS ---
        self.arrow_label = ctk.CTkLabel(self, text="", width=15, font=("Segoe UI", 12, "bold"), height=23)
        self.arrow_label.pack(side="left", padx=(2,0))

        if self.is_folder:
            self.arrow_label.configure(text=">", text_color=COLORS["dark"]["arrow"])
            self.arrow_label.bind("<Button-1>", lambda e: self.toggle())

        # Determine which icon to use
        icon_key = "folder" if self.is_folder else (self.ext if self.ext in ICONS else "default")
        icon_img = ICONS.get(icon_key, ICONS.get("default"))

        self.icon_label = ctk.CTkLabel(self, image=icon_img, text="", width=20, height=23)
        self.icon_label.pack(side="left", padx=(0, 5))

        self.text_label = ctk.CTkLabel(
            self, 
            text=self.name, 
            font=("Segoe UI", 12), 
            anchor="w",
            justify="left",
            height=23)
        self.text_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # --- BINDINGS ---
        # Bind click events to the whole row
        self.bind("<Button-1>", self._on_click)
        self.text_label.bind("<Button-1>", self._on_click)
        self.icon_label.bind("<Button-1>", self._on_click)
        
        # Bind double-click events
        self.bind("<Double-Button-1>", self._on_double_click)
        self.text_label.bind("<Double-Button-1>", self._on_double_click)
        self.icon_label.bind("<Double-Button-1>", self._on_double_click)

        # Apply Theme Colors
        self._update_theme_colors()

    def _update_theme_colors(self):
        """Updates colors based on current CTk theme."""
        mode = ctk.get_appearance_mode()
        theme = "dark" if mode == "Dark" else "light"
        colors = COLORS[theme]

        self.configure(fg_color=colors["bg"])
        self.text_label.configure(text_color=colors["fg"])
        
        if self.is_folder:
            arrow_char = "▾" if self.is_expanded else "▸"
            self.arrow_label.configure(text=arrow_char, text_color=colors["arrow"])

    def _on_click(self, event):
        self.parent_tree.select_item(self)

        if self.is_folder:
            self.toggle()
        else:
            if self.parent_tree.file_click_callback:
                self.parent_tree.file_click_callback(self.path)

    def _on_double_click(self, event):
        """Handles double click: Expand folder or Open file."""
        if self.is_folder:
            self.toggle()
        else:
            self.parent_tree.file_click_callback(self.path)

    def toggle(self):
        if not self.is_folder:
            return

        self.is_expanded = not self.is_expanded

        if self.is_expanded and self.child_widgets is None:
            self.child_widgets = []
            try:
                entries = os.listdir(self.path)
                entries.sort(
                    key=lambda x: (
                        not os.path.isdir(os.path.join(self.path, x)),
                        x.lower()
                    )
                )

                insert_after = self

                for entry in entries:
                    child_path = os.path.join(self.path, entry)

                    child_node = self.parent_tree._add_node(
                        path=child_path,
                        level=self.level + 1,
                        parent_frame=self.parent_tree
                    )

                    if child_node:
                        child_node.pack(
                            fill="x",
                            padx=((self.level + 1) * 10 + 5, 0),
                            pady=(1, 1),
                            after=insert_after
                        )
                        insert_after = child_node
                        self.child_widgets.append(child_node)

            except PermissionError:
                print(f"Permission denied: {self.path}")

        elif self.is_expanded:
            insert_after = self
            for child in self.child_widgets:
                child.pack(
                    fill="x",
                    padx=((self.level + 1) * 10 + 5, 0),
                    pady=(1, 1),
                    after=insert_after
                )
                insert_after = child

        else:
            if self.child_widgets:
                self._hide_children(self.child_widgets)

        self._update_theme_colors()

    def _hide_children(self, children):
        """Recursively hides child items."""
        if not children:
            return

        for child in children:
            child.pack_forget()

            if child.is_folder and child.child_widgets:
                self._hide_children(child.child_widgets)

            child.is_expanded = False
            child._update_theme_colors()

    def configure_selected(self, is_selected: bool):
        """Visual feedback for selection."""
        mode = "dark" if ctk.get_appearance_mode() == "Dark" else "light"
        bg = COLORS[mode]["selected_bg"] if is_selected else COLORS[mode]["bg"]
        self.configure(fg_color=bg)


class FileTree(CTkScrollableFrame):
    """
    The main Tree View Widget.
    Inherits from CTkScrollableFrame to provide automatic scrolling.
    """
    def __init__(self, master, width, height, root_path: str = "", 
                 file_click_callback: Optional[Callable] = None,
                 ignore_patterns: List[str] = None, 
                 **kwargs):
        
        super().__init__(master, width=width, height=height, 
                         corner_radius=0, fg_color=["#F5F5F5","#1E1E1E"],
                         **kwargs)
        
        # TODO: Apply adding watchdog by using cached files and items paths instead of dir loading
        self.fs_cache = {}
        self.fs_items = {}
        self.path_to_node = {}
        
        self._scrollbar.configure(corner_radius=0, width=8,
                                  fg_color=["#F5F5F5","#1E1E1E"])
        
        self._scrollbar._button_hover_color = ["#E3E3E3","#141414"]
        self._scrollbar._button_color = ["#F5F5F5","#1E1E1E"]
        
        self.root_path = root_path
        self.file_click_callback = file_click_callback
        self.ignore_patterns = ignore_patterns or [
            "node_modules", "ini", "in", "exe", "lnk", 
            "sys", "thumbs.db", "DS_Store"]
        
        self.selected_item: Optional[FileTreeItem] = None
        self.items = {}

        if self.root_path and os.path.exists(self.root_path):
            self.populate_tree(self.root_path)

    def _update_theme_colors(self):
        mode = "dark" if ctk.get_appearance_mode() == "Dark" else "light"
        self.configure(fg_color=COLORS[mode]["bg"])

    def _should_ignore(self, name: str, is_dir: bool) -> bool:
        """Check if a file/folder should be ignored based on patterns."""
        if is_dir:
            if name in self.ignore_patterns:
                return True
            if name.startswith('.'):
                return True
        else:
            if name.startswith('.'):
                return True
            _, ext = os.path.splitext(name)
            if ext.replace(".", "") in self.ignore_patterns:
                return True
        return False

    def populate_tree(self, root_path):
        """Populates the tree starting from root_path."""
        for widget in self.winfo_children():
            widget.destroy()
        self.items = {}
        
        self._add_node(root_path, level=0)

    def _add_node(self, path: str, level: int, parent_frame=None):
        name = os.path.basename(path)
        if not name: name = path
        is_folder = os.path.isdir(path)
        
        if self._should_ignore(name, is_folder):
            return None

        master_frame = self

        node = FileTreeItem(
            master=master_frame,
            path=path,
            level=level,
            is_folder=is_folder,
            parent_tree_ref=self)

        self.items[path] = node

        if is_folder:
            node.child_widgets = None

        return node

    def select_item(self, item: FileTreeItem):
        """Handles visual selection of an item."""
        if self.selected_item:
            self.selected_item.configure_selected(False)
        
        item.configure_selected(True)
        self.selected_item = item
