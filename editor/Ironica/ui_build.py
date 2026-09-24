"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved

EditorContainer: Public wrapper around the tab editor that
exposes a clean interface for toolbar callbacks and the IDE.
"""

from editor import *

# Local Imports
from editor.Ironica.api import EditorAPI
from editor.Ironica.tab_editor import DreamTabbedEditor
from editor.base.user.quickStartMenu import QuickStartMenu
from editor.Ironica.utils.minimap import MiniMapHostWidget

from editor.terminal.api import TerminalPanel
from editor.debugger.problems_widget import ProblemsWidget

logger = logging.getLogger(__name__)


def _inherit_workspace(widget) -> str:
    """Return the main window's workspace path, falling back to the CWD.

    Args:
        widget: Any widget inside the DreamStudio window hierarchy.
    """
    try:
        top = widget.window()
        workspace = getattr(top, "currentDirectory", None)
        if workspace:
            return workspace
    except Exception:
        pass
    return os.getcwd()


class _EditorMethods:
    """Thin adapter that routes toolbar actions to the
    tab editor or to the active editor API."""

    def __init__(self, container: "EditorContainer") -> None:
        self._container = container

    def open_new_tab(self) -> None:
        self._container._tabs.add_new_editor()

    def open_file(self, path: str) -> None:
        self._container._tabs.open_file_by_path(path)

    def save_current(self) -> None:
        self._container._tabs.save_current_file()

    def save_all(self) -> None:
        self._container._tabs.save_all_files()

    def current_editor(self) -> Optional[EditorAPI]:
        return self._container.current_editor()


class EditorContainer(QWidget):
    """Thin wrapper that owns the DreamTabbedEditor and QuickStartMenu in a
    QStackedWidget, exposing public API that the IDE toolbar depends on."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.currentDirectory = _inherit_workspace(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack)

        self._quick_start = QuickStartMenu(self)
        self._stack.addWidget(self._quick_start)

        self._tabs = DreamTabbedEditor(self)
        self._stack.addWidget(self._tabs)

        self.methods = _EditorMethods(self)

        if hasattr(self._tabs, "currentChanged"):
            self._tabs.currentChanged.connect(self._sync_view)

        self._sync_view()

    def _sync_view(self) -> None:
        """Shows QuickStartMenu when no tabs are open, and _tabs when >= 1 tab exists."""
        tab_count = getattr(self._tabs, "count", lambda: 0)()
        if tab_count > 0:
            self._stack.setCurrentWidget(self._tabs)
        else:
            self._stack.setCurrentWidget(self._quick_start)

    @property
    def quick_start(self) -> QuickStartMenu:
        return self._quick_start

    @property
    def tabs(self) -> DreamTabbedEditor:
        return self._tabs

    def current_editor(self) -> Optional[EditorAPI]:
        widget = self._tabs.currentWidget()
        if widget is None:
            return None
        if isinstance(widget, MiniMapHostWidget):
            return EditorAPI(widget)
        return None

    def set_font_size(self, value: int) -> None:
        self._tabs.set_font_size(value)

    def _main_window(self):
        return self.window()

    def update_position_status(self) -> None:
        win = self._main_window()
        if win and hasattr(win, "update_position_status"):
            win.update_position_status()

    def update_editor_visibility(self) -> None:
        self._sync_view()
        win = self._main_window()
        if win and hasattr(win, "update_editor_visibility"):
            win.update_editor_visibility()

    def _get_current_editor(self):
        return self.current_editor()

    @property
    def status_bar(self):
        win = self._main_window()
        return getattr(win, "status_bar", None)


class UtilsContainer(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.currentDirectory = _inherit_workspace(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack)

        self.terminal_window = TerminalPanel(self)
        self.problems_window = ProblemsWidget(self)

        self._stack.addWidget(self.terminal_window)
        self._stack.addWidget(self.problems_window)

        self.terminal_window.close_requested.connect(self._hide_show_terminal)

    def _hide_show_terminal(self) -> None:
        workspace = self.parent().parent()
        splitter = workspace._main_vertical_splitter
        self.setVisible(False)
        splitter.setSizes([1, 0])

    def _hide_problems_widget(self) -> None:
        pass
