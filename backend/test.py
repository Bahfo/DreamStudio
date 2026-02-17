######################## RECUIRES MORE AND MORE TESTING ... NEEDS MORE TIME TO VERDICT ########################

import os
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from core import WatchDog  # Your WatchDog class

class ProjectTreeGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Project Tree Tracker")
        self.geometry("800x600")

        # Treeview
        self.tree = ttk.Treeview(self)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.path_to_id = {}

        # Load Project button
        self.load_btn = tk.Button(self, text="Load Project", command=self.load_project)
        self.load_btn.pack(pady=5)

        # WatchDog instance
        self.watchdog = WatchDog(gui_callback=self.on_file_event)

        # Right-click menu
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Add File", command=self.add_file_menu)
        self.menu.add_command(label="Remove File", command=self.remove_file_menu)
        self.menu.add_command(label="Add Directory", command=self.add_dir_menu)
        self.menu.add_command(label="Remove Directory", command=self.remove_dir_menu)
        self.menu.add_separator()
        self.menu.add_command(label="Refresh Tree", command=self.refresh_tree)

        # Bind right-click
        self.tree.bind("<Button-3>", self.show_context_menu)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # -----------------------------
    # Load project
    # -----------------------------
    def load_project(self):
        project_path = filedialog.askdirectory(title="Select Project Folder")
        if not project_path:
            return

        # Root node
        root_id = self.tree.insert("", "end", text=os.path.basename(project_path), open=True)
        self.path_to_id[project_path] = root_id
        self.root_path = project_path

        # Populate tree
        self.populate_tree(project_path, root_id)

        # Start WatchDog
        self.watchdog.start_tracker(project_path)
        messagebox.showinfo("Tracker", f"File tracker started on: {project_path}")

    # -----------------------------
    # Recursive tree population
    # -----------------------------
    def populate_tree(self, path, parent_id):
        try:
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    dir_id = self.tree.insert(parent_id, "end", text=item, open=False)
                    self.path_to_id[full_path] = dir_id
                    self.populate_tree(full_path, dir_id)
                else:
                    file_id = self.tree.insert(parent_id, "end", text=item)
                    self.path_to_id[full_path] = file_id
        except PermissionError:
            pass

    # -----------------------------
    # WatchDog callback
    # -----------------------------
    def on_file_event(self, event):
        event_type = event["type"]
        path = event["path"]

        if event_type == "FILE_ADDED":
            if os.path.isdir(path):
                self.add_directory_recursively(path)
            else:
                self.add_file_node(path)
        elif event_type == "FILE_REMOVED":
            self.remove_item(path)
        elif event_type == "FILE_MOVED":
            old_path = event["old_path"]
            self.remove_item(old_path)
            if os.path.isdir(path):
                self.add_directory_recursively(path)
            else:
                self.add_file_node(path)
        elif event_type == "FILE_CHANGED":
            self.highlight_changed(path)

    # -----------------------------
    # Helper methods
    # -----------------------------
    def add_file_node(self, path):
        parent_path = os.path.dirname(path)
        parent_id = self.path_to_id.get(parent_path)
        if parent_id:
            name = os.path.basename(path)
            item_id = self.tree.insert(parent_id, "end", text=name)
            self.path_to_id[path] = item_id

    def add_directory_recursively(self, dir_path):
        parent_path = os.path.dirname(dir_path)
        parent_id = self.path_to_id.get(parent_path)
        if parent_id:
            name = os.path.basename(dir_path)
            dir_id = self.tree.insert(parent_id, "end", text=name, open=False)
            self.path_to_id[dir_path] = dir_id
            try:
                for item in os.listdir(dir_path):
                    full_path = os.path.join(dir_path, item)
                    if os.path.isdir(full_path):
                        self.add_directory_recursively(full_path)
                    else:
                        self.add_file_node(full_path)
            except PermissionError:
                pass

    def remove_item(self, path):
        item_id = self.path_to_id.pop(path, None)
        if item_id:
            self.tree.delete(item_id)

    def highlight_changed(self, path):
        item_id = self.path_to_id.get(path)
        if item_id:
            self.tree.item(item_id, tags=("changed",))
            self.tree.tag_configure("changed", background="yellow")
            self.after(500, lambda i=item_id: self.tree.item(i, tags=()))

    # -----------------------------
    # Right-click menu
    # -----------------------------
    def show_context_menu(self, event):
        selected = self.tree.identify_row(event.y)
        if selected:
            self.tree.selection_set(selected)
            self.menu.post(event.x_root, event.y_root)

    def add_file_menu(self):
        node = self.tree.selection()[0]
        parent_path = self.get_path_from_node(node)
        if os.path.isdir(parent_path):
            name = simpledialog.askstring("Add File", "Enter file name:")
            if name:
                full_path = os.path.join(parent_path, name)
                # Create the file physically
                open(full_path, "w").close()
                # Update Treeview
                self.add_file_node(full_path)

    def remove_file_menu(self):
        node = self.tree.selection()[0]
        path = self.get_path_from_node(node)
        if os.path.isfile(path):
            os.remove(path)
            self.remove_item(path)

    def add_dir_menu(self):
        node = self.tree.selection()[0]
        parent_path = self.get_path_from_node(node)
        if os.path.isdir(parent_path):
            name = simpledialog.askstring("Add Directory", "Enter folder name:")
            if name:
                full_path = os.path.join(parent_path, name)
                os.mkdir(full_path)
                self.add_directory_recursively(full_path)

    def remove_dir_menu(self):
        node = self.tree.selection()[0]
        path = self.get_path_from_node(node)
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
            self.remove_item(path)

    def refresh_tree(self):
        node = self.tree.selection()[0] if self.tree.selection() else ""
        path = self.get_path_from_node(node) if node else self.root_path
        if node:
            self.tree.delete(node)
        self.populate_tree(path, node or "")

    # Helper: get path from Treeview node
    def get_path_from_node(self, node):
        for path, node_id in self.path_to_id.items():
            if node_id == node:
                return path
        return None

    # -----------------------------
    # Close GUI
    # -----------------------------
    def on_close(self):
        self.watchdog.stop_tracker()
        self.destroy()


# -----------------------------
# Run GUI
# -----------------------------
if __name__ == "__main__":
    app = ProjectTreeGUI()
    app.mainloop()
