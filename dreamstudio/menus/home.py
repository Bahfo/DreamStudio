"""
The home menu application functionality layer
\nHandles home menu services, and calls second layer support if required
"""
import os
import tkinter as tk
import customtkinter as ctk


from typing import Any
from dreamstudio.texteditor import Config
from tkinter import filedialog, messagebox
from dreamstudio.texteditor import Editor, Languages

# Variables
tab_count = 0
current_session_editors_open = {}

# Popups Classes
class OpenPopup(ctk.CTkFrame):
    """
    Dropdown popup menu attached to a button
    """
    def __init__(self, master, options: dict[str, Any], width: int = 200):
        super().__init__(master, width=width, border_color="#9D9D9D", border_width=1,
                         fg_color=["#F2F2F2","#252525"], corner_radius=0)

        self.background_color = "#F2F2F2" if ctk.get_appearance_mode() == 'light' else "#252525"
        self.triangle_height = 10
        self.options = options
        self.master = master
        self.width = width

        self._populate()
        self.master.bind("<Button-1>", self._checkIfMouseLeft, add="+")

    def _populate(self):
        """
        Populate the widget with buttons
        """
        for label, command in self.options.items():
            ctk.CTkButton(
                self,
                anchor="w",
                text=label,
                width=196,
                height=20,
                font=("Segoe UI",12),
                command=command,
                corner_radius=0,
                border_width=0,
                fg_color=self.cget('fg_color'),
                text_color=["#252525","#F5F5F5"]
            ).pack(fill="x", padx=2, pady=1)

    def _checkIfMouseLeft(self, event):
        """
        Check if mouse has left the menu area and hide menus accordingly.
        """
        
        try:
            x1 = self.winfo_rootx()
            y1 = self.winfo_rooty()
            x2 = x1 + self.winfo_width()
            y2 = y1 + self.winfo_height()

            mouse_x = self.winfo_pointerx()
            mouse_y = self.winfo_pointery()

            if not (x1 <= mouse_x <= x2 and y1 <= mouse_y <= y2):
                self.destroy()
                self.master.unbind_all("<Button-1>")
        except tk.TclError:
            pass


class Notifications(ctk.CTkFrame):
    """
    Same as a popup class, but differs in contents.

    Made differently to control each without worrying about an abstraction layer
    """
    def __init__(self, master, title, content, width: int = 200):
        super().__init__(master, width=width, border_color="#9D9D9D", border_width=1,
                         fg_color=["#F2F2F2","#252525"], corner_radius=0)

        self.triangle_height = 10
        self.label = title
        self.content = content
        self.master = master
        self.width = width

        self.master.bind("<Button-1>", self._checkIfMouseLeft, add="+")

    def new_notification(self):
        """
        Add a new notification to the menu. It also notifies the user
        """
        holder = ctk.CTkFrame()
        

    def _checkIfMouseLeft(self, event):
        """
        Check if mouse has left the menu area and hide menus accordingly.
        """
        
        try:
            x1 = self.winfo_rootx()
            y1 = self.winfo_rooty()
            x2 = x1 + self.winfo_width()
            y2 = y1 + self.winfo_height()

            mouse_x = self.winfo_pointerx()
            mouse_y = self.winfo_pointery()

            if not (x1 <= mouse_x <= x2 and y1 <= mouse_y <= y2):
                self.destroy()
                self.master.unbind_all("<Button-1>")
        except tk.TclError:
            pass


def add_new_text_tab(tabSwitch, editor_initial_font, mode):
    global tab_count

    if tab_count >= 10:
        messagebox.showerror("Tabs Construction Error", "Cannot create more than 10 tabs")
        return None

    tab_count += 1
    tab_name = f"    Untitled-{tab_count}    "
    tabSwitch.add(tab_name)

    new_editor = Editor(
        tabSwitch.tab(tab_name),
        language=Languages.PYTHON,
        font=editor_initial_font,
        showpath=True,
        darkmode=mode,
        uifont=("Segoe UI", 11)
    )

    new_editor.pack(fill="both", expand=True)

    current_session_editors_open[tab_name] = new_editor
    tabSwitch.set(tab_name)

    return tab_name


def open_current_file(status_button,
                      current_session_editors,
                      tab_switch,
                      editor_font,
                      mode):
    current_file = filedialog.askopenfilename(title="Select an existing file")
    if not current_file:
        return

    if status_button:
        status_button.configure(text="Opening file...")

    try:
        with open(current_file, "r", encoding="utf-8") as f:
            content = f.read()

        tab_name = add_new_text_tab(tab_switch, editor_font, mode)

        if tab_name:
            target_editor = current_session_editors_open.get(tab_name)

            if target_editor:
                target_editor.content.delete("1.0", "end")
                target_editor.content.insert("1.0", content)
                
                if status_button:
                    status_button.configure(text=f"Opened: {current_file}")
                    
    except Exception as e:
        messagebox.showerror("Error", f"Could not open file:\n{e}")
        if status_button:
            status_button.configure(text="Operation Failed")

def update_all_editors_theme(mode):

    for editor in current_session_editors_open.values():

        editor.darkmode = mode
        editor.settings = Config(
            editor,
            editor.config_file,
            mode,
            None,
            None
        )

        editor.theme = editor.settings.theme
        editor.configure(bg=editor.theme.border)


# def save_temporary_file():


def open_menu_popup(event, root, button, options, x, y):
    popup = OpenPopup(master=root, options=options)
    popup.place(x=x, y=y)
