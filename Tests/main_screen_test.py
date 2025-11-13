"""
Minimal Code for Testing-Only
EX-Technologies
"""

from tkinter import ttk
from tkinter import filedialog
from pathlib import Path
from PIL import Image, ImageTk
import ctypes
import customtkinter as ctk
import subprocess

def main():
    ################################################################################################
    # HIGH DPI AWARENESS ENABLED
    ################################################################################################
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    #################################################################################################
    # PROCESSES AND SERVICES
    #################################################################################################
    version = "0.0.1 BETA"

    def open_terminal():
        subprocess.Popen("start cmd",shell=True)
    
    def open_version_license():
        license_window = ctk.CTk()
        license_window.title("Software License")
        license_window.iconbitmap(r"icons\softdream.ico")
        license_window.geometry("500x350")
        license_window.configure(bg="#1e1e1e")
        license_window.resizable(False, False)

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
            wraplength=480,   # wrap text to fit inside window
            justify="left"    # left-align text
        )
        license_label.pack(padx=10, pady=10)

        license_window.mainloop()
    
    import tkinter as tk

    class ToolTip:
        """Simple tooltip for Tk / CustomTkinter widgets.
        Usage: ToolTip(widget, "explanation text")
        """
        def __init__(self, widget, text, delay=400, bg="#2b2b2b", fg="white", font=("Segoe UI", 10)):
            self.widget = widget
            self.text = text
            self.delay = delay
            self.bg = bg
            self.fg = fg
            self.font = font

            # define BEFORE event binding to avoid AttributeError
            self.tip_window = None
            self._after_id = None

            # bind hover events
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

    ################################################################################################
    # MAIN WINDOW
    ################################################################################################
    window = ctk.CTk()
    window.title("Softdream")
    window.iconbitmap(r"icons\softdream.ico")
    window.geometry("1000x700")
    window.configure(bg="#1e1e1e")
    window.resizable(True, True)

    ################################################################################################
    # MENUBAR
    ################################################################################################
    menubar = ctk.CTkFrame(window, height=28, fg_color="#2d2d2d", corner_radius=0)
    menubar.pack(fill="x", side="top")

    menus = {
        "File": ["New", "Open", "Save", "Exit"],
        "Edit": ["Undo", "Redo", "Cut", "Copy", "Paste"],
        "View": ["Zoom In", "Zoom Out", "Reset Zoom"],
        "Run":  ["Run", "Debug"],
        "Help": ["About", "Documentation","license"]
    }

    ################################################################################################
    # DROPDOWNS
    ################################################################################################
    active_menu = {"menu": None}

    def open_dropdown(menu_name, button):
        if active_menu["menu"] is not None:
            active_menu["menu"].destroy()
            active_menu["menu"] = None
            if active_menu.get("last") == menu_name:
                return

        try:
            rel_x = button.winfo_rootx() - window.winfo_rootx()
            rel_y = button.winfo_rooty() + button.winfo_height() - window.winfo_rooty()
        except tk.TclError:
            rel_x = 0
            rel_y = menubar.winfo_height()

        dropdown = ctk.CTkFrame(window, fg_color="#252525", corner_radius=6, border_width=1,  
                                border_color="#3a3a3a")
        dropdown.place(x=rel_x, y=rel_y)

        for item_text in menus[menu_name]:
            item = ctk.CTkButton(
                dropdown,
                text=item_text,
                fg_color="transparent",
                hover_color="#0063af",
                text_color="#ededed",
                anchor="w",
                width=140,
                height=26,
                font=("Segoe UI", 12),
                corner_radius=0,
                command=lambda i=item_text: on_menu_select(i, dropdown)
            )
            item.pack(fill="x", padx=4, pady=1)

        dropdown.lift()
        window.update_idletasks() 

        active_menu["menu"] = dropdown
        active_menu["last"] = menu_name

    ################################################################################################
    # MENU BUTTONS
    ################################################################################################
    for menu_name in menus:
        btn = ctk.CTkButton(
            menubar,
            text=menu_name,
            fg_color="transparent",
            hover_color="#0063af",
            text_color="#d4d4d4",
            width=70,
            height=26,
            corner_radius=0,
            font=("Segoe UI", 12)
        )
        btn.pack(side="left", padx=1)
        btn.bind("<Button-1>", lambda e, name=menu_name, b=btn: open_dropdown(name, b))

    ################################################################################################
    # CLICK HANDLER FOR MENU ITEMS
    ################################################################################################
    def on_menu_select(item, dropdown):
        dropdown.destroy()
        active_menu["menu"] = None
        print(f"Selected: {item}")

        if item == "Exit":
            window.destroy()

    ################################################################################################
    # CLOSE DROPDOWN IF CLICK OUTSIDE
    ################################################################################################
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

        if (mx1 <= x_root <= mx2 and my1 <= y_root <= my2) or (mbx1 <= x_root <= mbx2 and mby1 <= y_root <= mby2):
            return

        active_menu["menu"].destroy()
        active_menu["menu"] = None

    window.bind("<Button-1>", close_on_click_outside)
    
    def clear_tree_focus(event):
        widget = event.widget
        if widget == tree:
            return
        current = widget
        is_descendant = False
        while current:
            if current == tree:
                is_descendant = True
                break
            try:
                current = current.master
            except:
                break
        if not is_descendant:
            tree.selection_remove(tree.selection())
            tree.focus("")
            tree.state(("!focus",))
    
    window.bind("<Button-1>", clear_tree_focus, add="+")

    #################################################################################################
    # STATUS BAR (PACKED EARLY TO AVOID LAYOUT ISSUES)
    #################################################################################################
    status_bar = ctk.CTkFrame(window, height=28, fg_color="#2d2d2d", corner_radius=0)
    status_bar.pack(fill="x", side="bottom")

    warnings_button = ctk.CTkButton(status_bar,text="Warnings",font=("Segoe UI",11),width=15,
                                    height=8, corner_radius=0, fg_color="#323232")
    warnings_button.pack(padx=(2,2),side="left",pady=(2,2))
    ToolTip(warnings_button,"Shows the number of warnings inside the file")

    problems_button = ctk.CTkButton(status_bar,text="Problems and Issues",font=("Segoe UI",11),
                                    width=15,height=8, corner_radius=0, fg_color="#323232")
    problems_button.pack(padx=(2,2),side="left",pady=(2,2))
    ToolTip(problems_button,"Shows the number of problems encountered inside the file")

    debug_configuration = ctk.CTkButton(status_bar,text="Select and Start Debug Configurations",
                                        font=("Segoe UI",11),width=15, height=8, corner_radius=0,
                                        fg_color="#323232")
    debug_configuration.pack(padx=(2,2),side="left",pady=(2,2))
    ToolTip(debug_configuration,"Shows automatic configuration for the selected language")

    Version_button = ctk.CTkButton(status_bar,text="Version 0.0.1 BETA",font=("Segoe UI",11),
                                    width=15,height=8, corner_radius=0, fg_color="#323232",
                                    command=open_version_license)
    Version_button.pack(padx=(2,2),side="right",pady=(2,2))
    ToolTip(Version_button, f"You are currently running on version{version}")

    Terminal_button = ctk.CTkButton(status_bar,text="Open Terminal",font=("Segoe UI",11),width=15,
                                    height=8, corner_radius=0,fg_color="#323232",
                                    command=open_terminal)
    Terminal_button.pack(padx=(2,2),side="right",pady=(2,2))
    ToolTip(Terminal_button, "Opens a new terminal, restricted by the device terminal type")

    #################################################################################################
    # SERVICES LEFTMOST BAR
    #################################################################################################
    services_bar = ctk.CTkFrame(window, width=50, fg_color="#131313", corner_radius=0)
    services_bar.pack_propagate(False)
    services_bar.pack(side="left", fill="y")

    search_photo   = ctk.CTkImage(light_image=Image.open(r"icons\zoom.ico"), size=(24, 24))
    open_photo     = ctk.CTkImage(light_image=Image.open(r"icons\open.ico"), size=(24, 24))
    settings_photo = ctk.CTkImage(light_image=Image.open(r"icons\settings.ico"), size=(24, 24))
    new_photo      = ctk.CTkImage(light_image=Image.open(r"icons\new.ico"), size=(24, 24))

    search_button = ctk.CTkButton(services_bar,text="",image=search_photo,width=36,height=36,
                                    corner_radius=5,fg_color="#131313",hover_color="#1f1f1f")
    search_button.pack(pady=5)
    ToolTip(search_button,"Searches inside the file for a specific key")

    open_button = ctk.CTkButton(services_bar,text="",image=open_photo,width=36,height=36,
                                    corner_radius=5,fg_color="#131313",hover_color="#1f1f1f")
    open_button.pack(pady=5)
    ToolTip(open_button, "Opens a file")

    settings_button = ctk.CTkButton(services_bar,text="",image=settings_photo,width=36,height=36,
                                    corner_radius=5,fg_color="#131313",hover_color="#1f1f1f")
    settings_button.pack(pady=5)
    ToolTip(settings_button, "Show IDE settings and preferences")

    new_button = ctk.CTkButton(services_bar,text="",image=new_photo,width=36,height=36,
                                    corner_radius=5,fg_color="#131313",hover_color="#1f1f1f")
    new_button.pack(pady=5)
    ToolTip(new_button,"Creates a new empty file")

    #################################################################################################
    # LEFT SIDEBAR FRAME
    #################################################################################################
    sidebar = tk.Frame(window, bg="#1e1e1e", width=360)
    sidebar.pack_propagate(False)
    sidebar.pack(side="left", fill="y")

    # Buttons
    run_btn = ctk.CTkButton(sidebar, text="Run and Debug", fg_color="#0063af", width=340, 
                             height=25, font=("Segoe UI semibold", 13))
    run_btn.pack(pady=(12, 2), padx=8, fill="x")
    open_btn = ctk.CTkButton(sidebar, text="Open Recent File", fg_color="#0063af", width=340,
                             height=25, font=("Segoe UI semibold", 13))
    open_btn.pack(pady=(8, 10), padx=8, fill="x")

    #################################################################################################
    # MAIN EDITOR AREA
    #################################################################################################
    editor_frame = tk.Frame(window, bg="#252526")
    editor_frame.pack(side="right", fill="both", expand=True)

    text_editor = tk.Text(
        editor_frame,
        font=("Courier New",13),
        bg="#252526",
        fg="#d4d4d4",
        insertbackground="#ffffff",
        borderwidth=0,
        padx=10,
        pady=10
    )
    text_editor.pack(fill="both", expand=True)
    text_editor.insert("1.0", "# Softdream Code Editor")

    #################################################################################################
    # FILE EXPLORER TREEVIEW (Optimized & Fast)
    #################################################################################################

    workspace_path = filedialog.askdirectory(title="Select a workspace folder for your code")
    if not workspace_path:
        workspace = Path.home() / "softdream"
        workspace.mkdir(exist_ok=True)
    else:
        workspace = Path(workspace_path)

    file_frame = tk.Frame(sidebar, bg="#1e1e1e", relief="flat", bd=0)
    file_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    tree = ttk.Treeview(file_frame, show="tree")
    tree.pack(fill="both", expand=True)

    style = ttk.Style()
    style.theme_use('default')
    style.configure("Treeview",
                    background="#1e1e1e",
                    foreground="#d4d4d4",
                    fieldbackground="#1e1e1e",
                    font=("Segoe UI", 11),
                    borderwidth=0,
                    lightcolor="#1e1e1e",
                    darkcolor="#1e1e1e",
                    rowheight=28)
    style.map("Treeview", background=[('selected', '#0e639c')])
    style.configure("Treeview.Heading",
                    background="#1e1e1e",
                    foreground="#d4d4d4",
                    relief="flat",
                    borderwidth=0)
    style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

    def create_padded_icon(ico_path, icon_size=(16, 16), padding=8):
        try:
            icon_img = Image.open(ico_path).convert("RGBA").resize(icon_size)
            img = Image.new('RGBA', (icon_size[0] + padding, icon_size[1]), (0, 0, 0, 0))
            img.paste(icon_img, (0, 0), icon_img)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Warning: Could not load icon {ico_path}: {e}")
            img = Image.new('RGBA', (icon_size[0] + padding, icon_size[1]), (0, 0, 0, 0))
            return ImageTk.PhotoImage(img)

    folder_img = create_padded_icon(r"icons\folder.ico")
    file_img = create_padded_icon(r"icons\file.ico")
    txt_img = create_padded_icon(r"icons\txt.ico")
    c_files = create_padded_icon(r"icons\c.ico")
    cpp_files = create_padded_icon(r"icons\cpp.ico")
    json_files = create_padded_icon(r"icons\json.ico")

    icons = {
        "folder": folder_img,
        "file": file_img,
        ".txt": txt_img,
        ".c": c_files,
        ".cpp": cpp_files,
        ".json": json_files
    }

    allowed_extensions = {".py", ".txt", ".c", ".cpp", ".json"}

    def insert_node_lazy(parent, path: Path):
        try:
            if path.name.startswith("."):
                return None

            if path.is_dir():
                node = tree.insert(parent, "end", text=path.name, image=icons["folder"], open=False)
                tree.insert(node, "end", text="loading...")  # lazy-loading placeholder
            else:
                if path.suffix not in allowed_extensions:
                    return None
                img = icons.get(path.suffix, icons["file"])
                node = tree.insert(parent, "end", text=path.name, image=img)

            return node
        except (PermissionError, FileNotFoundError):
            return None

    def load_children_batch(item, children_paths, batch_size=50, delay=30):
        if not children_paths:
            return
        
        batch = children_paths[:batch_size]
        remaining = children_paths[batch_size:]
        
        for path in batch:
            insert_node_lazy(item, path)
        
        if remaining:
            window.after(delay, lambda: load_children_batch(item, remaining, batch_size, delay))

    def load_children(event):
        item = tree.focus()
        if not item:
            return

        children = tree.get_children(item)
        if children and tree.item(children[0], "text") == "loading...":
            tree.delete(children[0])
            path = get_path(item)
            try:
                all_children = list(Path(path).iterdir())
                children_paths = sorted(all_children, key=lambda p: (not p.is_dir(), p.name.lower()))
                MAX_ITEMS = 300
                if len(children_paths) > MAX_ITEMS:
                    children_paths = children_paths[:MAX_ITEMS]
                load_children_batch(item, children_paths)
            except (PermissionError, FileNotFoundError):
                pass

    tree.bind("<<TreeviewOpen>>", load_children)

    def get_path(node_id):
        parts = []
        current = node_id
        while current:
            parts.insert(0, tree.item(current)["text"])
            current = tree.parent(current)
        if len(parts) == 1:
            return str(workspace)
        else:
            return str(workspace / Path(*parts[1:]))

    insert_node_lazy("", workspace)

    def open_file(event):
        selected = tree.selection()
        if not selected:
            return
        node = selected[0]
        path_str = get_path(node)
        path = Path(path_str)
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text_editor.delete("1.0", "end")
                    text_editor.insert("1.0", f.read())
            except Exception as e:
                text_editor.delete("1.0", "end")
                text_editor.insert("1.0", f"# Cannot open file: {e}")

    tree.bind("<Double-1>", open_file)


    #################################################################################################
    # CONFIGURATION
    #################################################################################################
    window.mainloop()

main()