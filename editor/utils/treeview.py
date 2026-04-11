import os
import shutil
import tkinter
import customtkinter as ctk
from editor.utils.ctk_scrollable_frame import CTkScrollableFrame
from typing import Callable, Optional, List, Set, Dict, Tuple
from editor.utils.icons_utils import get_icon, has_icon, preload_icons

COLORS = {
    "light": {
        "bg": "#F5F5F5",
        "fg": "#323233",
        "selected_bg": "#E8E8E8",
        "hover_bg": "#F0F0F0",
        "arrow": "#4B4B4B",
    },
    "dark": {
        "bg": "#1E1E1E",
        "fg": "#CCCCCC",
        "selected_bg": "#2A2D2E",
        "hover_bg": "#2A2D2E",
        "arrow": "#CECECE",
    },
}


class FileTreeItem(ctk.CTkFrame):
    def __init__(
        self,
        master,
        parent_tree_ref,
        path: str,
        level: int = 0,
        is_folder: bool = False,
        fg_color=["#F5F5F5", "#1E1E1E"],
        parent_node: Optional["FileTreeItem"] = None,
        height=25,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.parent_tree = parent_tree_ref
        self.path = path
        self.level = level
        self.is_folder = is_folder
        self.is_expanded = False
        self.parent = parent_node
        self.child_items: List["FileTreeItem"] = []
        self._is_reloading = False
        self.pack_propagate(False)

        self.name = os.path.basename(path) or path
        self.ext = (
            os.path.splitext(self.name)[1].replace(".", "")
            if not is_folder
            else "folder"
        )

        self.configure(fg_color="transparent", height=22, corner_radius=0)

        self._indent = level * 6

        # Lazy loader: load children in chunks to keep UI responsive
        self._is_loading_children = False
        self._child_load_chunk_size = 100  # number of entries to load per tick
        self._pending_child_entries = []  # type: List[str]
        self._pending_child_index = 0

        self.arrow_label = ctk.CTkLabel(
            self, text="", width=16, font=("inter", 10, "bold"), height=20
        )
        self.arrow_label.pack(side="left", padx=(self._indent, 0), pady=0)

        if self.is_folder:
            self._update_arrow_icon()
            self.arrow_label.bind("<Button-1>", lambda e: self.toggle())

        icon_key = (
            "folder"
            if self.is_folder
            else (self.ext if has_icon(self.ext) else "default")
        )
        self.icon_label = ctk.CTkLabel(
            self,
            image=get_icon(icon_key) or get_icon("default"),
            text="",
            width=16,
            height=20,
        )
        self.icon_label.pack(side="left", padx=(2, 0), pady=0)

        self.text_label = ctk.CTkLabel(
            self,
            text=f"    {self.name}",
            font=("inter", 12),
            anchor="w",
            justify="left",
            height=23,
            padx=0,
        )
        self.text_label.pack(side="left", fill="both", expand=True)

        for widget in [self, self.text_label, self.icon_label]:
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Double-Button-1>", self._on_double_click)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<ButtonRelease-1>", self._on_drop)

        self._update_theme_colors()

    def _update_arrow_icon(self):
        if not self.winfo_exists():
            return
        mode = "dark" if ctk.get_appearance_mode() == "Dark" else "light"
        char = "▾" if self.is_expanded else "▸"
        self.arrow_label.configure(text=char, text_color=COLORS[mode]["arrow"])

    def _update_theme_colors(self):
        if not self.winfo_exists():
            return
        mode = "dark" if ctk.get_appearance_mode() == "Dark" else "light"
        colors = COLORS[mode]
        is_selected = self == self.parent_tree.selected_item
        self.configure(fg_color=colors["selected_bg"] if is_selected else colors["bg"])
        self.text_label.configure(text_color=colors["fg"])
        if self.is_folder:
            self._update_arrow_icon()

    def _on_click(self, event):
        self.parent_tree.select_item(self)
        if self.is_folder:
            self.toggle()
        elif self.parent_tree.file_click_callback:
            self.parent_tree.file_click_callback(self.path)

    def _on_double_click(self, event):
        if self.is_folder:
            self.toggle()
        else:
            self.parent_tree.file_click_callback(self.path)

    def _on_drag(self, event):
        self.configure(cursor="fleur")

    def _on_drop(self, event):
        self.configure(cursor="")
        target = self.winfo_containing(event.x_root, event.y_root)
        while target and not isinstance(target, FileTreeItem):
            target = target.master

        if target and target != self:
            dest_dir = target.path if target.is_folder else os.path.dirname(target.path)
            if dest_dir.startswith(self.path):
                return

            try:
                shutil.move(self.path, os.path.join(dest_dir, self.name))
            except Exception as e:
                print(f"Move error: {e}")

    def update_path(self, new_path: str):
        old_path = self.path
        old_name = self.name

        del self.parent_tree.items[old_path]
        self.path = new_path
        self.name = os.path.basename(new_path) or new_path
        self.ext = (
            os.path.splitext(self.name)[1].replace(".", "")
            if not self.is_folder
            else "folder"
        )
        self.parent_tree.items[new_path] = self

        self.text_label.configure(text=self.name)

        icon_key = (
            "folder"
            if self.is_folder
            else (self.ext if has_icon(self.ext) else "default")
        )
        self.icon_label.configure(image=get_icon(icon_key) or get_icon("default"))

    def toggle(self):
        if not self.is_folder or not os.path.exists(self.path):
            return
        self.is_expanded = not self.is_expanded

        if self.is_expanded and not self.child_items:
            self._load_children()
        elif self.is_expanded:
            self._show_children()
        else:
            self._hide_children()

        self._update_arrow_icon()

    def _load_children(self):
        # Load children gradually to avoid blocking the UI when directories are large
        if self._is_loading_children:
            return
        self._is_loading_children = True
        try:
            # Prepare a list of entries using scandir for better performance
            try:
                with os.scandir(self.path) as it:
                    entries = [
                        entry
                        for entry in it
                        if not self.parent_tree._should_ignore(
                            entry.name, entry.is_dir()
                        )
                    ]
                # sort: folders first, then by name
                entries.sort(key=lambda e: (not e.is_dir(), e.name.lower()))
            except (PermissionError, FileNotFoundError):
                entries = []
            self._pending_child_entries = [e.name for e in entries]
            self._pending_child_index = 0

            # Schedule first batch
            self._load_next_chunk()
        finally:
            self._is_loading_children = False

    def _load_next_chunk(self):
        # Load the next chunk of children to keep UI responsive
        if not self._pending_child_entries:
            return
        end = min(
            self._pending_child_index + self._child_load_chunk_size,
            len(self._pending_child_entries),
        )
        last_shown = self
        for i in range(self._pending_child_index, end):
            entry_name = self._pending_child_entries[i]
            child_path = os.path.join(self.path, entry_name)
            if child_path in self.parent_tree.items:
                continue
            child_node = self.parent_tree._add_node(
                child_path, self.level + 1, parent_node=self
            )
            if child_node and last_shown.winfo_exists():
                child_node.pack(
                    fill="x",
                    padx=(child_node._indent, 0),
                    pady=(0, 0),
                    after=last_shown,
                )
                last_shown = child_node
                self.child_items.append(child_node)
        self._pending_child_index = end
        if self._pending_child_index < len(self._pending_child_entries):
            self.after(1, self._load_next_chunk)
        else:
            self._pending_child_entries = []
            self._pending_child_index = 0

    def _show_children(self):
        last_shown = self
        for child in self.child_items:
            if child.winfo_exists():
                child.pack(
                    fill="x", padx=(child._indent, 0), pady=(0, 0), after=last_shown
                )
                last_shown = child
                if child.is_expanded:
                    last_shown = child._show_descendants(last_shown)
                else:
                    child._show_children()
                    child._hide_children()

    def _show_descendants(self, last_shown: "FileTreeItem") -> "FileTreeItem":
        for child in self.child_items:
            if child.winfo_exists():
                child.pack(
                    fill="x", padx=(child._indent, 0), pady=(0, 0), after=last_shown
                )
                last_shown = child
                if child.is_expanded:
                    last_shown = child._show_descendants(last_shown)
        return last_shown

    def _hide_children(self):
        for child in self.child_items:
            if child.winfo_exists():
                child.pack_forget()
            child.is_expanded = False
        # If a batch of children is loading, cancel it to avoid unnecessary work
        self._pending_child_entries = []
        self._pending_child_index = 0

    def _destroy_recursive(self):
        for child in self.child_items:
            child._destroy_recursive()
            if child.path in self.parent_tree.items:
                del self.parent_tree.items[child.path]
            if child.winfo_exists():
                child.destroy()
        self.child_items = []

    def configure_selected(self, is_selected: bool):
        if not self.winfo_exists():
            return
        mode = "dark" if ctk.get_appearance_mode() == "Dark" else "light"
        colors = COLORS[mode]
        bg = colors["selected_bg"] if is_selected else colors["bg"]
        self.configure(fg_color=bg)


class FileTree(CTkScrollableFrame):
    def __init__(
        self,
        master,
        width: int,
        height: int,
        root_path: str = "",
        file_click_callback: Optional[Callable[[str], None]] = None,
        file_change_callback: Optional[Callable[[str, str, str], None]] = None,
        ignore_patterns: Optional[List[str]] = None,
        **kwargs,
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            corner_radius=0,
            fg_color=["#F5F5F5", "#1E1E1E"],
            **kwargs,
        )

        self.root_path = root_path
        self.file_click_callback = file_click_callback
        self.file_change_callback = file_change_callback
        self.ignore_patterns = ignore_patterns or [
            "node_modules",
            ".git",
            ".cache",
            ".config",
            ".local",
            "wireplumber",
            "mozilla",
            "sessionstore",
            "sqlite",
            ".tmp",
        ]

        self.selected_item = None
        self.items: Dict[str, FileTreeItem] = {}
        self.watchdog = None
        self._tree_populated = False
        self._watchdog_started = False

        self._scrollbar.configure(
            corner_radius=0, width=8, fg_color=["#F5F5F5", "#1E1E1E"]
        )

    def _should_ignore(self, name: str, is_dir: bool) -> bool:
        if name.startswith((".", "~$", ".~")):
            return True
        name_lower = name.lower()
        return any(pattern in name_lower for pattern in self.ignore_patterns)

    def populate_tree(self, root_path: str):
        if self._tree_populated and self.root_path == root_path:
            return
        
        self.root_path = root_path
        for widget in self.winfo_children():
            if isinstance(widget, FileTreeItem):
                widget.destroy()

        self.items = {}
        self._stop_watcher()

        root_node = self._add_node(root_path, level=0)
        if root_node:
            root_node.pack(fill="x", padx=(0, 0), pady=(0, 0))

        self._tree_populated = True

    def _ensure_watcher_started(self):
        if self._watchdog_started or not self._tree_populated:
            return
        
        from backend.watcher.core import WatchDog

        self.watchdog = WatchDog(
            path=self.root_path, gui_callback=self._on_fs_event_safe
        )
        self.watchdog.start_tracker(self.root_path)
        self._watchdog_started = True

    def _add_node(
        self, path: str, level: int, parent_node: Optional[FileTreeItem] = None
    ) -> Optional[FileTreeItem]:
        name = os.path.basename(path) or path
        is_folder = os.path.isdir(path)
        if self._should_ignore(name, is_folder):
            return None

        node = FileTreeItem(
            master=self,
            parent_tree_ref=self,
            path=path,
            level=level,
            is_folder=is_folder,
            parent_node=parent_node,
        )
        self.items[path] = node
        return node

    def _on_fs_event_safe(self, stable_event):
        try:
            if self.winfo_exists():
                self.after(0, lambda: self._handle_fs_event(stable_event))
        except (tkinter.TclError, RuntimeError):
            pass

    def _handle_fs_event(self, event_data: dict):
        event_type = event_data.get("type")
        path = event_data.get("path")
        old_path = event_data.get("old_path")

        if old_path and path:
            self._handle_rename(old_path, path)
        elif path:
            parent_path = os.path.dirname(path)
            if parent_path in self.items:
                self._refresh_node_smart(parent_path)

    def _handle_rename(self, old_path: str, new_path: str):
        if old_path not in self.items:
            parent_path = os.path.dirname(old_path)
            if parent_path in self.items:
                self._refresh_node_smart(parent_path)
            parent_path = os.path.dirname(new_path)
            if parent_path in self.items:
                self._refresh_node_smart(parent_path)
            return

        old_node = self.items[old_path]

        if self.file_change_callback:
            self.file_change_callback("rename", old_path, new_path)

        old_node.update_path(new_path)

        if not old_node.is_folder and old_node.parent:
            old_node.parent.child_items = [
                c for c in old_node.parent.child_items if c != old_node
            ]

    def _refresh_node_smart(self, parent_path: str):
        node = self.items.get(parent_path)
        if not node or not node.is_folder:
            return

        node._is_reloading = True
        try:
            current_entries: Set[str] = set()
            try:
                current_entries = set(os.listdir(parent_path))
            except (PermissionError, FileNotFoundError):
                return

            existing_names = {child.name for child in node.child_items}
            new_entries = current_entries - existing_names
            removed_names = existing_names - current_entries

            if removed_names:
                self._remove_stale_children(node, removed_names)

            if new_entries:
                self._add_new_children(node, new_entries)
        finally:
            node.after(100, lambda: setattr(node, "_is_reloading", False))

    def _remove_stale_children(self, node: FileTreeItem, removed_names: Set[str]):
        to_remove = [child for child in node.child_items if child.name in removed_names]
        for child in to_remove:
            if self.selected_item == child or self._is_descendant(
                self.selected_item, child
            ):
                self.selected_item = None
            if self.file_change_callback:
                self.file_change_callback("delete", child.path, "")
            child._destroy_recursive()
            node.child_items.remove(child)

    def _add_new_children(self, node: FileTreeItem, new_names: Set[str]):
        last_shown = node.child_items[-1] if node.child_items else node
        entries = sorted(
            new_names,
            key=lambda x: (not os.path.isdir(os.path.join(node.path, x)), x.lower()),
        )

        for entry in entries:
            child_path = os.path.join(node.path, entry)
            if child_path in self.items:
                continue
            child_node = self._add_node(child_path, node.level + 1, parent_node=node)
            if child_node and last_shown.winfo_exists():
                child_node.pack(
                    fill="x",
                    padx=(child_node._indent, 0),
                    pady=(0, 0),
                    after=last_shown,
                )
                last_shown = child_node
                node.child_items.append(child_node)

    def _is_descendant(
        self, item: Optional[FileTreeItem], ancestor: FileTreeItem
    ) -> bool:
        while item:
            if item == ancestor:
                return True
            item = item.parent
        return False

    def select_item(self, item: FileTreeItem):
        if self.selected_item and self.selected_item.winfo_exists():
            self.selected_item.configure_selected(False)

        self.selected_item = item
        if item and item.winfo_exists():
            item.configure_selected(True)

    def _stop_watcher(self):
        if self.watchdog:
            self.watchdog.stop_tracker()

    def destroy(self):
        self._stop_watcher()
        super().destroy()
