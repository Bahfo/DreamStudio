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


class GettingStartedTab:
    def __init__(self, welcome_tab):
        welcomeTabFrame = ctk.CTkFrame(welcome_tab, fg_color=["#FFFFFF","#1F1F1F"], corner_radius=0, border_width=0)
        welcomeTabFrame.pack(fill="both", expand=True)

        welcomeTabLabel = ctk.CTkLabel(welcomeTabFrame, text="Get Started With", font=("Microsoft YaHei UI",22),
                                       text_color=["#004073","#97C0FF"], fg_color=["#FFFFFF","#1F1F1F"],
                                       anchor="w", justify="left")
        welcomeTabLabel.place(x = 20, y = 15)

        welcomeTabLabel2 = ctk.CTkLabel(welcomeTabFrame, text="DreamStudio", font=("Microsoft YaHei UI",46),
                                       text_color=["#004073","#97C0FF"], fg_color=["#FFFFFF","#1F1F1F"],
                                       anchor="w", justify="left")
        welcomeTabLabel2.place(x = 20, y = 50)

        versionLabel = ctk.CTkLabel(welcomeTabFrame, text="version 1.0 - 0.0.1 BETA", font=("Microsoft YaHei UI",14),
                                       text_color=["#004073","#97C0FF"], fg_color=["#FFFFFF","#1F1F1F"],
                                       anchor="w", justify="left")
        versionLabel.place(x = 320, y = 80)

        whats_new_label = ctk.CTkLabel(welcomeTabFrame, font=("Microsoft YaHei UI",16),
                                       text_color=["#730047","#FF97E2"], fg_color=["#FFFFFF","#1F1F1F"],
                                       text="Discover Stronger Tools to Build Your Next Dream App", 
                                       anchor="w", justify="left")
        whats_new_label.place(x = 60, y = 150)

        welcomeTabLabel3 = ctk.CTkLabel(welcomeTabFrame, text="Take a tour in DreamStudio to help you get started",
                                        font=("Microsoft YaHei UI",13), text_color=["#000000","#FFFFFF"], 
                                        fg_color=["#FFFFFF","#1F1F1F"], anchor="w", justify="left")
        welcomeTabLabel3.place(x = 20, y = 250)

        welcomeTabLabel4 = LinkLabel(welcomeTabFrame, text="Start My Tour!", corner_radius=0, font=("Segoe UI",12),
                                     width=80, height=18)
        welcomeTabLabel4.place(x = 340, y = 255)

        welcomeTabLabel5 = ctk.CTkLabel(welcomeTabFrame, text="Or read the full documentation for further information",
                                        font=("Microsoft YaHei UI",13), text_color=["#000000","#FFFFFF"], 
                                        fg_color=["#FFFFFF","#1F1F1F"], anchor="w", justify="left")
        welcomeTabLabel5.place(x = 20, y = 275)

        welcomeTabLabel6 = LinkLabel(welcomeTabFrame, text="Read the Documentation", corner_radius=0,
                                     font=("Segoe UI",12), width=136, height=18)
        welcomeTabLabel6.place(x = 362, y = 280)

        ########## SOME RANDOM BUTTONS TO HELP TOURING ##########
        copyright_label = ctk.CTkLabel(welcomeTabFrame, font=("Microsoft YaHei UI",10),
                                       text_color=["#000000","#FFFFFF"], fg_color=["#FFFFFF","#1F1F1F"],
                                       text="Copyright 2026 © DreamStudio - All Rights Reserved",
                                       anchor="w", justify="left")
        copyright_label.place(x = 20, y = 600)


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


def open_file_from_tree(file_path, status_button, tab_switch, editor_font, mode):
    """Open a file from the treeview in a new tab
    
    Args:
        file_path: Path to the file to open
        status_button: Status bar widget to show messages
        tab_switch: The tab switcher widget
        editor_font: Font for the editor
        mode: Dark mode boolean
    """
    import os
    
    # Verify it's a file, not a directory
    if not os.path.isfile(file_path):
        messagebox.showwarning("Invalid", "Selected item is not a file")
        return
    
    if status_button:
        status_button.configure(text=f"Opening: {os.path.basename(file_path)}...")
    
    try:
        # Try to open with UTF-8 encoding
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Create new tab
        tab_name = add_new_text_tab(tab_switch, editor_font, mode)
        
        if tab_name:
            target_editor = current_session_editors_open.get(tab_name)
            
            if target_editor:
                # Rename tab to filename for clarity
                file_name = os.path.basename(file_path)
                file_name_with_spaces = "   " + file_name + "   "
                tab_switch.rename(tab_name, file_name_with_spaces)
                
                # Insert content
                target_editor.content.delete("1.0", "end")
                target_editor.content.insert("1.0", content)
                
                # Store file path for later reference (optional)
                target_editor.file_path = file_path
                
                if status_button:
                    status_button.configure(text=f"Opened: {file_path}")
    
    except UnicodeDecodeError as e:
        messagebox.showerror(
            "Encoding Error",
            f"File is not UTF-8 encoded.\n\n"
            f"Error: {str(e)}\n\n"
            f"Only UTF-8 files are supported."
        )
        if status_button:
            status_button.configure(text="Failed: Unsupported encoding")
    
    except Exception as e:
        messagebox.showerror(
            "Error",
            f"Could not open file:\n{str(e)}"
        )
        if status_button:
            status_button.configure(text="Operation Failed")


def on_close_tab_click(tabSwitch, event=None):
    """Close the currently selected tab"""
    current_tab = tabSwitch.get()

    if not current_tab:
        messagebox.showwarning("No Tab", "No tab is currently selected")
        return

    if current_tab in current_session_editors_open:
        del current_session_editors_open[current_tab]

    tabSwitch.delete(current_tab)

    if len(tabSwitch._name_list) == 0:
        tabSwitch._segmented_button.grid_forget()


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
