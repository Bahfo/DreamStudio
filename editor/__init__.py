import os
import sys

from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *

from editor.base.statusBar import StatusBar
from editor.base.optionsBar import OptionsMenu
from editor.base.verticalBar import VerticalSidebar
from editor.base.titleBar import DreamStudioTitleBar

from editor.terminal.api import TerminalPanel
from editor.api.vertical_menus_api import VerticalMenusAPI

from editor.utils.tools.todo_search import TODOSearch
from editor.utils.utils_tabmanager import UtilityTabManager
from editor.utils.explorer.explorer import SolutionExplorer
from editor.utils.properties.properties import PropertiesExplorer
from editor.utils.git_control.source_control import GitVersionControl


from editor.Ironica.ui_build import EditorContainer


class WorkspaceContainer(QWidget):
    """Main workspace container: Manages real-time state
    tracking, collapsing, expanding, and floating allocations
    for side panels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workspace Container")
        self.resize(1024, 768)

        self._base_layout = QHBoxLayout(self)
        self._base_layout.setContentsMargins(0, 0, 0, 0)
        self._base_layout.setSpacing(0)

        self._main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self._top_horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)

        self._left_utils_manager = UtilityTabManager(self)
        self._right_utils_manager = UtilityTabManager(self)

        self._text_editor_center = EditorContainer(self)
        self.terminal_window = TerminalPanel()
        self.terminal_window.close_requested.connect(self._hide_terminal)

        self._top_horizontal_splitter.addWidget(self._left_utils_manager)
        self._top_horizontal_splitter.addWidget(self._text_editor_center)
        self._top_horizontal_splitter.addWidget(self._right_utils_manager)

        self._main_vertical_splitter.addWidget(self._top_horizontal_splitter)
        self._main_vertical_splitter.addWidget(self.terminal_window)
        self._base_layout.addWidget(self._main_vertical_splitter)

        self._top_horizontal_splitter.setSizes([0, 1024, 0])
        self._main_vertical_splitter.setSizes([1, 0])

        self._left_utils_manager.setVisible(False)
        self._right_utils_manager.setVisible(False)
        self.terminal_window.setVisible(False)

        self._populate_panels()

        self._vertical_menus_api = VerticalMenusAPI(self)
        self._vertical_menus_api.register_panel(
            "solution_explorer",
            self._solution_explorer,
            self._left_utils_manager,
            "left",
            splitter=self._top_horizontal_splitter,
            splitter_index=0,
            default_width=350,
        )
        self._vertical_menus_api.register_panel(
            "source_control",
            self._source_control,
            self._left_utils_manager,
            "left",
            splitter=self._top_horizontal_splitter,
            splitter_index=0,
            default_width=350,
        )
        self._vertical_menus_api.register_panel(
            "properties",
            self._properties_explorer,
            self._right_utils_manager,
            "right",
            splitter=self._top_horizontal_splitter,
            splitter_index=2,
            default_width=350,
        )
        self._vertical_menus_api.register_panel(
            "todo_search",
            self._todo_search,
            self._right_utils_manager,
            "right",
            splitter=self._top_horizontal_splitter,
            splitter_index=2,
            default_width=350,
        )

        self._left_utils_manager.panel_close_requested.connect(
            lambda pid: (self._vertical_menus_api.deactivate_panel(pid))
        )
        self._right_utils_manager.panel_close_requested.connect(
            lambda pid: (self._vertical_menus_api.deactivate_panel(pid))
        )

    def _populate_panels(self) -> None:
        self._solution_explorer = SolutionExplorer()
        self._source_control = GitVersionControl()
        self._properties_explorer = PropertiesExplorer()
        self._todo_search = TODOSearch()

    def set_theme(self, bg: str, fg: str, sel: str) -> None:
        self._left_utils_manager.set_theme(bg, fg, sel)
        self._right_utils_manager.set_theme(bg, fg, sel)

    def _hide_terminal(self) -> None:
        self.terminal_window.setVisible(False)
        self._main_vertical_splitter.setSizes([1, 0])

    def _create_placeholder_panel(self, text: str):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        return frame
