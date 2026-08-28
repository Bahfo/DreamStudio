"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Main workspace container for DreamStudio: hosts the central text editor
flanked by left/right utility tab managers and the bottom utilities panel.
"""

from editor import *

from editor.base.statusBar import StatusBar
from editor.base.optionsBar import OptionsMenu
from editor.base.verticalBar import VerticalSidebar
from editor.base.titleBar import DreamStudioTitleBar

from editor.api.vertical_menus_api import VerticalMenusAPI

from editor.utils.tools.todo_search import TODOSearch
from editor.utils.utils_tabmanager import UtilityTabManager
from editor.utils.explorer.explorer import SolutionExplorer
from editor.utils.properties.properties import PropertiesExplorer
from editor.utils.git_control.source_control import GitVersionControl
from editor.utils.server_explorer.server_explorer import ServerExplorer
from editor.utils.notifications.notifications_panel import NotificationsPanel

from editor.Ironica.ui_build import EditorContainer, UtilsContainer


class WorkspaceContainer(QWidget):
    """Main workspace container: Manages real-time state
    tracking, collapsing, expanding, and floating allocations
    for side panels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workspace Container")
        self.resize(1024, 768)

        # 1. Native targets - only changed by user drags
        self._left_target_width = 235
        self._right_target_width = 235
        self._startup_done = False

        self._base_layout = QHBoxLayout(self)
        self._base_layout.setContentsMargins(0, 0, 0, 0)
        self._base_layout.setSpacing(0)

        self._main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self._top_horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)

        self._left_utils_manager = UtilityTabManager(self)
        self._right_utils_manager = UtilityTabManager(self)

        self._text_editor_center = EditorContainer(self)
        self._lower_widget = UtilsContainer(self)

        self._top_horizontal_splitter.setCollapsible(0, False)
        self._top_horizontal_splitter.setCollapsible(2, False)

        self._left_utils_manager.setMinimumWidth(250)
        self._right_utils_manager.setMinimumWidth(250)
        self._text_editor_center.setMinimumWidth(300)

        # QSplitter native resistance: sides never resize on standard window drag
        self._top_horizontal_splitter.setStretchFactor(0, 0)
        self._top_horizontal_splitter.setStretchFactor(1, 1)
        self._top_horizontal_splitter.setStretchFactor(2, 0)

        self._top_horizontal_splitter.addWidget(self._left_utils_manager)
        self._top_horizontal_splitter.addWidget(self._text_editor_center)
        self._top_horizontal_splitter.addWidget(self._right_utils_manager)

        self._main_vertical_splitter.addWidget(self._top_horizontal_splitter)
        self._main_vertical_splitter.addWidget(self._lower_widget)
        self._base_layout.addWidget(self._main_vertical_splitter)

        self._left_utils_manager.setVisible(False)
        self._right_utils_manager.setVisible(False)
        self._lower_widget.setVisible(False)

        # 2. Update targets EXCLUSIVELY when the user drags the handle
        self._top_horizontal_splitter.splitterMoved.connect(self._on_splitter_moved)

        self._populate_panels()

        self._vertical_menus_api = VerticalMenusAPI(self)
        self._vertical_menus_api.register_panel(
            "solution_explorer",
            self._solution_explorer,
            self._left_utils_manager,
            "left",
            splitter=self._top_horizontal_splitter,
            splitter_index=0,
            default_width=220,
        )
        self._vertical_menus_api.register_panel(
            "source_control",
            self._source_control,
            self._left_utils_manager,
            "left",
            splitter=self._top_horizontal_splitter,
            splitter_index=0,
            default_width=220,
        )
        self._vertical_menus_api.register_panel(
            "properties",
            self._properties_explorer,
            self._right_utils_manager,
            "right",
            splitter=self._top_horizontal_splitter,
            splitter_index=2,
            default_width=220,
        )
        self._vertical_menus_api.register_panel(
            "todo_search",
            self._todo_search,
            self._right_utils_manager,
            "right",
            splitter=self._top_horizontal_splitter,
            splitter_index=2,
            default_width=220,
        )
        self._vertical_menus_api.register_panel(
            "server_explorer",
            self._server_explorer,
            self._right_utils_manager,
            "right",
            splitter=self._top_horizontal_splitter,
            splitter_index=2,
            default_width=220,
        )
        self._vertical_menus_api.register_panel(
            "notifications",
            self._notifications_panel,
            self._right_utils_manager,
            "right",
            splitter=self._top_horizontal_splitter,
            splitter_index=2,
            default_width=220,
        )

        self._left_utils_manager.panel_close_requested.connect(
            lambda pid: (self._vertical_menus_api.deactivate_panel(pid))
        )
        self._right_utils_manager.panel_close_requested.connect(
            lambda pid: (self._vertical_menus_api.deactivate_panel(pid))
        )

        # Default workspace layout on startup.
        self._vertical_menus_api.activate_panel("solution_explorer")
        self._vertical_menus_api.activate_panel("properties")

    def _on_splitter_moved(self, pos: int, index: int) -> None:
        """Cache widths ONLY when the user manually intervenes."""
        sizes = self._top_horizontal_splitter.sizes()
        if self._left_utils_manager.isVisible():
            self._left_target_width = sizes[0]
        if self._right_utils_manager.isVisible():
            self._right_target_width = sizes[2]

    def changeEvent(self, event) -> None:
        """Intercept the OS-level minimize/restore cycle directly."""
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            # If the OS is restoring the window from a minimized state
            if not self.window().isMinimized() and (
                event.oldState() & Qt.WindowState.WindowMinimized
            ):
                # Wait 50ms for Qt's layout engine to finish its crushed rendering cycle, then enforce user widths
                QTimer.singleShot(50, self._restore_user_sizes)

    def _restore_user_sizes(self) -> None:
        """Re-apply user widths to overwrite the minimize crush."""
        total_w = self._top_horizontal_splitter.width()
        if total_w <= 0:
            return

        left_w = self._left_target_width if self._left_utils_manager.isVisible() else 0
        right_w = (
            self._right_target_width if self._right_utils_manager.isVisible() else 0
        )
        center_w = max(0, total_w - left_w - right_w)

        self._top_horizontal_splitter.setSizes([left_w, center_w, right_w])

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Prevent layout resets if the container is re-shown (e.g. toggling tabs in a main window)
        if not self._startup_done:
            self._startup_done = True
            QTimer.singleShot(0, self._apply_initial_layout)

    def _apply_initial_layout(self) -> None:
        self._top_horizontal_splitter.setSizes(
            [235, max(0, self._top_horizontal_splitter.width() - 470), 235]
        )
        # Seed targets with the exact initial state
        sizes = self._top_horizontal_splitter.sizes()
        self._left_target_width = sizes[0] if sizes[0] > 0 else 235
        self._right_target_width = sizes[2] if sizes[2] > 0 else 235

    def _populate_panels(self) -> None:
        self._solution_explorer = SolutionExplorer()
        self._source_control = GitVersionControl()
        self._properties_explorer = PropertiesExplorer()
        self._todo_search = TODOSearch()
        self._server_explorer = ServerExplorer()
        self._notifications_panel = NotificationsPanel()

    def set_theme(self, bg: str, fg: str, sel: str) -> None:
        self._left_utils_manager.set_theme(bg, fg, sel)
        self._right_utils_manager.set_theme(bg, fg, sel)

    def _create_placeholder_panel(self, text: str):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        return frame
