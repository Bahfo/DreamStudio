from editor import *
from editor.workspace_container import WorkspaceContainer
from editor.api.editor_api import EditorAPI
from editor.api.menus_api import MenusAPI

# Local Imports
from editor.base.statusBar import StatusBar
from editor.base.optionsBar import OptionsMenu
from editor.base.verticalBar import VerticalSidebar
from editor.base.titleBar import DreamStudioTitleBar


class DreamStudio(MenusAPI, EditorAPI, QMainWindow):
    """Main IDE window.

    Receives the bootstrap ``ServiceRegistry`` via constructor injection
    and obtains all startup dependencies (config, theme, resource_manager)
    from it.  The window must never independently locate configuration
    files, theme files, or startup paths.
    """

    ui_ready = pyqtSignal()

    def __init__(self, _parent=None, registry=None):
        super().__init__(parent=_parent)
        self._parent = _parent
        self._registry = registry
        self._current_theme_name = None

        self.currentDirectory = QDir.currentPath()
        self.setWindowTitle("DreamStudio")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.setup_layout()

        self.ui_ready.connect(self._on_ui_ready)

        # Apply the theme provided by the bootstrap kernel.
        theme_content = self._registry.get("theme_content") if self._registry else None
        if theme_content:
            config = self._registry.get("config") if self._registry else None
            if isinstance(config, dict):
                self._current_theme_name = config.get("editor", {}).get("theme", "dark")
            self._apply_theme_content(theme_content)
        else:
            self._current_theme_name = "dark"
            self._parse_styleSheet("editor/qss/dark.qss")

    def setup_layout(self) -> None:
        self.main_layout = self._build_main_layout()
        self._build_title_bar(self.main_layout)
        self._build_hero()
        self._build_status_bar(self.main_layout)

    def _build_main_layout(self) -> QVBoxLayout:
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        main_layout.addLayout(self.body_layout, stretch=1)

        return main_layout

    def _build_title_bar(self, main_layout: QVBoxLayout) -> None:
        self.title_bar = DreamStudioTitleBar(self, self.currentDirectory)
        self.options_menu = OptionsMenu(self, "editor/base/json/optionbar.json")

        main_layout.insertWidget(0, self.title_bar)
        main_layout.insertWidget(1, self.options_menu)

    def _build_hero(self) -> None:
        self.left_sidebar = VerticalSidebar(self, "editor/base/json/leftbar.json")
        self.hero_window = WorkspaceContainer(self)
        self.right_sidebar = VerticalSidebar(self, "editor/base/json/rightbar.json")

        self.tab_editors = self.hero_window._text_editor_center.tabs
        self.tab_editors.currentChanged.connect(self._sync_menu_state)

        self.body_layout.addWidget(self.left_sidebar)
        self.body_layout.addWidget(self.hero_window, stretch=1)
        self.body_layout.addWidget(self.right_sidebar)

        self._wire_sidebar_toggles()
        self._set_initial_workspace()
        self._wire_explorer_double_click()

    def _wire_sidebar_toggles(self) -> None:
        api = self.hero_window._vertical_menus_api
        api.panel_visibility_changed.connect(self._on_panel_visibility_changed)

    def _set_initial_workspace(self) -> None:
        root = QDir.currentPath()
        self.hero_window._source_control.set_workspace(root)

    def _wire_explorer_double_click(self) -> None:
        explorer = self.hero_window._solution_explorer
        explorer.tree_view.doubleClicked.connect(self._on_explorer_double_click)

    def _on_explorer_double_click(self, index) -> None:
        explorer = self.hero_window._solution_explorer
        source_index = explorer.proxy_model.mapToSource(index)
        if not source_index.isValid():
            return

        file_path = explorer.base_model.filePath(source_index)
        if not file_path or not os.path.isfile(file_path):
            return

        tabs = self.hero_window._text_editor_center.tabs
        tabs.open_file_by_path(file_path)

    def _build_status_bar(self, main_layout: QVBoxLayout) -> None:
        self.status_bar = StatusBar(self, self.currentDirectory)
        self.status_bar.notificationBtn.clicked.connect(self._toggle_notifications)
        self.status_bar.errorsBtn.clicked.connect(self._toggle_problems)
        main_layout.addWidget(self.status_bar)

    def _sync_menu_state(self) -> None:
        """Update File menu enabled/disabled state from current tab count."""
        has_tabs = self.tab_editors.count() > 0
        self.title_bar._update_menu_state(has_tabs)

    def _defer_menu_sync(self) -> None:
        """Schedule a menu-state sync after the next event-loop iteration.

        Call this after any operation that adds or removes tabs so the
        count is up-to-date when the check runs.
        """
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(0, self._sync_menu_state)

    def _on_ui_ready(self):
        workspace_root = QDir.currentPath()
        problems = self.hero_window._lower_widget.problems_window
        problems.run_workspace_analysis(workspace_root)
