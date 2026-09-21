from editor import *
from editor.workspace_container import WorkspaceContainer
from editor.utils.resource_path import resource_path
from editor.api.editor_api import EditorAPI
from editor.api.menus_api import MenusAPI

# Local Imports
from editor.base.statusBar import StatusBar
from editor.base.optionsBar import OptionsMenu
from editor.base.verticalBar import VerticalSidebar
from editor.base.titleBar import DreamStudioTitleBar

# Quiet period after the last keystroke before the file outline is
# rebuilt.  The outline rebuild parses the whole buffer (ast.parse) and
# recreates the entire symbol tree, so it must never run synchronously
# inside ``textChanged``.
OUTLINE_REFRESH_DEBOUNCE_MS = 600


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
            self._parse_styleSheet(resource_path("editor/qss/dark.qss"))

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
        self.options_menu = OptionsMenu(self, resource_path("editor/base/json/optionbar.json"))

        main_layout.insertWidget(0, self.title_bar)
        main_layout.insertWidget(1, self.options_menu)

    def _build_hero(self) -> None:
        self.left_sidebar = VerticalSidebar(self, resource_path("editor/base/json/leftbar.json"))
        self.hero_window = WorkspaceContainer(self)
        self.right_sidebar = VerticalSidebar(self, resource_path("editor/base/json/rightbar.json"))

        self.tab_editors = self.hero_window._text_editor_center.tabs
        self.tab_editors.currentChanged.connect(self._sync_menu_state)
        self.tab_editors.currentChanged.connect(self._sync_outline)

        # Run dropdown: dynamic state + saved run configurations.
        from editor.debugger.run.run_menu import RunMenuController

        self._run_menu = RunMenuController(self)
        self.tab_editors.currentChanged.connect(self._run_menu.refresh_state)

        self.body_layout.addWidget(self.left_sidebar)
        self.body_layout.addWidget(self.hero_window, stretch=1)
        self.body_layout.addWidget(self.right_sidebar)

        self._wire_sidebar_toggles()
        self._set_initial_workspace()
        self._wire_explorer_double_click()
        self._wire_outline_panel()

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

    # ------------------------------------------------------------------
    # Outline wiring
    # ------------------------------------------------------------------

    def _wire_outline_panel(self) -> None:
        """Connect the outline panel's symbol click to editor navigation."""
        outline = self.hero_window._file_outline
        outline.symbol_clicked.connect(self._on_outline_symbol_clicked)
        self._outline_text_connection = None

        # Debounced outline refresh: every keystroke restarts this timer
        # and the whole-document rebuild runs once, after typing pauses.
        self._outline_refresh_timer = QTimer(self)
        self._outline_refresh_timer.setSingleShot(True)
        self._outline_refresh_timer.setInterval(OUTLINE_REFRESH_DEBOUNCE_MS)
        self._outline_refresh_timer.timeout.connect(
            self._refresh_outline_for_current_editor
        )

        # Also refresh outline when the panel becomes visible (e.g. first
        # activation — currentChanged won't fire for an already-open tab).
        api = self.hero_window._vertical_menus_api
        api.panel_visibility_changed.connect(self._on_outline_visibility_changed)

    def _on_outline_visibility_changed(self, panel_id: str, visible: bool) -> None:
        """Refresh the outline when the outline panel becomes visible."""
        if panel_id == "file_outline" and visible:
            QTimer.singleShot(0, self._sync_outline)

    def _on_outline_symbol_clicked(self, line: int) -> None:
        """Scroll the active editor to the clicked outline symbol."""
        api = self.hero_window._text_editor_center.current_editor()
        if api is None:
            return
        editor = api.editor
        editor.setCursorPosition(line, 0)
        editor.ensureCursorVisible()
        editor.setFocus(Qt.FocusReason.MouseFocusReason)

    def _sync_outline(self, _index: int = -1) -> None:
        """Rebuild the outline tree for the currently active editor."""
        outline = self.hero_window._file_outline

        api = self.hero_window._text_editor_center.current_editor()
        if api is None:
            outline.clear_outline()
            return

        editor = api.editor

        # (Re)bind live updates to the active editor before any early
        # return, so even an empty buffer keeps tracking text changes.
        if self._outline_text_connection is not None:
            try:
                self._outline_text_connection[0].textChanged.disconnect(
                    self._outline_text_connection[1]
                )
            except (TypeError, RuntimeError):
                pass
            self._outline_text_connection = None

        try:
            editor.textChanged.connect(self._on_outline_text_changed)
            self._outline_text_connection = (editor, self._on_outline_text_changed)
        except (TypeError, RuntimeError):
            pass

        source = editor.text()
        lang = getattr(editor, "current_lang", None)

        if not lang or not source:
            outline.clear_outline()
            return

        self._update_outline_for_editor(editor)

    def _on_outline_text_changed(self) -> None:
        """Debounced outline refresh when the editor text changes.

        Restarts the single-shot refresh timer instead of rebuilding
        synchronously: a per-keystroke rebuild parses the entire buffer
        and recreates the whole symbol tree, which freezes typing on
        large files.  Rebuilds are also skipped while the outline panel
        is hidden; the visibility hook rebuilds the tree when the panel
        is re-opened.
        """
        outline = self.hero_window._file_outline
        if not outline.isVisible():
            return
        timer = getattr(self, "_outline_refresh_timer", None)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(OUTLINE_REFRESH_DEBOUNCE_MS)
            timer.timeout.connect(self._refresh_outline_for_current_editor)
            self._outline_refresh_timer = timer
        timer.start()

    def _refresh_outline_for_current_editor(self) -> None:
        """Run the debounced outline rebuild for the active editor."""
        outline = self.hero_window._file_outline
        if not outline.isVisible():
            return
        api = self.hero_window._text_editor_center.current_editor()
        if api is None:
            return
        self._update_outline_for_editor(api.editor)

    def _update_outline_for_editor(self, editor) -> None:
        """Build and push the outline for a specific editor."""
        outline = self.hero_window._file_outline
        source = editor.text()
        lang = getattr(editor, "current_lang", None)

        if not lang or not source:
            outline.clear_outline()
            return

        try:
            from editor.utils.file_properties.outline import build_outline

            result = build_outline(
                source, lang,
                filename=getattr(editor, "current_file_path", "") or "",
            )
            outline.update_outline(result)
        except Exception:
            outline.clear_outline()

    def _build_status_bar(self, main_layout: QVBoxLayout) -> None:
        self.status_bar = StatusBar(self, self.currentDirectory)
        self.status_bar.notificationBtn.clicked.connect(self._toggle_notifications)
        self.status_bar.errorsBtn.clicked.connect(self._toggle_problems)
        main_layout.addWidget(self.status_bar)

    def _sync_menu_state(self, _idx: int = -1) -> None:
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

    def _on_free_trial_click(self) -> None:
        self.hero_window._text_editor_center.tabs.open_free_trial_tab()

    def _on_welcome_btn_click(self) -> None:
        self.hero_window._text_editor_center.tabs.open_welcome_window()
