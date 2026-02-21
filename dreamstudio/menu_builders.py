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
import customtkinter as ctk
from dreamstudio.utils.colorDialog import ColorDialog
from dreamstudio.utils.largeButton import LargeButton
from dreamstudio.utils.layoutsTab import LayoutsTab
from dreamstudio.utils.largeButton import LargeButton
from dreamstudio.utils.linkLabel import LinkLabel
from dreamstudio.utils.smallButton import SmallButton
from dreamstudio.utils.toolTip import ToolTip
from dreamstudio.utils.horizontalButton import HorizontalButton
from dreamstudio.utils.verticalButton import VerticalButton
from dreamstudio.utils.animations import *

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

class DebugBuilder:
    def __init__(self, parent_color, debugFrame : ctk.CTkFrame):
        self.debugFrame = debugFrame
        self.parent_color = parent_color

        self._create_debug_tab()

    def _create_debug_tab(self):
        style = {"font": ("Segoe UI", 12), "fg_color": self.parent_color, "hover_color": "#3a3a3a"}

        main_btns = [
            ("debuggingBtn", "bug.png",     "Start\nDebugging",   5,   3),
            ("runNoBugBtn",  "start.png",   "Run without\nDebug", 82,  5),
            ("attachBtn",    "attach.png",  "Attach to\nProc",    162, 5),
            ("compileBtn",   "compile.png", "Compile\nCode",      253, 5),
            ("stopBugBtn",   "stop.png",    "Stop\nDebugging",    315, 5),
            ("restartBugBtn","restart.png", "Restart\nDebug",     392, 5),
            ("deatBugBtn",   "deattach.png","Detach\nDebugger",   470, 5),
        ]

        for attr, icon, txt, x, y in main_btns:
            btn = VerticalButton(self.debugFrame, image_path=rf"icons\system\{icon}", text=txt, **style)
            btn.place(x=x, y=y)
            setattr(self, attr, btn)

        for x_pos in [543, 938]:
            ctk.CTkFrame(self.debugFrame, width=2, height=75, fg_color=["#727272","#3E3E3E"]).place(x=x_pos, y=7)

        self.debuggingToolsFrame = ctk.CTkFrame(self.debugFrame, width=162, height=35, border_width=1, border_color="#5e5e5e")
        self.debuggingToolsFrame.place(x=553, y=7)

class TerminalBuilder:
    def __init__(self, terminalFrame, parent_color):
        self.terminalFrame = terminalFrame
        self.parent_color = parent_color

        self._create_terminal_tab()

    def _create_terminal_tab(self):
        terminal_btns = [
            ("runTaskBtn",  "task.png",     "Run Task",          5),
            ("buildBtn",    "build.png",    "Build Task",        75),
            ("fileMngBtn",  "fileMng.png",  "Run File\nManager", 150),
            ("dayDreamBtn", "daydream.png", "DayDream\nTerminal",220)]

        style = {
            "font": ("Segoe UI", 12),
            "fg_color": self.parent_color,
            "hover_color": "#3a3a3a"}
        icon_dir = r"icons\system"

        for attr, icon, text, x in terminal_btns:
            btn = VerticalButton(
                self.terminalFrame,
                image_path=f"{icon_dir}\\{icon}",
                text=text,
                **style)
            btn.place(x=x, y=5)
            setattr(self, attr, btn)

class HelpBuilder:
    def __init__(self, helpFrame, parent_color):
        self.parent_color = parent_color
        self.helpFrame = helpFrame

    def _create_help_tab(self):
        help_btns = [
            ("docBtn",  "documentation.png", "Documentation", 5),
            ("feedBtn", "feedback.png",      "Feedback",      106),
            ("hBtn",    "help.png",          "Show Help",     176),]

        style = {
            "font": ("Segoe UI", 12),
            "fg_color": self.parent_color,
            "hover_color": "#3a3a3a"}

        for attr, icon, text, x in help_btns:
            btn = VerticalButton(
                self.helpFrame,
                image_path=rf"icons\system\{icon}",
                text=text,
                **style)
            btn.place(x=x, y=5)
            setattr(self, attr, btn)


CONFIG_FILE = r"themes\config\config.json"
REFRESH_INTERVAL_MINUTES = 2
REFRESH_INTERVAL_MS = REFRESH_INTERVAL_MINUTES * 60 * 1000

icon_paths = {
    "load_ico": r"icons\system\load.png",
    "refresh_ico": r"icons\system\refresh.png",
    "console": r"icons\system\console.png",
    "debug": r"icons\system\debug.png",
    "manage": r"icons\system\manager.png",
    "problem": r"icons\system\problem.png",
    "ver": r"icons\system\version.png",
    "warning": r"icons\system\warning.png",
}

ctk_icons = {
    "search_photo": (r"icons\system\search.png", (24, 24)),
    "open_photo": (r"icons\system\open_folder.png", (24, 24)),
    "settings_photo": (r"icons\system\settings.png", (24, 24)),
    "save_photo": (r"icons\system\save_file.png", (24, 24)),
    "user_photo": (r"icons\system\user.png", (24, 24)),
}

arrow_icons = {
    "downArrow": (r"icons\system\down_arrow.png", (8, 8)),
    "upArrow": (r"icons\system\up_arrow.png", (8, 8)),
    "rightArrow": (r"icons\system\right_arrow.png", (8, 8)),
    "stepTo": (r"icons\system\stepTo.png", (20, 20)),
    "stepOut": (r"icons\system\stepOut.png", (20, 20)),
    "stepOver": (r"icons\system\stepOver.png", (20, 20)),
    "runToCursor": (r"icons\system\runToCursor.png", (20, 20)),
    "toggleCursor": (r"icons\system\toggle.png", (20, 20)),
}

allowed_extensions = {
    ".py",".txt",".c",".cpp",".json",".docx",".ppt",".pptx",".apk",
    ".cpp",".cs",".cc",".cxx",".html",".js",".java",".swift",".rb",
    ".ts",".jsx",".py",".h"}

