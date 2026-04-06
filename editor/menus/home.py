"""
The home menu application functionality layer
\nHandles home menu services, and calls second layer support if required
"""

import os
import tkinter as tk
import customtkinter as ctk


from typing import Any
from editor.texteditor import Config
from tkinter import filedialog, messagebox
from editor.utils.linkLabel import LinkLabel
from editor.texteditor import Editor, Languages
from editor.utils.largeButton import LargeButton

# Variables
tab_count = 0
naming_counter = 0
notifications_class = {}
current_session_editors_open = {}
current_session_editors_content = {}
image = "assets/system/styles.png"


# Popups Classes
class OpenPopup(ctk.CTkFrame):
    """
    Dropdown popup menu attached to a button
    """

    def __init__(self, master, options: dict[str, Any], width: int = 200):
        super().__init__(
            master,
            width=width,
            border_color="#9D9D9D",
            border_width=1,
            fg_color=["#F2F2F2", "#252525"],
            corner_radius=0,
        )

        self.background_color = (
            "#F2F2F2" if ctk.get_appearance_mode() == "light" else "#252525"
        )
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
                font=("Segoe UI", 12),
                command=command,
                corner_radius=0,
                border_width=0,
                fg_color=self.cget("fg_color"),
                text_color=["#252525", "#F5F5F5"],
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


def open_menu_popup(event, root, button, options, x, y):
    popup = OpenPopup(master=root, options=options)
    popup.place(x=x, y=y)


class Notifications(ctk.CTkFrame):
    """
    Popup notification menu.
    Closes automatically if the user clicks outside.
    """

    def __init__(self, master, title, content, width: int = 250):
        super().__init__(
            master,
            width=width,
            border_color="#9D9D9D",
            border_width=1,
            fg_color=["#F2F2F2", "#252525"],
            corner_radius=0,
        )
        self.master = master
        self.width = width

        self.title_label = ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=12, weight="bold")
        )
        self.title_label.pack(padx=10, pady=(10, 2))

        self.content_label = ctk.CTkLabel(self, text=content, font=ctk.CTkFont(size=10))
        self.content_label.pack(padx=10, pady=(0, 10))

        self._bind_id = self.master.bind(
            "<Button-1>", self._check_if_mouse_left, add="+"
        )

    def _check_if_mouse_left(self, event):
        try:
            x1 = self.winfo_rootx()
            y1 = self.winfo_rooty()
            x2 = x1 + self.winfo_width()
            y2 = y1 + self.winfo_height()

            if not (x1 <= event.x_root <= x2 and y1 <= event.y_root <= y2):
                self.destroy()
                self.master.unbind("<Button-1>", self._bind_id)
        except tk.TclError:
            pass


def open_notifications(root_window, title, content):
    """Creates and displays a notification popup at (x, y)"""
    popup = Notifications(master=root_window, title=title, content=content)
    popup.place(relx=0.87, rely=0.855)


class GettingStartedTab:
    def __init__(self, welcome_tab):
        welcomeTabFrame = ctk.CTkFrame(
            welcome_tab,
            fg_color=["#FFFFFF", "#1F1F1F"],
            corner_radius=0,
            border_width=0,
        )
        welcomeTabFrame.pack(fill="both", expand=True)

        welcomeTabLabel = ctk.CTkLabel(
            welcomeTabFrame,
            text="Get Started With",
            font=("Microsoft YaHei UI", 22),
            text_color=["#004073", "#97C0FF"],
            fg_color=["#FFFFFF", "#1F1F1F"],
            anchor="w",
            justify="left",
        )
        welcomeTabLabel.place(x=20, y=15)

        welcomeTabLabel2 = ctk.CTkLabel(
            welcomeTabFrame,
            text="DreamStudio",
            font=("Microsoft YaHei UI", 46),
            text_color=["#004073", "#97C0FF"],
            fg_color=["#FFFFFF", "#1F1F1F"],
            anchor="w",
            justify="left",
        )
        welcomeTabLabel2.place(x=20, y=50)

        versionLabel = ctk.CTkLabel(
            welcomeTabFrame,
            text="version 1.0 - 0.0.1 BETA",
            font=("Microsoft YaHei UI", 14),
            text_color=["#004073", "#97C0FF"],
            fg_color=["#FFFFFF", "#1F1F1F"],
            anchor="w",
            justify="left",
        )
        versionLabel.place(x=320, y=80)

        whats_new_label = ctk.CTkLabel(
            welcomeTabFrame,
            font=("Microsoft YaHei UI", 16),
            text_color=["#730047", "#FF97E2"],
            fg_color=["#FFFFFF", "#1F1F1F"],
            text="Discover Stronger Tools to Build Your Next Dream App",
            anchor="w",
            justify="left",
        )
        whats_new_label.place(x=60, y=150)

        welcomeTabLabel3 = ctk.CTkLabel(
            welcomeTabFrame,
            text="Take a tour in DreamStudio to help you get started",
            font=("Microsoft YaHei UI", 13),
            text_color=["#000000", "#FFFFFF"],
            fg_color=["#FFFFFF", "#1F1F1F"],
            anchor="w",
            justify="left",
        )
        welcomeTabLabel3.place(x=20, y=250)

        welcomeTabLabel4 = LinkLabel(
            welcomeTabFrame,
            text="Start My Tour!",
            corner_radius=0,
            font=("Segoe UI", 12),
            width=80,
            height=18,
        )
        welcomeTabLabel4.place(x=340, y=255)

        welcomeTabLabel5 = ctk.CTkLabel(
            welcomeTabFrame,
            text="Or read the full documentation for further information",
            font=("Microsoft YaHei UI", 13),
            text_color=["#000000", "#FFFFFF"],
            fg_color=["#FFFFFF", "#1F1F1F"],
            anchor="w",
            justify="left",
        )
        welcomeTabLabel5.place(x=20, y=275)

        welcomeTabLabel6 = LinkLabel(
            welcomeTabFrame,
            text="Read the Documentation",
            corner_radius=0,
            font=("Segoe UI", 12),
            width=136,
            height=18,
        )
        welcomeTabLabel6.place(x=362, y=280)

        ########## SOME RANDOM BUTTONS TO HELP TOURING ##########
        copyright_label = ctk.CTkLabel(
            welcomeTabFrame,
            font=("Microsoft YaHei UI", 10),
            text_color=["#000000", "#FFFFFF"],
            fg_color=["#FFFFFF", "#1F1F1F"],
            text="Copyright 2026 © DreamStudio - All Rights Reserved",
            anchor="w",
            justify="left",
        )
        copyright_label.place(x=20, y=600)


def add_new_text_tab(tabSwitch, editor_initial_font, mode):
    """
    This documentation is powered by _autoDocstring_.
    _summary_
    Adds a new tab with cupcake editor inside

    Args:
        tabSwitch (_type_): The tab manager to reference.
        editor_initial_font (_type_): the font of the editor (global variable)
        mode (_type_): boolean (True/False) for Dark/Light.
    """
    global tab_count
    global naming_counter

    if tab_count >= 10:
        messagebox.showerror(
            "Tabs Construction Error", "Cannot create more than 10 tabs"
        )
        return None

    tab_count += 1
    naming_counter += 1
    tab_name = f"    Untitled-{naming_counter}    "
    tabSwitch.add(tab_name)

    # Immediately grid the tab frame so the editor can be packed inside
    tab_frame = tabSwitch.tab(tab_name)
    tab_frame.grid(row=0, column=0, sticky="nsew")
    tabSwitch.update_idletasks()  # <- ensures layout is processed immediately

    new_editor = Editor(
        tab_frame,
        language=Languages.PYTHON,
        font=editor_initial_font,
        showpath=True,
        darkmode=mode,
        uifont=("Segoe UI", 11),
    )
    new_editor.pack(fill="both", expand=True)

    editor_id = id(new_editor)
    current_session_editors_open[editor_id] = new_editor
    new_editor._tab_name = tab_name

    tabSwitch.set(tab_name)  # set the tab after the frame is gridded

    return tab_name


def open_current_file(
    status_button, current_session_editors, tab_switch, editor_font, mode
):
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
            target_editor = next(
                (
                    e
                    for e in current_session_editors_open.values()
                    if e._tab_name == tab_name
                ),
                None,
            )

            if target_editor:
                # Here comes the mess: structure is so bad I can't look at it anymore
                file_name = os.path.basename(current_file)
                file_name_with_spaces = "   " + file_name + "   "
                new_tab_name = (
                    file_name_with_spaces  # Adding a new variable to fix naming errors
                )
                target_editor._tab_name = new_tab_name
                tab_switch.rename(tab_name, new_tab_name)
                tab_name = new_tab_name

                # Re-aliasing the name to prevent crashing
                tab_name = new_tab_name
                tab_switch.set(tab_name)

                def activate_and_load(
                    name=tab_name, editor=target_editor, data=content
                ):
                    """
                    An insider function that all its purpose to update the idletasks of GUI simultaneously
                    without the worry about using threaded (after) function. This is an internal function
                    and has no outer usage.
                    """
                    editor.content.delete("1.0", "end")
                    editor.content.insert("1.0", data)

                activate_and_load()

                target_editor.file_path = current_file

                if status_button:
                    status_button.configure(text=f"Opened: {new_tab_name}")

    except Exception as e:
        messagebox.showerror("Error", f"Could not open file:\n{e}")
        if status_button:
            status_button.configure(text="Operation Failed")


def open_file_from_tree(file_path, status_button, tab_switch, editor_font, mode):
    """Open a file from the treeview in a new tab

    Args:
        file_path: Path to the file to open
        status_button: Status bar widget to show messages
        tab_switch: The tab switcher widget
        editor_font: Font for the editor
        mode: Dark mode boolean
    """

    # Verify it's a file, not a directory
    if not os.path.isfile(file_path):
        messagebox.showwarning("Invalid", "Selected item is not a file")
        return

    if status_button:
        status_button.configure(text=f"Opening: {os.path.basename(file_path)}...")

    # Check if the file is already open
    for editor in current_session_editors_open.values():
        if getattr(editor, "file_path", None) == file_path:
            tab_switch.after(10, lambda name=editor._tab_name: tab_switch.set(name))

            if status_button:
                status_button.configure(text=f"Focused: {file_path}")

            return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tab_name = add_new_text_tab(tab_switch, editor_font, mode)
        current_session_editors_content[tab_name] = content

        if tab_name:
            target_editor = next(
                (
                    e
                    for e in current_session_editors_open.values()
                    if e._tab_name == tab_name
                ),
                None,
            )

            if target_editor:
                # Here comes the mess: structure is so bad I can't look at it anymore
                file_name = os.path.basename(file_path)
                file_name_with_spaces = "   " + file_name + "   "
                new_tab_name = (
                    file_name_with_spaces  # Adding a new variable to fix naming errors
                )
                target_editor._tab_name = new_tab_name
                tab_switch.rename(tab_name, new_tab_name)
                tab_name = new_tab_name

                # Re-aliasing the name to prevent crashing
                tab_name = new_tab_name
                tab_switch.set(tab_name)

                def activate_and_load(
                    name=tab_name, editor=target_editor, data=content
                ):
                    """
                    An insider function that all its purpose to update the idletasks of GUI simultaneously
                    without the worry about using threaded (after) function. This is an internal function
                    and has no outer usage.
                    """
                    editor.content.delete("1.0", "end")
                    editor.content.insert("1.0", data)

                activate_and_load()

                target_editor.file_path = file_path

                if status_button:
                    status_button.configure(text=f"Opened: {new_tab_name}")

    except UnicodeDecodeError as e:
        messagebox.showerror(
            "Encoding Error",
            f"File is not UTF-8 encoded.\n\n"
            f"Error: {str(e)}\n\n"
            f"Only UTF-8 files are supported.",
        )
        if status_button:
            status_button.configure(text="Failed: Unsupported encoding")

    except Exception as e:
        messagebox.showerror("Error", f"Could not open file:\n{str(e)}")
        if status_button:
            status_button.configure(text="Operation Failed")


def on_close_tab_click(tabSwitch, event=None):
    """Close the currently selected tab and cleanup memory"""
    global tab_count
    current_tab = tabSwitch.get()

    if not current_tab:
        if len(tabSwitch._name_list) == 0:
            tab_count = 0
        return

    for key, editor in list(current_session_editors_open.items()):
        if hasattr(editor, "_tab_name") and editor._tab_name == current_tab:
            del current_session_editors_open[key]
            break

    try:
        tabSwitch.delete(current_tab)
    except Exception as e:
        print(f"Tab deletion error: {e}")

    if tab_count > 0:
        tab_count -= 1

    if len(tabSwitch._name_list) == 0:
        tabSwitch._segmented_button.grid_forget()
        tab_count = 0


def update_all_editors_theme(mode):

    for editor in current_session_editors_open.values():

        editor.darkmode = mode
        editor.settings = Config(editor, editor.config_file, mode, None, None)

        editor.theme = editor.settings.theme
        editor.configure(bg=editor.theme.border)


def save_current_opened_file(tab_switch, save_popup=None):
    current_tab = tab_switch.get()

    if not current_tab:
        return  # No tabs opened

    # Finding the editor instance linked to the current tab
    active_editor = None
    for editor in current_session_editors_open.values():
        if getattr(editor, "_tab_name", None) == current_tab:
            active_editor = editor
            break

    if not active_editor:
        return

    # File already exists (Overwrite)
    if hasattr(active_editor, "file_path") and active_editor.file_path:
        try:
            content = active_editor.content.get("1.0", "end-1c")
            with open(active_editor.file_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"Successfully saved to {active_editor.file_path}")

        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save file:\n{e}")

    # New file created via add_new_text_tab (Prompt User)
    else:
        if save_popup:
            save_popup.target_editor = active_editor
            save_popup.tab_switch = tab_switch
            save_popup.show()
        else:
            messagebox.showwarning(
                "Notice", "Save functionality is missing the popup reference."
            )
