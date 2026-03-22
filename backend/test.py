import os
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
from core import WatchDog  # Your backend


class FileExplorer(ttk.Frame):
    """
    FileExplorer widget for Tkinter / CustomTkinter.
    Displays a directory tree with icons, supports add/remove files/folders,
    WatchDog backend updates, and theme customization.

    Parameters:
        parent (tk.Widget): Parent container.
        directory (str, optional): Initial directory path.
        theme (str): "dark" or "light".
        border_width (int): Width of the border around the widget.
        border_color (str): Color of the border.
        show_editor (bool): If True, shows a right-side editor panel.
    """

    def __init__(
        self,
        parent,
        directory=None,
        theme="dark",
        border_width=2,
        border_color="#555555",
        show_editor=True,
        **kwargs
    ):
        # Use style instead of bg directly
        super().__init__(parent, style="FileExplorer.TFrame", **kwargs)
        self.parent = parent
        self.directory = directory
        self.theme = theme
        self.border_width = border_width
        self.border_color = border_color
        self.show_editor = show_editor
        self.path_to_id = {}

        # ----------------------------
        # Styles / Theme
        # ----------------------------
        self.style = ttk.Style(self)
        self.setup_theme()

        # ----------------------------
        # Paned window layout
        # ----------------------------
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # ----------------------------
        # Treeview panel
        # ----------------------------
        self.tree_frame = ttk.Frame(
            self.paned,
            style="TreePanel.TFrame",
            borderwidth=self.border_width,
            relief="solid",
        )
        self.tree = ttk.Treeview(self.tree_frame, show="tree")
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=2, pady=2)
        self.tree_scroll = ttk.Scrollbar(
            self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.paned.add(self.tree_frame, weight=1)

        # ----------------------------
        # Optional editor panel
        # ----------------------------
        if self.show_editor:
            self.editor_frame = ttk.Frame(
                self.paned,
                style="EditorPanel.TFrame",
                borderwidth=self.border_width,
                relief="solid",
            )
            self.editor = tk.Text(
                self.editor_frame, wrap=tk.NONE, bg=self.bg, fg=self.fg
            )
            self.editor.pack(fill=tk.BOTH, expand=True)
            self.paned.add(self.editor_frame, weight=3)

        # ----------------------------
        # Load icons
        # ----------------------------
        self.load_icons()

        # ----------------------------
        # WatchDog backend
        # ----------------------------
        self.watchdog = WatchDog(gui_callback=self.on_file_event)
        if self.directory:
            self.load_directory(self.directory)

        # ----------------------------
        # Right-click menu
        # ----------------------------
        self.menu = tk.Menu(
            self,
            tearoff=0,
            bg=self.bg,
            fg=self.fg,
            activebackground="#007acc" if self.theme == "dark" else "#cce6ff",
            activeforeground=self.fg,
        )
        self.menu.add_command(label="Add File", command=self.add_file)
        self.menu.add_command(label="Add Folder", command=self.add_folder)
        self.menu.add_command(label="Remove", command=self.remove_item)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", self.open_file)

        # ----------------------------
        # Modern tree appearance
        # ----------------------------
        self.style.configure("Treeview", rowheight=24, font=("Segoe UI", 10))
        self.style.map(
            "Treeview",
            foreground=[("selected", "#ffffff")],
            background=[("selected", "#007acc" if self.theme == "dark" else "#3399ff")],
        )
        # Replace default plus/minus indicators with modern layout
        self.tree.tk.call(
            "ttk::style",
            "layout",
            "Treeview.Item",
            [
                (
                    "Treeitem.padding",
                    {
                        "sticky": "nswe",
                        "children": [
                            ("Treeitem.indicator", {"side": "left", "sticky": ""}),
                            ("Treeitem.image", {"side": "left", "sticky": ""}),
                            ("Treeitem.text", {"side": "left", "sticky": "we"}),
                        ],
                    },
                )
            ],
        )

    # ----------------------------
    # Theme setup
    # ----------------------------
    def setup_theme(self):
        if self.theme == "dark":
            self.bg, self.fg = "#1e1e1e", "#d4d4d4"
        else:
            self.bg, self.fg = "#ffffff", "#000000"

        # Frame styles
        self.style.configure("FileExplorer.TFrame", background=self.bg)
        self.style.configure("TreePanel.TFrame", background=self.bg)
        self.style.configure("EditorPanel.TFrame", background=self.bg)

        # Treeview styles
        self.style.configure(
            "Treeview", background=self.bg, foreground=self.fg, fieldbackground=self.bg
        )
        self.style.configure("Treeview.Heading", background=self.bg, foreground=self.fg)

    # ----------------------------
    # Load icons
    # ----------------------------
    def load_icons(self):
        self.icons = {}
        try:
            folder_img = Image.open(r"backend\folder.png").resize((16, 16))
            self.icons["folder"] = ImageTk.PhotoImage(folder_img)
            unknown_img = Image.open(r"backend\unknown.png").resize((16, 16))
            self.icons["file"] = ImageTk.PhotoImage(unknown_img)
        except Exception as e:
            print("Error loading icons:", e)
            self.icons = {}

    def get_icon(self, path):
        if os.path.isdir(path):
            return self.icons.get("folder")
        return self.icons.get("file")

    # ----------------------------
    # Load directory
    # ----------------------------
    def load_directory(self, directory):
        self.directory = directory
        root_id = self.tree.insert(
            "",
            "end",
            text=os.path.basename(directory),
            open=True,
            image=self.get_icon(directory),
        )
        self.path_to_id[directory] = root_id
        self.populate_tree(directory, root_id)
        self.watchdog.start_tracker(directory)

    def populate_tree(self, path, parent_id):
        try:
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    dir_id = self.tree.insert(
                        parent_id,
                        "end",
                        text=item,
                        image=self.get_icon(full_path),
                        open=False,
                    )
                    self.path_to_id[full_path] = dir_id
                    self.populate_tree(full_path, dir_id)
                else:
                    file_id = self.tree.insert(
                        parent_id, "end", text=item, image=self.get_icon(full_path)
                    )
                    self.path_to_id[full_path] = file_id
        except PermissionError:
            pass

    # ----------------------------
    # WatchDog callback
    # ----------------------------
    def on_file_event(self, event):
        typ = event["type"]
        path = event["path"]
        if typ == "FILE_ADDED":
            self.add_node(path)
        elif typ == "FILE_REMOVED":
            self.remove_node(path)
        elif typ == "FILE_MOVED":
            self.remove_node(event["old_path"])
            self.add_node(path)
        elif typ == "FILE_CHANGED":
            self.highlight_node(path)

    # ----------------------------
    # Node helpers
    # ----------------------------
    def add_node(self, path):
        parent = os.path.dirname(path)
        parent_id = self.path_to_id.get(parent)
        if parent_id:
            if os.path.isdir(path):
                self.add_folder_recursive(path, parent_id)
            else:
                file_id = self.tree.insert(
                    parent_id,
                    "end",
                    text=os.path.basename(path),
                    image=self.get_icon(path),
                )
                self.path_to_id[path] = file_id

    def add_folder_recursive(self, path, parent_id):
        dir_id = self.tree.insert(
            parent_id, "end", text=os.path.basename(path), image=self.get_icon(path)
        )
        self.path_to_id[path] = dir_id
        try:
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    self.add_folder_recursive(full_path, dir_id)
                else:
                    file_id = self.tree.insert(
                        dir_id, "end", text=item, image=self.get_icon(full_path)
                    )
                    self.path_to_id[full_path] = file_id
        except PermissionError:
            pass

    def remove_node(self, path):
        item_id = self.path_to_id.pop(path, None)
        if item_id:
            self.tree.delete(item_id)

    def highlight_node(self, path):
        item_id = self.path_to_id.get(path)
        if item_id:
            self.tree.item(item_id, tags=("changed",))
            self.tree.tag_configure("changed", background="yellow")
            self.after(500, lambda i=item_id: self.tree.item(i, tags=()))

    # ----------------------------
    # Context menu
    # ----------------------------
    def show_context_menu(self, event):
        selected = self.tree.identify_row(event.y)
        if selected:
            self.tree.selection_set(selected)
            self.menu.post(event.x_root, event.y_root)

    def add_file(self):
        node = self.tree.selection()[0]
        parent_path = self.get_path(node)
        if os.path.isdir(parent_path):
            name = filedialog.asksaveasfilename(initialdir=parent_path)
            if name:
                open(name, "w").close()
                self.add_node(name)

    def add_folder(self):
        node = self.tree.selection()[0]
        parent_path = self.get_path(node)
        if os.path.isdir(parent_path):
            name = filedialog.askdirectory(initialdir=parent_path)
            if name:
                os.makedirs(name, exist_ok=True)
                self.add_node(name)

    def remove_item(self):
        node = self.tree.selection()[0]
        path = self.get_path(node)
        if path:
            import shutil

            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.remove_node(path)

    def open_file(self, event):
        if not self.show_editor:
            return
        node = self.tree.selection()[0]
        path = self.get_path(node)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                self.editor.delete("1.0", tk.END)
                self.editor.insert(tk.END, f.read())

    def get_path(self, node):
        for path, nid in self.path_to_id.items():
            if nid == node:
                return path
        return None

    def destroy_widget(self):
        """Stop WatchDog and destroy widget."""
        self.watchdog.stop_tracker()
        self.destroy()


root = ctk.CTk()
root.geometry("1000x650")
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

directory = filedialog.askdirectory(title="Select Project Directory")

explorer = FileExplorer(
    root,
    directory=directory,
    theme="dark",
    border_width=3,
    border_color="#222222",
    show_editor=True,
)
explorer.pack(fill="both", expand=True, padx=10, pady=10)

root.mainloop()
