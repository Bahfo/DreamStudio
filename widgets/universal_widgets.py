# Written by Bahaa Nofal - 11/12/2025
# A special implementation of CustomTkinter suitable for DreamStudio
# Universal Widgets: Custom IronKinter script for building DreamStudio's
# environment. DO NOT PUBLISH OR COPY IN ANY METHOD OR WAY BY ANY MEAN,
# THIS SCRIPT IS ACCESIABLE ONLY UNDER THE AGREEMENT OF A DEVELOPER
# WORKING IN DREAMSTUIO'S ENVIRONMENT.

"""
COPYRIGHT 2026 DREAMSTUDIO - EX_TECHNOLOGIES - ALL RIGHTS RESREVED
Ironkinter is a supplementary header file wrapped above customtkinter
that imporves widgets creation, adds additional widgets, and animations.

The above copyright shall be included in all copies or substantial 
portions of the software.

Please note that DreamStudio's universal widgets wrappers is not a 
subject to publish. You got access to this file only as a developer
under the DreamStudio's agreement. The free publishable version and
edited for user experience is available under Ironkinter's framework,
which is a general purpose wrapper around tkinter that improves overall
performance, increasing thread acceptability and adds the same widgets
from DreamStudio's development environment. 
"""

import tkinter as tk
from PIL import Image
import customtkinter as ctk
from typing import List, Dict
from typing import List, Dict, Any
from tkinter import messagebox as mb

########################################################################################
# MENUS BUILDERS
########################################################################################
class HomeToolbarBuilder:
    def __init__(self, parent, parent_color, logic_ref):
        """
        parent       → where to place buttons (your homeFrame)
        parent_color → fg_color for buttons
        mode         → light/dark theme logic
        logic_ref    → reference to main class (for callbacks)
        """
        self.parent = parent
        self.parent_color = parent_color
        self.logic = logic_ref

        self._icon_cache = {}  # cache paths to avoid repeated loading
        self._create_buttons()
        self._create_separators()

    def _load_icon(self, path):
        """Cache image paths (do not open CTkImage here)"""
        if path not in self._icon_cache:
            self._icon_cache[path] = path  # store string path
        return self._icon_cache[path]

    def _create_buttons(self):
        """Defines and creates all buttons using a single loop."""
        buttons = [
        ("newFile", VerticalButton, r"icons\system\new_file.png", " New Tab ",
        5, 5),
        ("newMacro", VerticalButton, r"icons\system\new_macro.png", " New Code",
        75, 5),
        ("openCode", VerticalButton, r"icons\system\open_code.png", "Open Code",
        152, 5),
        ("refreshWorkspace", HorizontalButton, r"icons\system\refresh_workspace.png",
         "Refresh Files", 230, 7),
        ("saveAll", HorizontalButton, r"icons\system\save_all.png", "Save All Files",
        230, 37),
        ("pasteBtn", VerticalButton, r"icons\system\paste.png", "Paste Code",
        350, 5),
        ("cutBtn", HorizontalButton, r"icons\system\cut.png", " Cut Codes",
        428, 7),
        ("copyBtn", HorizontalButton, r"icons\system\copy.png", " Copy Codes",
        428, 37),
        ("undoBtn", HorizontalButton, r"icons\system\undo.png", "Undo Action",
        538, 7),
        ("redoBtn", HorizontalButton, r"icons\system\redo.png", "Redo Action",
        538, 37),
        ("deleteBtn", HorizontalButton, r"icons\system\delete.png", "Delete Codes",
        648, 7),
        ("replaceBtn", HorizontalButton, r"icons\system\replace.png", "Find/Replace",
        648, 37),
        ("syntaxBtn", VerticalButton, r"icons\system\syntax.png", "Configure \nSyntax",
        770, 5)]

        for item in buttons:
            if len(item) == 6:
                attr, widget, img, text, x, y = item
                command = None
            else:
                attr, widget, img, text, x, y, method_name = item
                command = getattr(self.logic, method_name)

            btn = widget(
                self.parent,
                image_path=self._load_icon(img),
                text=text,
                font=("Segoe UI", 12),
                fg_color=self.parent_color,
                hover_color="#3a3a3a",
                command=command,
            )
            setattr(self, attr, btn)
            btn.place(x=x, y=y)

    def _create_separators(self):
        """Separators also created automatically."""
        separators = [("vertical_sep_1", 340, 7), ("vertical_sep_2", 760, 7)]
        for name, x, y in separators:
            sep = ctk.CTkFrame(
                self.parent,
                bg_color="transparent",
                width=2,
                height=75,
                corner_radius=0,
            )
            setattr(self, name, sep)
            sep.place(x=x, y=y)


class ToolsBarBuilder:
    def __init__(self, parent, parent_color, logic_ref):
        self.parent = parent
        self.parent_color = parent_color
        self.logic = logic_ref

        self._icon_cache = {}
        self._create_buttons()

    def _load_icon(self, path):
        """Cache image paths (do not open CTkImage here)"""
        if path not in self._icon_cache:
            self._icon_cache[path] = path
        return self._icon_cache[path]

    def _create_buttons(self):

        buttons = [
        ("explorBtn", VerticalButton, r"icons\system\solution.png", " Solution\nExplorer",
        5, 5),
        ("boxBtn", VerticalButton, r"icons\system\tools.png", "Open\n ToolBox ",
        75, 5),
        ("managerBtn", VerticalButton, r"icons\system\manager.png", "Workspace\nManager",
        148, 5),
        ("propertiesBtn", VerticalButton, r"icons\system\properties.png", "Properties\nWindow",
        228, 5),
        ("vertical_sep_3", "separator", None, None,
        304, 7),
        ("openTerminalBtn", VerticalButton, r"icons\system\terminal.png", "Open\nTerminal",
        314, 5),
        ("cmdWindowBtn", VerticalButton, r"icons\system\command.png", "Command\nWindow",
        382, 5),
        ("resourcesBtn", VerticalButton, r"icons\system\resources.png", "Manage\nResources",
        457, 5),
        ("containerBtn", VerticalButton, r"icons\system\container.png", "Container\nWindow",
        529, 5),
        ("tasksBtn", VerticalButton, r"icons\system\tasks.png", "Manage\nTasks",
        600, 5),
        ("vertical_sep_4", "separator", None, None,
        664, 7),
        ("gitBtn", VerticalButton, r"icons\system\git.png", "Repository\nManager",
        674, 5),
        ("gitChangesBtn", HorizontalButton, r"icons\system\gitchanges.png", "Git Changes",
        746, 7),
        ("githubBtn", HorizontalButton, r"icons\system\github.png", "View Github",
        746, 37)]

        for item in buttons:
            name = item[0]
            widget = item[1]
            x = item[4]
            y = item[5]

            if widget == "separator":
                sep = ctk.CTkFrame(
                    self.parent,
                    bg_color="transparent",
                    width=2,
                    height=75,
                    corner_radius=0,
                )
                setattr(self, name, sep)
                sep.place(x=x, y=y)
                continue

            _, widget, img, text, x, y = item
            btn = widget(
                self.parent,
                image_path=self._load_icon(img),
                text=text,
                font=("Segoe UI", 12),
                fg_color=self.parent_color,
                hover_color="#3a3a3a",
            )
            setattr(self, name, btn)
            btn.place(x=x, y=y)


class DatabasesToolbarBuilder:
    def __init__(self, parent, parent_color, mode, logic_ref):
        """
        parent       → where to place buttons (your homeFrame)
        parent_color → fg_color for buttons
        mode         → light/dark theme logic
        logic_ref    → reference to main class (for callbacks)
        """
        self.parent = parent
        self.parent_color = parent_color
        self.logic = logic_ref

        self._icon_cache = {}
        self._create_buttons()

    def _load_icon(self, path):
        """Cache image paths (do not open CTkImage here)"""
        if path not in self._icon_cache:
            self._icon_cache[path] = path
        return self._icon_cache[path]

    def _create_buttons(self):
        """Defines and creates all buttons using a single loop."""
        buttons = [
        ("databaseBtn", VerticalButton, r"icons\system\database.png", "Manage\nDatabases",
        5, 5),
        ("sourcesBtn", VerticalButton, r"icons\system\datasources.png", "Data\nSources",
        75, 5),
        ("impDataBtn", VerticalButton, r"icons\system\importdata.png", "Import\nData",
        132, 5),
        ("cleanDataBtn", VerticalButton, r"icons\system\cleandata.png", "Clean\nData",
        185, 5),
        ("sqlBtn", VerticalButton, r"icons\system\sql.png", "SQL\nServices",
        230, 5),
        ("jsonBtn", HorizontalButton, r"icons\system\json.png", "Open JSON",
        290, 7),
        ("xamlBtn", HorizontalButton, r"icons\system\xaml.png", "Open XAML",
        290, 37),
        ("htmlBtn", HorizontalButton, r"icons\system\html.png", "Open HTML",
        400, 7),
        ("webBtn", HorizontalButton, r"icons\system\web.png", "Manage Web",
        400, 37)]

        for item in buttons:
            if len(item) == 6:
                attr, widget, img, text, x, y = item
                command = None
            else:
                attr, widget, img, text, x, y, method_name = item
                command = getattr(self.logic, method_name)

            btn = widget(
                self.parent,
                image_path=self._load_icon(img),
                text=text,
                font=("Segoe UI", 12),
                fg_color=self.parent_color,
                hover_color="#3a3a3a",
                command=command,
            )
            setattr(self, attr, btn)
            btn.place(x=x, y=y)


########################################################################################
# WIDGETS
########################################################################################
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


class HorizontalButton(ctk.CTkFrame):
    """
    A horizontal button with an icon and text.
    """

    def __init__(
        self,
        parent,
        image_path=None,
        text="",
        command=None,
        size=(16, 16),
        hover_border=["#454545","#bebebe"],
        click_border=["#737373","#808080"],
        font=("Segoe UI", 11),
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent")

        self.command = command
        self.hover_border = hover_border
        self.click_border = click_border

        self.border_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=6,
            border_width=0,
            border_color=self.hover_border,
            width=100,
            height=25,
        )
        self.border_frame.pack(padx=2, pady=2, fill="both", expand=True)
        self.border_frame.pack_propagate(False)

        self.inner_frame = ctk.CTkFrame(self.border_frame, fg_color="transparent")
        self.inner_frame.pack(fill="both", expand=True, padx=4, pady=4)

        if image_path:
            self.image = ctk.CTkImage(light_image=Image.open(image_path), size=size)
            self.icon = ctk.CTkLabel(self.inner_frame, image=self.image, text="")
            self.icon.pack(side="left", padx=(0, 5))
        else:
            self.icon = None

        self.label = ctk.CTkLabel(
            self.inner_frame,
            text=text,
            font=font,
            text_color=["#1E1E1E", "#c8c8c8"],
        )
        self.label.pack(side="left")

        for widget in (
            self,
            self.border_frame,
            self.inner_frame,
            self.icon,
            self.label,
        ):
            if widget:
                widget.bind("<Enter>", self._on_enter)
                widget.bind("<Leave>", self._on_leave)
                widget.bind("<Button-1>", self._on_click)
                widget.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event):
        self.border_frame.configure(border_width=1)

    def _on_leave(self, event):
        self.border_frame.configure(border_width=0)

    def _on_click(self, event):
        self.border_frame.configure(border_color=self.click_border)
        if self.command:
            self.command()

    def _on_release(self, event):
        self.border_frame.configure(border_color=self.hover_border)

class LargeButton(ctk.CTkFrame):
    """
    A Large horizontal button with an icon and text.
    """

    def __init__(
        self,
        parent,
        image_path=None,
        text="",
        command=None,
        size=(48, 48),
        hover_border=["#454545","#bebebe"],
        click_border=["#737373","#808080"],
        font=("Segoe UI", 15),
        explainText = "",
        explainfont = ("Segoe UI",12),
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent")

        self.command = command
        self.hover_border = hover_border
        self.click_border = click_border

        self.border_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=6,
            border_width=0,
            border_color=self.hover_border,
            width=450,
            height=70,
        )
        self.border_frame.pack(padx=2, pady=2, fill="both", expand=True)
        self.border_frame.pack_propagate(False)

        self.inner_frame = ctk.CTkFrame(self.border_frame, fg_color="transparent")
        self.inner_frame.pack(fill="both", expand=True, padx=4, pady=4)

        if image_path:
            self.image = ctk.CTkImage(light_image=Image.open(image_path), size=size)
            self.icon = ctk.CTkLabel(self.inner_frame, image=self.image, text="")
            self.icon.place(x=0,y=5)
        else:
            self.icon = None

        self.label = ctk.CTkLabel(
            self.inner_frame,
            text=text,
            font=font,
            anchor="w",
            justify="left",
            text_color=["#1E1E1E", "#c8c8c8"],
        )
        self.label.place(x=60,y=5)

        self.label2 = ctk.CTkLabel(
            self.inner_frame,
            text=explainText,
            font=explainfont,
            anchor="w",
            justify="left",
            text_color=["#1E1E1E", "#c8c8c8"]
        )
        self.label2.place(x=60,y=30)

        for widget in (
            self,
            self.border_frame,
            self.inner_frame,
            self.icon,
            self.label,
        ):
            if widget:
                widget.bind("<Enter>", self._on_enter)
                widget.bind("<Leave>", self._on_leave)
                widget.bind("<Button-1>", self._on_click)
                widget.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event):
        self.border_frame.configure(border_width=1)

    def _on_leave(self, event):
        self.border_frame.configure(border_width=0)

    def _on_click(self, event):
        self.border_frame.configure(border_color=self.click_border)
        if self.command:
            self.command()

    def _on_release(self, event):
        self.border_frame.configure(border_color=self.hover_border)

class VerticalButton(ctk.CTkFrame):
    """
    A vertical button with an icon above text.
    """

    def __init__(
        self,
        parent,
        image_path=None,
        text="",
        command=None,
        size=(27, 27),
        hover_border=["#454545","#bebebe"],
        click_border=["#737373","#808080"],
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent")

        self.command = command
        self.hover_border = hover_border
        self.click_border = click_border

        self.border_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=6,
            border_width=0,
            border_color=self.hover_border,
        )
        self.border_frame.pack(padx=2, pady=2, fill="both", expand=True)

        self.inner_frame = ctk.CTkFrame(self.border_frame, fg_color="transparent")
        self.inner_frame.pack(fill="both", expand=True, padx=4, pady=4)

        if image_path:
            self.image = ctk.CTkImage(light_image=Image.open(image_path), size=size)
            self.icon = ctk.CTkLabel(self.inner_frame, image=self.image, text="")
            self.icon.pack(pady=(0, 2))
        else:
            self.icon = None

        self.label = ctk.CTkLabel(
            self.inner_frame,
            text=text,
            font=("Segoe UI", 12),
            text_color=["#1E1E1E", "#c8c8c8"],
        )
        self.label.pack()

        for widget in (
            self,
            self.border_frame,
            self.inner_frame,
            self.icon,
            self.label,
        ):
            if widget:
                widget.bind("<Enter>", self._on_enter)
                widget.bind("<Leave>", self._on_leave)
                widget.bind("<Button-1>", self._on_click)
                widget.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event):
        self.border_frame.configure(border_width=1)

    def _on_leave(self, event):
        self.border_frame.configure(border_width=0)

    def _on_click(self, event):
        self.border_frame.configure(border_color=self.click_border)
        if self.command:
            self.command()

    def _on_release(self, event):
        self.border_frame.configure(border_color=self.hover_border)


class SmallButton(ctk.CTkFrame):
    """
    A small button for typical no-background colors and custom interaction.
    """

    def __init__(
        self,
        parent,
        image_path=None,
        command=None,
        size=(16, 16),
        hover_border=["#B7B7B7","#434343"],
        click_border=["#737373","#808080"],
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent")

        self.command = command
        self.hover_border = hover_border
        self.click_border = click_border

        self.border_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=3,
            border_width=0,
            border_color=self.hover_border,
        )
        self.border_frame.pack(padx=1, pady=1, fill="both", expand=True)
        self.border_frame.pack_propagate(True)

        self.inner_frame = ctk.CTkFrame(self.border_frame, fg_color="transparent")
        self.inner_frame.pack(fill="both", expand=True, padx=1, pady=1)
        self.inner_frame.pack_propagate(True)

        if image_path:
            self.image = ctk.CTkImage(light_image=Image.open(image_path), size=size)
            self.icon = ctk.CTkLabel(self.inner_frame, image=self.image, text="",width=16,height=16)
            self.icon.pack(pady=(0,0))
        else:
            self.icon = None

        for widget in (
            self,
            self.border_frame,
            self.inner_frame,
            self.icon,
        ):
            if widget:
                widget.bind("<Enter>", self._on_enter)
                widget.bind("<Leave>", self._on_leave)
                widget.bind("<Button-1>", self._on_click)
                widget.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event):
        self.border_frame.configure(border_width=1)

    def _on_leave(self, event):
        self.border_frame.configure(border_width=0)

    def _on_click(self, event):
        self.border_frame.configure(border_color=self.click_border)
        if self.command:
            self.command()

    def _on_release(self, event):
        self.border_frame.configure(border_color=self.hover_border)


class LinkLabel(ctk.CTkFrame):
    """
    A clickable link label that changes color on hover.
    """

    def __init__(
        self,
        parent,
        width,
        height,
        link_color="#1a73e8",
        after_link_color="#551a8b",
        corner_radius=5,
        font=None,
        text="",
        command=None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.command = command
        self.link_color = link_color
        self.after_link_color = after_link_color
        self.corner_radius = corner_radius
        self.font = font or ("Segoe UI", 12)
        self.width=width
        self.height=height

        self.hoverframe = ctk.CTkFrame(
            self,
            width=self.width,
            height=self.height,
            fg_color=parent.cget("fg_color"),
            corner_radius=self.corner_radius,
            border_width=0
        )
        self.hoverframe.pack(fill="both")
        self.hoverframe.pack_propagate(False)

        self.label = ctk.CTkLabel(
            self.hoverframe,
            text=text, 
            font=self.font,
            text_color=self.link_color,
        )
        self.label.pack()

        for widget in (self, self.hoverframe, self.label):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def _on_enter(self, event):
        self.label.configure(text_color=self.after_link_color)

    def _on_leave(self, event):
        self.label.configure(text_color=self.link_color)

    def _on_click(self, event):
        if self.command:
            self.command()


class ToolTip(ctk.CTkFrame):
    """
    A tooltip widget that displays informative text when hovering over a widget.
    """

    def __init__(
        self, widget, text, delay=400, bg="#2b2b2b", fg="white", font=("Segoe UI", 10)
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


class ListView(ctk.CTkFrame):
    def __init__(self):
        pass


class ColorDialog(ctk.CTkToplevel):
    """
    A comprehensive color picker dialog with RGB sliders, hex input,
    a default color palette, and recent colors.
    """

    def __init__(self, master, initial_color="#FFFFFF"):
        super().__init__(master)
        self.title("Color Picker")
        self.resizable(False, False)
        self.geometry("330x400")

        self.current_rgb = self.hex_to_rgb(initial_color)
        self.current_hex = initial_color
        self.selected_color = None
        self.recent_colors = []
        self.max_recent = 10

        self.transient(master)

        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=10)

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        self.preview_frame = ctk.CTkFrame(
            top_frame, width=120, height=135, corner_radius=5, fg_color=self.current_hex
        )
        self.preview_frame.pack(side="left", padx=(0, 10))

        self.palette_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        self.palette_frame.pack(side="left", fill="both", expand=True)

        self.default_palette = [
            "#000000",
            "#4B4B4B",
            "#9C9C9C",
            "#CDCDCD",
            "#FFFFFF",
            "#6F0000",
            "#FF0000",
            "#FF4D00",
            "#FF9D00",
            "#FFD000",
            "#EAFF00",
            "#A6FF00",
            "#2EB700",
            "#008B09",
            "#006B1B",
            "#00A2ED",
            "#008CFF",
            "#0046AF",
            "#000073",
            "#4E008E",
        ]
        self._create_palette_buttons()

        slider_frame = ctk.CTkFrame(self, fg_color="transparent")
        slider_frame.pack(fill="x", padx=10, pady=5)

        self.slider_r, self.label_r = self._create_slider(
            slider_frame, "R", self.current_rgb[0]
        )
        self.slider_g, self.label_g = self._create_slider(
            slider_frame, "G", self.current_rgb[1]
        )
        self.slider_b, self.label_b = self._create_slider(
            slider_frame, "B", self.current_rgb[2]
        )

        self.hex_entry = ctk.CTkEntry(slider_frame, width=100, font=("Segoe UI", 13))
        self.hex_entry.pack(pady=(5, 5), side="right")
        self.hex_label = ctk.CTkLabel(
            slider_frame, width=40, text="Hex:", font=("Segoe UI", 13)
        )
        self.hex_label.pack(pady=(5, 5), side="right")
        self.gradient_label = ctk.CTkLabel(
            slider_frame, width=70, text="Gradients", font=("Segoe UI", 13)
        )
        self.gradient_label.pack(pady=(5, 5), side="left", padx=(0, 10))
        self.hex_entry.insert(0, self.current_hex)
        self.hex_entry.bind("<KeyRelease>", lambda e: self._hex_live_update())
        self.hex_entry.bind("<Return>", lambda e: self._hex_changed())
        self.hex_entry.bind("<FocusOut>", lambda e: self._hex_changed())

        self.recent_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.recent_frame.pack(fill="x", padx=10, pady=(5, 0))
        self._update_recent_colors()

        cancel_button = ctk.CTkButton(
            bottom_frame,
            text="Cancel",
            width=80,
            font=("Segoe UI", 12),
            command=self._on_cancel,
        )
        cancel_button.pack(side="right", padx=5)
        ok_button = ctk.CTkButton(
            bottom_frame,
            text="OK",
            width=80,
            font=("Segoe UI", 12),
            command=self._on_ok,
        )
        ok_button.pack(side="right", padx=5)

        self.update_preview()

    def _create_slider(self, parent, label_text, initial_value):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(2, 5))
        label = ctk.CTkLabel(frame, text=label_text, font=("Segoe UI", 14))
        label.pack(side="left")
        slider = ctk.CTkSlider(
            frame, from_=0, to=255, number_of_steps=255, command=self._slider_changed
        )
        slider.set(initial_value)
        slider.pack(side="left", fill="x", expand=True, padx=(5, 5))
        value_label = ctk.CTkLabel(
            frame, text=str(initial_value), width=30, font=("Segoe UI", 13)
        )
        value_label.pack(side="right")
        return slider, value_label

    def _create_palette_buttons(self):
        btn_size = 30
        buttons_per_row = 5
        for idx, color in enumerate(self.default_palette):
            btn = ctk.CTkButton(
                self.palette_frame,
                fg_color=color,
                width=btn_size,
                height=btn_size,
                corner_radius=5,
                text="",
                command=lambda c=color: self._palette_color_selected(c),
            )
            row = idx // buttons_per_row
            col = idx % buttons_per_row
            btn.grid(row=row, column=col, padx=2, pady=2)

    def _palette_color_selected(self, hex_color):
        self.current_hex = hex_color
        self.update_sliders_from_hex()
        self._save_recent_color(hex_color)

    def _slider_changed(self, value):
        r = int(self.slider_r.get())
        g = int(self.slider_g.get())
        b = int(self.slider_b.get())
        self.current_rgb = [r, g, b]
        self.label_r.configure(text=str(r))
        self.label_g.configure(text=str(g))
        self.label_b.configure(text=str(b))
        self.update_preview()
        self._save_recent_color(self.rgb_to_hex(r, g, b))

    def _hex_changed(self):
        hex_value = self.hex_entry.get()
        if not hex_value.startswith("#"):
            hex_value = "#" + hex_value
        self.current_hex = hex_value
        self.update_sliders_from_hex()
        self._save_recent_color(self.current_hex)

    def _hex_live_update(self):
        hex_value = self.hex_entry.get()
        if not hex_value.startswith("#"):
            hex_value = "#" + hex_value
        if len(hex_value) == 7:
            try:
                self.current_hex = hex_value
                self.current_rgb = self.hex_to_rgb(self.current_hex)
                self.slider_r.set(self.current_rgb[0])
                self.slider_g.set(self.current_rgb[1])
                self.slider_b.set(self.current_rgb[2])
                self.label_r.configure(text=str(self.current_rgb[0]))
                self.label_g.configure(text=str(self.current_rgb[1]))
                self.label_b.configure(text=str(self.current_rgb[2]))
                self.update_preview()
            except ValueError:
                pass

    def update_sliders_from_hex(self):
        hex_code = self.current_hex.lstrip("#")
        if len(hex_code) != 6:
            return
        try:
            self.current_rgb = self.hex_to_rgb(self.current_hex)
            self.slider_r.set(self.current_rgb[0])
            self.slider_g.set(self.current_rgb[1])
            self.slider_b.set(self.current_rgb[2])
            self.label_r.configure(text=str(self.current_rgb[0]))
            self.label_g.configure(text=str(self.current_rgb[1]))
            self.label_b.configure(text=str(self.current_rgb[2]))
            self.update_preview()
        except ValueError:
            pass

    def update_preview(self):
        hex_color = self.rgb_to_hex(*self.current_rgb)
        self.current_hex = hex_color
        self.preview_frame.configure(fg_color=hex_color)
        self.hex_entry.delete(0, "end")
        self.hex_entry.insert(0, hex_color)

    def _save_recent_color(self, color):
        if color in self.recent_colors:
            return
        self.recent_colors.insert(0, color)
        if len(self.recent_colors) > self.max_recent:
            self.recent_colors.pop()
        self._update_recent_colors()

    def _update_recent_colors(self):
        for widget in self.recent_frame.winfo_children():
            widget.destroy()
        btn_size = 25
        for idx, color in enumerate(self.recent_colors):
            btn = ctk.CTkButton(
                self.recent_frame,
                fg_color=color,
                width=btn_size,
                height=btn_size,
                corner_radius=5,
                text="",
                command=lambda c=color: self._palette_color_selected(c),
            )
            btn.grid(row=0, column=idx, padx=2)

    def rgb_to_hex(self, r, g, b):
        return f"#{r:02X}{g:02X}{b:02X}"

    def hex_to_rgb(self, hex_code):
        hex_code = hex_code.lstrip("#")
        if len(hex_code) != 6:
            raise ValueError("Invalid hex code")
        r = int(hex_code[0:2], 16)
        g = int(hex_code[2:4], 16)
        b = int(hex_code[4:6], 16)
        return [r, g, b]

    def _on_ok(self):
        self._hex_changed()
        self.selected_color = self.current_hex
        self.destroy()

    def _on_cancel(self):
        self.selected_color = None
        self.destroy()

    def get_color(self):
        self.wait_window()
        return self.selected_color


class ImageShower(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Image Picker")
        self.geometry("400x400")

        self.mainFrame = ctk.CTkFrame(
            self, corner_radius=0, height=360, fg_color="#1E1E1E"
        )
        self.mainFrame.pack(fill="both")
        self.mainFrame.pack_propagate(False)

        self.bottomFrame = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.bottomFrame.pack(side="bottom", fill="x")

        self.imgChooseBtn = ctk.CTkButton(self.mainFrame, width=40, height=40, text="")
        self.imgChooseBtn.pack(anchor="center", pady=160)


class DrawingCanvas(ctk.CTkFrame):
    def __init__(self):
        pass


class DateTimeDialog(ctk.CTkFrame):
    def __init__(self):
        pass


class VisualTimer(ctk.CTkFrame):
    def __init__(self):
        pass


class GraphBox(ctk.CTkFrame):
    def __init__(self):
        pass


class NumericCounter(ctk.CTkFrame):
    def __init__(self):
        pass


class IconListFrame(ctk.CTkFrame):
    def __init__(self):
        pass


class CustomMessageBox(ctk.CTkToplevel):
    """
    A customizable message box with optional further explanation and icon,
    positioned at a specified offset from the bottom-right corner of the screen.
    """

    def __init__(
        self,
        master,
        message,
        font,
        width=200,
        height=100,
        further_explanation=None,
        icon=None,
        offset_x=20,
        offset_y=40,
    ):
        super().__init__(master)
        self.overrideredirect(True)
        self.geometry(f"{width}x{height}")

        if icon:
            self.iconbitmap(icon)

        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - width - offset_x
        y = screen_height - height - offset_y

        self.geometry(f"{width}x{height}+{x}+{y}")

        text = (
            message if not further_explanation else f"{message}\n{further_explanation}"
        )
        self.message_label = ctk.CTkLabel(
            self, text=text, font=font, fg_color=self.cget("fg_color")
        )
        self.message_label.place(x=40, y=30)

        self.close_btn = ctk.CTkButton(self, text="OK", command=self.destroy, width=80)
        self.close_btn.place(x=60, y=70)

        self.focus()
        self.grab_set()


########################################################################################
# ANIMATIONS AND SHADERS
########################################################################################

class ScreenShakeAnimation:
    def __init__(
        self,
        widget,
        orig_x=None,
        orig_y=None,
        intensity_x=5,
        intensity_y=2,
        duration=50,
        cycles=6,
        anchor=None,
    ):
        self.widget = widget
        self.intensity_x = intensity_x
        self.intensity_y = intensity_y
        self.duration = duration
        self.cycles = cycles
        self.anchor = anchor

        widget.update_idletasks()
        self.orig_x = orig_x if orig_x is not None else widget.winfo_x()
        self.orig_y = orig_y if orig_y is not None else widget.winfo_y()

        self._animate(0)

    def _animate(self, count):
        if count < self.cycles:
            offset_x = self.intensity_x if count % 2 == 0 else -self.intensity_x
            offset_y = self.intensity_y if count % 2 == 0 else -self.intensity_y

            self.widget.place(
                x=int(self.orig_x + offset_x),
                y=int(self.orig_y + offset_y),
                anchor=self.anchor,
            )

            self.widget.after(self.duration, lambda: self._animate(count + 1))
        else:
            self.widget.place(
                x=int(self.orig_x), y=int(self.orig_y), anchor=self.anchor
            )


class ClickPressAnimation:
    def __init__(self):
        pass


class MouseHoverAnimation:
    def __init__(self):
        pass


class MouseWaitAnimation:
    def __init__(self):
        pass


class SlidingAnimation:
    def __init__(
        self,
        master: ctk.CTkFrame,
        x_target: int,
        y_target: int,
        animation_time: int,
        animation_step: int,
        slide_x: bool = True,
        slide_y: bool = False):

        if slide_x == slide_y:
            raise ValueError("Animation can specify either X or Y, not both")

        self.master = master
        self.x_target = x_target
        self.y_target = y_target
        self.animation_time = animation_time
        self.animation_step = animation_step
        self.slide_x = slide_x
        self.slide_y = slide_y

    def animate_in(self):
        if self.slide_x:
            self._animate_x_in()
        else:
            self._animate_y_in()

    def animate_out(self):
        if self.slide_x:
            self._animate_x_out()
        else:
            self._animate_y_out()

    def _animate_x_in(self):
        start_x = self.master.winfo_width()
        self.master.place(x=start_x, y=self.y_target)

        x = start_x

        def step():
            nonlocal x
            x -= self.animation_step
            if x <= self.x_target:
                self.master.place(x=self.x_target, y=self.y_target)
                return

            self.master.place(x=x, y=self.y_target)
            self.master.after(self.animation_time, step)

        step()

    def _animate_x_out(self):
        x = self.master.winfo_x()
        end_x = self.master.winfo_width()

        def step():
            nonlocal x
            x += self.animation_step
            if x >= end_x:
                self.master.place(x=end_x, y=self.y_target)
                return

            self.master.place(x=x, y=self.y_target)
            self.master.after(self.animation_time, step)

        step()

    def _animate_y_in(self):
        start_y = self.master.winfo_height()
        self.master.place(x=self.x_target, y=start_y)

        y = start_y

        def step():
            nonlocal y
            y -= self.animation_step
            if y <= self.y_target:
                self.master.place(x=self.x_target, y=self.y_target)
                return

            self.master.place(x=self.x_target, y=y)
            self.master.after(self.animation_time, step)

        step()

    def _animate_y_out(self):
        y = self.master.winfo_y()
        end_y = self.master.winfo_height()

        def step():
            nonlocal y
            y += self.animation_step
            if y >= end_y:
                self.master.place(x=self.x_target, y=end_y)
                return

            self.master.place(x=self.x_target, y=y)
            self.master.after(self.animation_time, step)

        step()

class WaitAnimation:
    def __init__(self):
        pass
