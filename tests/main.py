import os
import re
import ast
import sys
import time
import keyword
import settings
import builtins
import tempfile
import platform
import pyperclip
import subprocess
import tkinter as tk
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk
from tkinter import messagebox

workspace_container = {"path": None, "loaded_nodes": {}}

PYTHON_KEYWORDS = keyword.kwlist

allowed_extensions = {".py", ".txt", ".html", ".json", ".js"}


def auto_indent(text_editor):
    line_index = text_editor.index("insert linestart")
    current_line = text_editor.get(line_index, "insert")
    leading_spaces = len(current_line) - len(current_line.lstrip())
    indent = " " * leading_spaces
    if current_line.rstrip().endswith(":"):
        indent += "    "  # 4 spaces per level
    text_editor.insert("insert", f"\n{indent}")
    return "break"


def highlight_errors(text_editor):
    text_editor.tag_remove("error_underline", "1.0", "end")

    code = text_editor.get("1.0", "end-1c")
    try:
        ast.parse(code)
    except SyntaxError as e:
        line = e.lineno
        col = e.offset or 1
        # start from offset-1
        start_index = f"{line}.{col-1}"
        # underline until end of line
        end_index = f"{line}.end"
        text_editor.tag_add("error_underline", start_index, end_index)
        text_editor.tag_config("error_underline", underline=True, foreground="#FF0000")


class Highlighter(ctk.CTkTextbox):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        self.tag_config("keyword", foreground="#569CD6")
        self.tag_config("string", foreground="#D69D85")
        self.tag_config("comment", foreground="#6A9955")

        self.bind("<KeyRelease>", self.on_keyrelease)

    def on_keyrelease(self, event=None):
        self.highlight_syntax()

    def highlight_syntax(self):
        content = self.get("1.0", tk.END)
        self.tag_remove("keyword", "1.0", tk.END)
        self.tag_remove("string", "1.0", tk.END)
        self.tag_remove("comment", "1.0", tk.END)

        for match in re.finditer(r"#.*", content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.tag_add("comment", start, end)

        for match in re.finditer(r'(["\'])(?:(?=(\\?))\2.)*?\1', content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.tag_add("string", start, end)

        for kw in PYTHON_KEYWORDS:
            for match in re.finditer(rf"\b{kw}\b", content):
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.tag_add("keyword", start, end)


class CTkWorkspaceTree:
    def __init__(self, parent, text_editor_widget):
        self.root_frame = ctk.CTkScrollableFrame(
            parent, corner_radius=0, fg_color="transparent", height=500
        )
        self.root_frame.pack(fill="both", padx=17, pady=3)

        if platform.system() == "Linux":
            ctk.set_widget_scaling(1.2)
            ctk.set_window_scaling(1.2)

        self.nodes = {}  # node_id → node data
        self.node_order = []  # preserved visual order
        self.text_editor = text_editor_widget

    # ------------------- ICONS -------------------
    def load_icon(self, path):
        img = Image.open(path).resize((16, 16))
        return ImageTk.PhotoImage(img)

    # ------------------- CREATE NODE -------------------
    def insert_node(self, parent_id, name, path_obj, indent):
        node_id = id(path_obj)

        # The container where this node's row and its children_frame will live
        container = (
            self.root_frame
            if parent_id is None
            else self.nodes[parent_id]["children_frame"]
        )

        # Main "row"
        row = ctk.CTkFrame(container, fg_color="transparent")
        row.pack(fill="x")

        # ---------------- Double-click binding ----------------
        row.bind("<Double-1>", lambda e, nid=node_id: self._on_row_double_click(nid))

        # Expand button
        arrow = ctk.CTkButton(
            row,
            width=18,
            height=18,
            font=("Segoe UI", 12),
            text="▶" if path_obj.is_dir() else "",
            fg_color="transparent",
            hover_color="gray15",
            command=lambda nid=node_id: self.toggle(nid),
        )
        arrow.pack(side="left", padx=(indent * 20, 5))

        # Icon (placeholder transparent image)
        icon_img = ImageTk.PhotoImage(Image.new("RGBA", (16, 16)))
        icon = ctk.CTkLabel(row, text="", image=icon_img)
        icon.image = icon_img
        icon.pack(side="left")

        # Label
        label = ctk.CTkLabel(row, text=name, font=("Segoe UI", 12))
        label.pack(side="left", padx=5)

        # Child container (hidden initially)
        child_frame = ctk.CTkFrame(container, fg_color="transparent")

        # Save node data
        self.nodes[node_id] = {
            "name": name,
            "path": path_obj,
            "row": row,
            "arrow": arrow,
            "children_frame": child_frame,
            "children": [],
            "expanded": False,
            "indent": indent,
            "parent": parent_id,
        }

        # Register in workspace container
        workspace_container["loaded_nodes"][node_id] = path_obj

        return node_id

    # ------------------- LAZY INSERT -------------------
    def insert_node_lazy(self, parent_id, path_obj):
        indent = 0 if parent_id is None else self.nodes[parent_id]["indent"] + 1
        return self.insert_node(parent_id, path_obj.name, path_obj, indent)

    # ------------------- TOGGLE -------------------
    def toggle(self, node_id):
        node = self.nodes[node_id]
        if not node["path"].is_dir():
            return
        if node["expanded"]:
            self._collapse(node_id)
        else:
            self._expand(node_id)

    def _expand(self, node_id):
        node = self.nodes[node_id]

        # First time loading children
        if not node["children"]:
            try:
                for child in sorted(
                    node["path"].iterdir(),
                    key=lambda p: (not p.is_dir(), p.name.lower()),
                ):
                    child_id = self.insert_node_lazy(node_id, child)
                    node["children"].append(child_id)
            except (PermissionError, FileNotFoundError):
                return

        try:
            node["children_frame"].pack(fill="x", after=node["row"])
        except TypeError:
            node["children_frame"].pack(fill="x")

        node["arrow"].configure(text="▼")
        node["expanded"] = True

    def _collapse(self, node_id):
        node = self.nodes[node_id]
        node["children_frame"].pack_forget()
        node["arrow"].configure(text="▶")
        node["expanded"] = False

    # ------------------- GET CHILDREN IDS -------------------
    def get_children(self, node_id):
        return self.nodes[node_id]["children"] if node_id in self.nodes else []

    # ------------------- DOUBLE-CLICK FILE OPEN -------------------
    def _on_row_double_click(self, node_id):
        path = workspace_container["loaded_nodes"].get(node_id)
        if path is None:
            return

        if path.is_file() and path.suffix.lower() in allowed_extensions:
            try:
                self.text_editor.delete("1.0", "end")
                with open(path, "r", encoding="utf-8") as f:
                    self.text_editor.insert("1.0", f.read())
            except Exception as e:
                self.text_editor.delete("1.0", "end")
                self.text_editor.insert("1.0", f"Cannot open file: {e}")


def main():

    ctk.set_appearance_mode("dark")
    mode = ctk.get_appearance_mode()
    ################################################################################################
    # MAIN WINDOW
    ################################################################################################
    window = ctk.CTk()
    window.title("Softdream")
    window.geometry("1000x700")
    window.resizable(True, True)

    code_font_var = ctk.StringVar(value="Courier New")

    #################################################################################################
    # PROCESSES AND SERVICES
    #################################################################################################

    def open_version_license():
        license_window = ctk.CTk()
        license_window.title("Software License")
        license_window.geometry("500x350")
        license_window.resizable(False, False)
        license_window.attributes("-topmost", True)

        license_text = """
    Copyright 2026 EX Technologies
    An Integrated Development Environment (IDE) designed to be light, professional, and user-friendly.

    Proprietary Freeware License:
    Softdream is free to download and use, but the user is restricted to the following keypoints:

    - The software is free to use (gratis).
    - Users cannot modify the software.
    - Users cannot sell or distribute it.
    - You may use this software for personal or internal purposes only.
    - You may not modify, reverse engineer, or create derivative works.
    - You may not redistribute, sell, or sublicense this software.

    For more info, download the full documentation.
    """

        license_label = ctk.CTkLabel(
            license_window,
            text=license_text,
            font=("Segoe UI", 13),
            wraplength=480,
            justify="left",
        )
        license_label.pack(padx=10, pady=10)

        license_window.mainloop()

    active_menu = {
        "File": ["New", "Open", "Save", "Exit"],
        "Edit": ["Undo", "Redo", "Cut", "Copy", "Paste"],
        "View": ["Zoom In", "Zoom Out", "Reset Zoom"],
        "Run": ["Run", "Debug"],
        "Help": ["About", "Documentation", "license"],
    }

    class ToolTip:
        def __init__(
            self,
            widget,
            text,
            delay=400,
            bg="#2b2b2b",
            fg="white",
            font=("Segoe UI", 10),
        ):
            self.widget = widget
            self.text = text
            self.delay = delay
            self.bg = bg
            self.fg = fg
            self.font = font

            self.tip_window = None
            self._after_id = None

            widget.bind("<Enter>", self._schedule)
            widget.bind("<Leave>", self._unschedule)
            widget.bind("<Motion>", self._move_tip_position)

        def _schedule(self, event=None):
            self._unschedule()
            self._after_id = self.widget.after(self.delay, self.show_tip)

        def _unschedule(self, event=None):
            if self._after_id is not None:
                try:
                    self.widget.after_cancel(self._after_id)
                except Exception:
                    pass
                self._after_id = None
            self.hide_tip()

        def _move_tip_position(self, event=None):
            if self.tip_window:
                x = event.x_root + 16
                y = event.y_root + 12
                try:
                    self.tip_window.wm_geometry(f"+{x}+{y}")
                except Exception:
                    pass

        def show_tip(self):
            if self.tip_window or not self.text:
                return
            x = self.widget.winfo_rootx() + 40
            y = self.widget.winfo_rooty() + 20

            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_attributes("-topmost", True)
            tw.wm_geometry(f"+{x}+{y}")

            label = tk.Label(
                tw,
                text=self.text,
                justify="left",
                bg=self.bg,
                fg=self.fg,
                font=self.font,
                bd=0,
                padx=6,
                pady=3,
            )
            label.pack()

        def hide_tip(self):
            if self.tip_window:
                try:
                    self.tip_window.destroy()
                except Exception:
                    pass
                self.tip_window = None

    def create_new_file():
        creating_new_file = ctk.CTkToplevel()
        creating_new_file.title("Create a New File")
        creating_new_file.iconbitmap(
            r"/home/bahaa/Desktop/DreamStudio/DreamStudio/tests/icons/new.ico"
        )
        creating_new_file.geometry("360x160")
        creating_new_file.resizable(False, False)
        creating_new_file.attributes("-topmost", True)

        label = ctk.CTkLabel(
            creating_new_file, text="Enter file name:", font=("Segoe UI", 12)
        )
        label.pack(pady=(20, 5))

        file_naming_box = ctk.CTkEntry(
            creating_new_file, width=250, placeholder_text="untitled.txt"
        )
        file_naming_box.pack(pady=(0, 20))

        def confirm_create():
            file_name = file_naming_box.get().strip()
            if not file_name:
                file_name = "untitled.txt"
            with open(file_name, "w", encoding="utf-8") as f:
                f.write("")
            creating_new_file.destroy()

        confirm_button = ctk.CTkButton(
            creating_new_file,
            font=("Segoe UI", 12),
            text="Create",
            width=100,
            corner_radius=6,
            command=confirm_create,
        )
        confirm_button.pack(pady=(0, 10))

    current_file_path = None

    def open_current_file():
        global current_file_path
        current_file = filedialog.askopenfilename(title="Select an existing file")
        if not current_file:
            return

        try:
            with open(current_file, "r", encoding="utf-8") as f:
                content = f.read()

            text_editor.delete("1.0", "end")
            text_editor.insert("1.0", content)
            current_file_path = current_file
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: \n{e}")

    def search_for_keywords():
        search_bar_inside = ctk.CTkToplevel()
        search_bar_inside.title("Find and Search")
        search_bar_inside.geometry("350x150")
        search_bar_inside.resizable(False, False)
        search_bar_inside.attributes("-topmost", True)

        def on_close():
            text_editor.tag_remove("highlight", "1.0", "end-1c")
            search_bar_inside.destroy()

        search_bar_inside.protocol("WM_DELETE_WINDOW", on_close)

        label = ctk.CTkLabel(
            search_bar_inside, text="Enter Keyword/Sentence/.etc", font=("Segoe UI", 12)
        )
        label.pack(pady=(20, 5))

        search_entry = ctk.CTkEntry(search_bar_inside, width=250)
        search_entry.pack(pady=(0, 20))

        def searching(event=None):
            text_to_search = search_entry.get().strip()
            if not text_to_search:
                return

            full_text = text_editor.get("1.0", "end-1c")
            text_editor.tag_remove("highlight", "1.0", "end-1c")
            matches = list(re.finditer(re.escape(text_to_search), full_text))

            if matches:
                for match in matches:
                    start = f"1.0+{match.start()}c"
                    end = f"1.0+{match.end()}c"
                    text_editor.tag_add("highlight", start, end)

                first_match = matches[0]
                start_index = f"1.0+{first_match.start()}c"
                text_editor.mark_set("insert", start_index)
                text_editor.see(start_index)

                text_editor.tag_config(
                    "highlight", background="#633B24", foreground="#FFFFFF"
                )

        confirm_button = ctk.CTkButton(
            search_bar_inside,
            font=("Segoe UI", 12),
            text="Search",
            width=100,
            corner_radius=6,
            command=searching,
        )
        confirm_button.pack(pady=(0, 10))

        search_entry.bind("<Return>", searching)

        search_entry.focus_set()

    font_size_var = ctk.IntVar(value=13)

    def save_current_workspace_file():
        if workspace_container["path"] is None:
            messagebox.showerror("Error", "Please load a workspace first!")
            return

        save_current_workspace = ctk.CTkToplevel()
        save_current_workspace.title("Save File")
        save_current_workspace.iconbitmap(
            r"/home/bahaa/Desktop/DreamStudio/DreamStudio/tests/icons/save.ico"
        )
        save_current_workspace.geometry("360x160")
        save_current_workspace.resizable(False, False)

        label = ctk.CTkLabel(
            save_current_workspace, text="Enter file name:", font=("Segoe UI", 12)
        )
        label.pack(pady=(20, 5))

        file_naming_box = ctk.CTkEntry(
            save_current_workspace, width=250, placeholder_text="untitled.txt"
        )
        file_naming_box.pack(pady=(0, 20))

        def save_file():
            filename = file_naming_box.get().strip()
            file_content = text_editor.get("1.0", "end-1c")

            if not filename:
                file_naming_box.configure(
                    placeholder_text="Please enter a file name",
                    placeholder_text_color="#ffb2b2",
                )
                return

            if "." not in filename:
                filename += ".txt"

            file_path = workspace_container["path"] / filename
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file_content)
                messagebox.showinfo("Success", f"File saved successfully as {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{e}")
            save_current_workspace.destroy()

        confirm_button = ctk.CTkButton(
            save_current_workspace,
            font=("Segoe UI", 12),
            text="Save",
            width=100,
            command=save_file,
            corner_radius=6,
        )
        confirm_button.pack(pady=(0, 10))

    def open_settings():
        settings.open_settings_window()

    menus = {
        "File": [
            "New File",
            "New Folder",
            "Open File",
            "Open Folder",
            "Save",
            "Save as",
            "Exit and Close",
        ],
        "Edit": ["Undo", "Redo", "Cut", "Copy", "Paste"],
        "View": ["View Terminal", "Debug Console"],
        "Run": ["Start Debugging", "Run without Debugging", "Stop Running"],
        "Help": ["Help", "Documentation", "About"],
    }

    ################################################################################################
    # MENUBAR
    ################################################################################################
    active_menu = {"menu": None}

    def file_new():
        print("File → New clicked")

    def file_open():
        print("File → Open clicked")

    def file_save():
        print("File → Save clicked")

    def file_exit():
        window.destroy()

    def edit_undo():
        print("Edit → Undo clicked")

    def edit_redo():
        print("Edit → Redo clicked")

    def edit_cut():
        print("Edit → Cut clicked")

    def edit_copy():
        print("Edit → Copy clicked")

    def edit_paste():
        print("Edit → Paste clicked")

    def view_toggle_sidebar():
        print("View → Toggle Sidebar clicked")

    def view_toggle_toolbar():
        print("View → Toggle Toolbar clicked")

    def run_start():
        print("Run → Start clicked")

    def run_stop():
        print("Run → Stop clicked")

    def run_restart():
        print("Run → Restart clicked")

    def help_about():
        print("Help → About clicked")

    def help_docs():
        print("Help → Documentation clicked")

    menus = {
        "File": [
            ("New", file_new),
            ("Open", file_open),
            ("Save", file_save),
            ("Exit", file_exit),
        ],
        "Edit": [
            ("Undo", edit_undo),
            ("Redo", edit_redo),
            ("Cut", edit_cut),
            ("Copy", edit_copy),
            ("Paste", edit_paste),
        ],
        "View": [
            ("Toggle Sidebar", view_toggle_sidebar),
            ("Toggle Toolbar", view_toggle_toolbar),
        ],
        "Run": [("Start", run_start), ("Stop", run_stop), ("Restart", run_restart)],
        "Help": [("About", help_about), ("Documentation", help_docs)],
    }

    def create_menu_frame(menu_name, x_pos):
        """Generic function to create a menu frame at the given x position."""
        if active_menu["menu"] is not None:
            active_menu["menu"].destroy()
            active_menu["menu"] = None

        active_menu["menu"] = ctk.CTkFrame(
            window,
            fg_color="transparent",
            border_color="#6f6f6f",
            border_width=2,
            corner_radius=10,
        )
        active_menu["menu"].place(x=x_pos, y=28)

        for name, func in menus[menu_name]:
            btn = ctk.CTkButton(
                active_menu["menu"],
                text=name,
                corner_radius=0,
                width=190,
                height=25,
                fg_color="transparent",
                anchor="w",
                font=("Segoe UI", 13),
                border_color="#5E5E5E",
                border_width=1,
                command=func,
            )
            btn.pack()

    def file_menu():
        create_menu_frame("File", 2)

    def edit_menu():
        create_menu_frame("Edit", 55)

    def view_menu():
        create_menu_frame("View", 108)

    def run_menu():
        create_menu_frame("Run", 161)

    def help_menu():
        create_menu_frame("Help", 213)

    menubar = ctk.CTkFrame(
        window,
        height=31,
        corner_radius=0,
        border_color="#5E5E5E",
        fg_color="#007ACC",
        border_width=1,
    )
    menubar.pack(fill="x", side="top")
    menubar.pack_propagate(False)

    file_button_menu = ctk.CTkButton(
        menubar,
        corner_radius=3,
        width=45,
        height=26,
        text="File",
        fg_color=menubar.cget("fg_color"),
        font=("Segoe UI", 12),
    )
    file_button_menu.place(x=3, y=2)
    file_button_menu.configure(command=file_menu)

    edit_button_menu = ctk.CTkButton(
        menubar,
        corner_radius=3,
        width=45,
        height=26,
        text="Edit",
        fg_color=menubar.cget("fg_color"),
        font=("Segoe UI", 12),
    )
    edit_button_menu.place(x=55, y=2)
    edit_button_menu.configure(command=edit_menu)

    view_button_menu = ctk.CTkButton(
        menubar,
        corner_radius=3,
        width=45,
        height=26,
        text="View",
        fg_color=menubar.cget("fg_color"),
        font=("Segoe UI", 12),
    )
    view_button_menu.place(x=108, y=2)
    view_button_menu.configure(command=view_menu)

    run_button_menu = ctk.CTkButton(
        menubar,
        corner_radius=3,
        width=45,
        height=26,
        text="Run",
        fg_color=menubar.cget("fg_color"),
        font=("Segoe UI", 12),
    )
    run_button_menu.place(x=161, y=2)
    run_button_menu.configure(command=run_menu)

    help_button_menu = ctk.CTkButton(
        menubar,
        corner_radius=3,
        width=45,
        height=26,
        text="Help",
        fg_color=menubar.cget("fg_color"),
        font=("Segoe UI", 12),
    )
    help_button_menu.place(x=214, y=2)
    help_button_menu.configure(command=help_menu)

    def close_on_click_outside(event):
        if active_menu["menu"] is None:
            return
        x_root = event.x_root
        y_root = event.y_root
        menu = active_menu["menu"]

        try:
            mx1 = menu.winfo_rootx()
            my1 = menu.winfo_rooty()
            mx2 = mx1 + menu.winfo_width()
            my2 = my1 + menu.winfo_height()
        except tk.TclError:
            mx1 = my1 = mx2 = my2 = 0

        try:
            mbx1 = menubar.winfo_rootx()
            mby1 = menubar.winfo_rooty()
            mbx2 = mbx1 + menubar.winfo_width()
            mby2 = mby1 + menubar.winfo_height()
        except tk.TclError:
            mbx1 = mby1 = mbx2 = mby2 = 0

        if (mx1 <= x_root <= mx2 and my1 <= y_root <= my2) or (
            mbx1 <= x_root <= mbx2 and mby1 <= y_root <= mby2
        ):
            return

        active_menu["menu"].destroy()
        active_menu["menu"] = None

    window.bind("<Button-1>", close_on_click_outside)

    #################################################################################################
    # STATUS BAR
    #################################################################################################
    status_bar = ctk.CTkFrame(
        window,
        height=28,
        corner_radius=0,
        border_color="#5E5E5E",
        border_width=1,
        fg_color="#007ACC",
    )
    status_bar.pack(fill="x", side="bottom")

    Version_button = ctk.CTkLabel(
        status_bar,
        text="Version 0.0.1 BETA",
        font=("Segoe UI", 11),
        text_color="#DCDCDC",
        width=15,
        height=8,
        corner_radius=0,
        fg_color=status_bar.cget("fg_color"),
    )
    Version_button.pack(padx=(10, 10), side="right", pady=(2, 2))

    #################################################################################################
    # SERVICES LEFTMOST BAR
    #################################################################################################
    services_bar = ctk.CTkFrame(
        window, width=50, corner_radius=0, border_color="#5E5E5E", border_width=1
    )
    services_bar.pack_propagate(False)
    services_bar.pack(side="left", fill="y")

    search_photo = ctk.CTkImage(
        light_image=Image.open(
            r"/home/bahaa/Desktop/DreamStudio/DreamStudio/tests/icons/zoom.ico"
        ),
        size=(24, 24),
    )
    open_photo = ctk.CTkImage(
        light_image=Image.open(
            r"/home/bahaa/Desktop/DreamStudio/DreamStudio/tests/icons/open.ico"
        ),
        size=(24, 24),
    )
    settings_photo = ctk.CTkImage(
        light_image=Image.open(
            r"/home/bahaa/Desktop/DreamStudio/DreamStudio/tests/icons/settings.ico"
        ),
        size=(24, 24),
    )
    new_photo = ctk.CTkImage(
        light_image=Image.open(
            r"/home/bahaa/Desktop/DreamStudio/DreamStudio/tests/icons/new.ico"
        ),
        size=(24, 24),
    )
    save_photo = ctk.CTkImage(
        light_image=Image.open(
            r"/home/bahaa/Desktop/DreamStudio/DreamStudio/tests/icons/save.ico"
        ),
        size=(24, 24),
    )

    search_button = ctk.CTkButton(
        services_bar,
        text="",
        image=search_photo,
        width=36,
        height=36,
        corner_radius=5,
        fg_color=services_bar.cget("fg_color"),
        command=search_for_keywords,
    )
    search_button.pack(pady=5)
    ToolTip(search_button, "Searches inside the file for a specific key")

    open_button = ctk.CTkButton(
        services_bar,
        text="",
        image=open_photo,
        width=36,
        height=36,
        fg_color=services_bar.cget("fg_color"),
        corner_radius=5,
        command=open_current_file,
    )
    open_button.pack(pady=5)
    ToolTip(open_button, "Opens a file")

    settings_button = ctk.CTkButton(
        services_bar,
        text="",
        image=settings_photo,
        width=36,
        height=36,
        fg_color=services_bar.cget("fg_color"),
        corner_radius=5,
        command=open_settings,
    )
    settings_button.pack(pady=5)
    ToolTip(settings_button, "Show IDE settings and preferences")

    new_button = ctk.CTkButton(
        services_bar,
        text="",
        image=new_photo,
        width=36,
        height=36,
        corner_radius=5,
        fg_color=services_bar.cget("fg_color"),
        command=create_new_file,
    )
    new_button.pack(pady=5)
    ToolTip(new_button, "Creates a new empty file")

    save_button = ctk.CTkButton(
        services_bar,
        text="",
        image=save_photo,
        width=36,
        height=36,
        corner_radius=5,
        fg_color=services_bar.cget("fg_color"),
        command=save_current_workspace_file,
    )
    save_button.pack(pady=5)
    ToolTip(save_button, "Saves the current loaded workspace file")

    #################################################################################################
    # LEFT SIDEBAR FRAME
    #################################################################################################
    sidebar = ctk.CTkFrame(
        window, width=360, border_width=1, border_color="#5E5E5E", corner_radius=0
    )
    sidebar.pack_propagate(False)
    sidebar.pack(side="left", fill="y")
    editor_frame = ctk.CTkFrame(window)

    text_editor = Highlighter(
        editor_frame,
        font=("consolas", 14),
        border_width=1,
        border_color="#5E5E5E",
        corner_radius=0,
    )

    def on_open_workspace():
        if workspace_container["path"] is None:
            folder = ctk.filedialog.askdirectory(title="Select a workspace folder")
            if not folder:
                return
            workspace_container["path"] = Path(folder)
            open_btn.configure(text="Refresh Workspace")

        refresh_workspace_tree(tree)

    run_btn = ctk.CTkButton(
        sidebar,
        text="Python Integrated Runner",
        fg_color="#004C7E",
        width=320,
        height=25,
        font=("Segoe UI", 13),
        corner_radius=5,
    )
    run_btn.pack(pady=(12, 2), padx=8)
    run_btn.pack_propagate(False)

    open_btn = ctk.CTkButton(
        sidebar,
        text="Open Workspace",
        fg_color="#004C7E",
        width=320,
        height=25,
        font=("Segoe UI", 13),
        corner_radius=5,
        command=on_open_workspace,
    )
    open_btn.pack(pady=(8, 5), padx=8)
    open_btn.pack_propagate(False)

    currentDirLabel = ctk.CTkLabel(
        sidebar,
        text="CURRENT DIRECTORY",
        anchor="w",
        justify="left",
        width=320,
        height=20,
        font=("Segoe UI", 12),
    )
    currentDirLabel.pack(pady=(20, 5), padx=8)

    horizontalFrame = ctk.CTkFrame(sidebar, fg_color="#595959", width=320, height=2)
    horizontalFrame.pack(pady=(0, 10), padx=20, fill="x")

    tree = CTkWorkspaceTree(sidebar, text_editor)

    def run_python_debugger():
        if "current_file_path" in globals() and current_file_path:
            file_to_run = current_file_path
        else:
            code = text_editor.get("1.0", "end-1c")
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as tmp_file:
                tmp_file.write(code)
                file_to_run = tmp_file.name

        subprocess.Popen(
            [sys.executable, "-i", file_to_run],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

    run_btn.configure(command=run_python_debugger)

    def refresh_workspace_tree(tree_widget):
        root_path = workspace_container["path"]
        if root_path is None:
            return

        # If tree empty, insert root node
        if not workspace_container["loaded_nodes"]:
            tree_widget.insert_node_lazy(None, root_path)
            return

        # Refresh existing nodes
        for node_id in list(workspace_container["loaded_nodes"].keys()):
            refresh_node(tree_widget, node_id)

    def refresh_node(tree_widget, node_id):
        node_path = workspace_container["loaded_nodes"].get(node_id)
        if node_path is None:
            return

        path_obj = Path(node_path)
        if not path_obj.exists():
            return

        node = tree_widget.nodes.get(node_id)
        if node is None:
            return

        # Lookup existing children by name
        existing_children = {
            tree_widget.nodes[c]["name"]: c for c in tree_widget.get_children(node_id)
        }

        # Add new children only
        try:
            for child in path_obj.iterdir():
                if child.name in existing_children:
                    continue
                new_child_id = tree_widget.insert_node_lazy(node_id, child)
                tree_widget.nodes[node_id]["children"].append(new_child_id)
        except PermissionError:
            pass

    #################################################################################################
    # MAIN EDITOR AREA
    #################################################################################################
    editor_frame.pack(side="right", fill="both", expand=True)

    def update_text_font(*args):
        text_editor.configure(font=(code_font_var.get(), font_size_var.get()))

    font_size_var.trace_add("write", update_text_font)
    code_font_var.trace_add("write", update_text_font)
    text_editor.pack(fill="both", expand=True)
    text_editor.insert("1.0", "# Softdream Code Editor")

    def copy_text_event(event=None):
        try:
            selected_text = text_editor.selection_get()
            pyperclip.copy(selected_text)
        except tk.TclError:
            pass
        return "break"

    def cut_text_event(event=None):
        try:
            selected_text = text_editor.selection_get()
            pyperclip.copy(selected_text)
            text_editor.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        return "break"

    def paste_text_event(event=None):
        content = pyperclip.paste()
        text_editor.insert(tk.INSERT, content)
        return "break"

    terminal_box = ctk.CTkTextbox(
        editor_frame,
        font=("consolas", 14),
        border_width=1,
        border_color="#5E5E5E",
        corner_radius=0,
    )
    terminal_box.insert("1.0", f"{os.getcwd()} >>> ")
    terminal_box.mark_set("input_start", "insert")

    def open_windows_terminal():
        try:
            subprocess.Popen(
                ["powershell.exe"], creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        except Exception as e:
            pass

    Terminal_button = ctk.CTkButton(
        status_bar,
        text="Open Terminal",
        font=("Segoe UI", 11),
        width=15,
        text_color="#2D2D2D" if mode == "Light" else "#DCDCDC",
        fg_color=status_bar.cget("fg_color"),
        height=8,
        corner_radius=0,
        command=open_windows_terminal,
    )

    def update_line_col():
        pos = text_editor.index("insert")
        line, col = pos.split(".")
        line_and_pos.configure(text=f"Ln: {line}, Col: {int(col)+1}")
        line_and_pos.after(100, update_line_col)

    line_and_pos = ctk.CTkLabel(
        status_bar,
        text="Ln: 1, Col: 1",
        font=("Segoe UI", 11),
        text_color="#DCDCDC",
        width=15,
        height=8,
        corner_radius=0,
        fg_color=status_bar.cget("fg_color"),
    )
    line_and_pos.pack(padx=(2, 10), side="right", pady=(2, 2))

    update_line_col()

    Terminal_button.pack(padx=(2, 10), side="right", pady=(2, 2))

    text_editor.bind("<Control-c>", copy_text_event)
    text_editor.bind("<Control-x>", cut_text_event)
    text_editor.bind("<Control-v>", paste_text_event)
    text_editor.bind("<Control-s>", save_current_workspace_file)
    text_editor.bind("<KeyRelease>", lambda event: highlight_errors(text_editor))
    text_editor.bind("<Return>", lambda e: auto_indent(text_editor))

    error_box = ctk.CTkLabel(
        editor_frame, height=20, font=("Segoe UI", 12), justify="left", anchor="w"
    )
    error_box.pack(fill="x", side="bottom", padx=5)

    def update_problems():
        code = text_editor.get("1.0", "end-1c")
        try:
            ast.parse(code)
            error_box.configure(text="No mistakes catched! Working Fine Wine")
        except SyntaxError as e:
            error_box.configure(
                text=f"SyntaxError: {e.msg} at line {e.lineno}, col {e.offset}"
            )

        defined_names = set()
        for line in code.splitlines():
            tokens = line.strip().split()
            for t in tokens:
                if t in keyword.kwlist or t in dir(builtins):
                    continue
                if t.isidentifier() and t not in defined_names:
                    defined_names.add(t)
                if "=" in line and t in line.split("=")[0]:
                    defined_names.add(t)

        for line in code.splitlines():
            tokens = line.strip().split()
            for t in tokens:
                if (
                    t.isidentifier()
                    and t not in keyword.kwlist
                    and t not in defined_names
                ):
                    error_box.configure(text=f"Warning: '{t}'")

        text_editor.after(500, lambda: update_problems())

    update_problems()

    #################################################################################################
    # CONFIGURATION
    #################################################################################################
    window.mainloop()


def loading_screen():
    ctk.set_appearance_mode("dark")
    splash = ctk.CTk()
    splash.resizable(False, False)
    splash.overrideredirect(False)
    splash.title("EX Technologies")
    splash.iconbitmap(
        r"/home/bahaa/Desktop/DreamStudio/DreamStudio/tests/icons/softdream.ico"
    )

    window_width = 400
    window_height = 300

    splash.update_idletasks()

    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)

    splash.geometry(f"{window_width}x{window_height}+{x}+{y}")

    logo_image = ctk.CTkImage(
        light_image=Image.open(
            r"/home/bahaa/Desktop/DreamStudio/DreamStudio/tests/icons/logo.png"
        ),
        dark_image=Image.open(
            r"/home/bahaa/Desktop/DreamStudio/DreamStudio/tests/icons/logo.png"
        ),
        size=(180, 180),
    )

    image_label = ctk.CTkLabel(splash, image=logo_image, text="")
    image_label.pack(pady=20)

    progress_bar = ctk.CTkProgressBar(splash, width=270)
    progress_bar.pack(pady=10)
    progress_bar.set(0)

    loading_label = ctk.CTkLabel(splash, text="Loading ...", font=("Segoe UI", 12))
    loading_label.pack(pady=10)

    for i in range(101):
        progress_bar.set(i / 100)
        if i == 25:
            loading_label.configure(text="Loading Modules ...")
        elif i == 50:
            loading_label.configure(text="Setting up Interface ...")
        elif i == 75:
            loading_label.configure(text="Initializing Components ...")
        elif i == 90:
            loading_label.configure(text="Finalizing ...")
        splash.update()
        time.sleep(0.05)

    splash.destroy()
    main()


#####################################################################################################
# RUN AND MODIFY
#####################################################################################################
if __name__ == "__main__":
    main()
