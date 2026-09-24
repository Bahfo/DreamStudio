from __future__ import annotations

from editor import *
from editor.utils.resource_path import resource_path

# Local Imports
from editor.utils.explorer.proxy import (
    ExplorerFilterProxy,
    DreamTreeView,
    ExplorerDelegate,
)
from editor.utils.explorer.menu import ExplorerClickMenu, MenuRegistry
from editor.utils.explorer.collapsable_menu import (
    ExplorerOptionsMenu,
    create_options_button,
)
from editor.utils.git_control.status_service import get_status_service
from editor.utils.explorer.gitignore import get_gitignore_service
from editor.widgets.QToolBox import ExplorerToolbar, ToolbarButton
from editor.utils.explorer.icons import DreamStudioIconProvider
from editor.utils.explorer.vcs_colors import build_status_index
from editor.utils.explorer.packages import DependenciesView
from editor.utils.explorer.api import ExplorerAPI
from editor.utils.panel_shell import PanelShell

try:
    import sip  # type: ignore
except ImportError:
    try:
        from PyQt6 import sip  # type: ignore
    except ImportError:
        sip = None  # type: ignore

logger = logging.getLogger(__name__)

MENU_JSON = Path(resource_path("editor/utils/explorer/menu.json"))

TOOLBAR_BUTTONS: dict[str, tuple[str, str]] = {
    "New File": ("_toolbar_new_file", resource_path("assets/menus/add.png")),
    "New Folder": ("_toolbar_new_folder", resource_path("assets/menus/folder.png")),
    "Delete Item": ("_toolbar_delete_item", resource_path("assets/menus/trash.png")),
    "Refresh": ("_toolbar_refresh", resource_path("assets/menus/restart.png")),
    "Collapse All": (
        "_toolbar_collapse_all",
        resource_path("assets/menus/collapse.png"),
    ),
    "Expand All": ("_toolbar_expand_all", resource_path("assets/menus/expand.png")),
}


@dataclass(frozen=True)
class ExplorerSelection:
    """
    Data container representing the user's active file system selection context.
    """

    path: str
    is_dir: bool
    name: str


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


class SolutionExplorer(PanelShell):
    """
    IDE sidebar management component managing local project workspaces and
    package systems via a clean, multi-tab layout interface.
    """

    PANEL_OBJECT_NAME = "SolutionExplorer"
    FRAME_OBJECT_NAME = "ExplorerFrame"
    TITLE_OBJECT_NAME = "ExplorerTitle"
    DIRECTORY_LABEL_OBJECT_NAME = "ExplorerDirectoryLabel"
    SEARCH_BAR_OBJECT_NAME = "ExplorerSearchBar"
    TREE_VIEW_OBJECT_NAME = "ExplorerTreeView"
    RENAME_EDITOR_OBJECT_NAME = "ExplorerRenameEditor"
    TITLE_TEXT = "Solution Explorer"
    SEARCH_DEBOUNCE_MS = 180

    def __init__(self, parent=None):
        """
        Initializes internal core system variables, views, proxies,
        and selection systems.
        """
        self._menu_registry = MenuRegistry()
        self._context_menu: ExplorerClickMenu | None = None

        self.base_model: QFileSystemModel | None = None
        self.proxy_model: ExplorerFilterProxy | None = None
        self.tree_view: DreamTreeView | None = None

        self._header_visible = False
        self._focus_connected = False
        self._suppress_search_signal = False

        super().__init__(parent)

        self._root_path = _inherit_workspace(self)

        self._setup_models()
        self._hide_extra_columns()
        self._setup_context_menu()
        self._setup_signals()
        self._setup_options_menu()

        self.set_workspace(self._root_path)
        self.setMinimumWidth(235)

    def _build_shell(self) -> None:
        """
        Constructs core view layouts and wires stacked view pages
        together natively.
        """
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._frame = QFrame(self)
        self._frame.setObjectName(self.FRAME_OBJECT_NAME)
        self._frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._frame_layout = QVBoxLayout(self._frame)
        self._frame_layout.setContentsMargins(10, 10, 10, 10)
        self._frame_layout.setSpacing(8)
        self._main_layout.addWidget(self._frame)

        self._build_header_row()
        self._build_tab_navigation()

        self.view_stack = QStackedWidget(self)
        self._build_explorer_page()
        self._build_packages_page()

        self._frame_layout.addWidget(self.view_stack)

    def _build_tab_navigation(self) -> None:
        """
        Creates top-level tab buttons to switch between file and
        package subsystems.
        """
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.btn_files = QPushButton("Files", self)
        self.btn_packages = QPushButton("Packages", self)

        self.btn_files.clicked.connect(lambda: self.view_stack.setCurrentIndex(0))
        self.btn_packages.clicked.connect(lambda: self.view_stack.setCurrentIndex(1))

        layout.addWidget(self.btn_files)
        layout.addWidget(self.btn_packages)
        layout.addStretch(1)

        self._frame_layout.addLayout(layout)

    def _build_explorer_page(self) -> None:
        """
        Constructs the primary file workspace navigator page for the
        stacked view layout.
        """
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._toolbar_row = QHBoxLayout()
        self._toolbar_row.setContentsMargins(0, 0, 0, 0)
        self._toolbar_row.setSpacing(8)

        self._dir_label = QLabel("Workspace: --")
        self._dir_label.setObjectName(self.DIRECTORY_LABEL_OBJECT_NAME)
        self._toolbar_row.addWidget(self._dir_label)
        self._toolbar_row.addStretch(1)

        self._explr_toolbox = ExplorerToolbar()
        self.populate_toolbar(TOOLBAR_BUTTONS)
        self._toolbar_row.addLayout(self._explr_toolbox)
        layout.addLayout(self._toolbar_row)

        self.search_bar = QLineEdit(page)
        self.search_bar.setObjectName(self.SEARCH_BAR_OBJECT_NAME)
        self.search_bar.setPlaceholderText("Search in workspace")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        layout.addWidget(self.search_bar)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(self.SEARCH_DEBOUNCE_MS)
        self._search_timer.timeout.connect(self._apply_search_text)

        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("ExplorerStatusLabel")

        self._status_row = QHBoxLayout()
        self._status_row.setContentsMargins(0, 0, 0, 0)
        self._status_row.setSpacing(4)
        self._status_row.addWidget(self._status_label)
        self._status_row.addStretch(1)
        layout.addLayout(self._status_row)

        self.tree_view = DreamTreeView(page)
        self.tree_view.setObjectName(self.TREE_VIEW_OBJECT_NAME)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setAnimated(False)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setAlternatingRowColors(False)
        self.tree_view.setExpandsOnDoubleClick(True)
        self.tree_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tree_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree_view.setSortingEnabled(True)
        layout.addWidget(self.tree_view)

        self.view_stack.addWidget(page)

    def _build_packages_page(self) -> None:
        """
        Constructs the runtime metadata dependencies page view for the stacked
        widget.
        """
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.packages_view = DependenciesView(page)
        layout.addWidget(self.packages_view)

        self.view_stack.addWidget(page)

    def _header_right_widgets(self) -> list[QWidget]:
        """
        Provides optional system panel context items for the structural view
        parent frame.
        """
        return [
            ToolbarButton(
                resource_path("editor/utils/explorer/assets/icons/dropdown.png"),
                "View more widget options",
                (20, 20),
                (15, 15),
            ),
        ]

    def _setup_models(self) -> None:
        """
        Configures core file system models, mapping sorting filters and
        tree configurations.
        """
        self.base_model = QFileSystemModel(self)
        self.base_model.setReadOnly(False)
        self.base_model.setIconProvider(DreamStudioIconProvider())
        self.base_model.setFilter(
            QDir.Filter.AllDirs
            | QDir.Filter.Files
            | QDir.Filter.NoDotAndDotDot
            | QDir.Filter.AllEntries
            | QDir.Filter.Hidden
        )

        self.proxy_model = ExplorerFilterProxy(self)
        self.proxy_model.setSourceModel(self.base_model)
        self.proxy_model.set_root_path(self._root_path)

        self.tree_view.setModel(self.proxy_model)
        self.tree_view.setItemDelegate(ExplorerDelegate(self.tree_view))
        self.tree_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        selection_model = self.tree_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self._on_selection_changed)

    def _setup_context_menu(self) -> None:
        """
        Loads contextual metadata registries and binds platform menu
        request mechanisms.
        """
        try:
            self._menu_registry.load_json(str(MENU_JSON))
        except Exception:
            pass

        self._context_menu = ExplorerClickMenu(
            tree=self.tree_view,
            model=self.base_model,
            registry=self._menu_registry,
            proxy_model=self.proxy_model,
            parent=self,
        )

        self._wire_menu_callbacks()
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(
            self._context_menu.show_context_menu
        )

    def _setup_signals(self) -> None:
        """
        Hooks search entry triggers and synchronizes application engine
        window focus tracks.
        """
        self.search_bar.textChanged.connect(self._on_search_text_changed)

        if not self._focus_connected:
            QApplication.instance().focusChanged.connect(self._on_app_focus_changed)
            self._focus_connected = True

        self.base_model.fileRenamed.connect(self._notify_vcs_activity)
        self.base_model.directoryLoaded.connect(self._notify_vcs_activity)
        self.base_model.rootPathChanged.connect(self._notify_vcs_activity)
        try:
            self.base_model.rowsInserted.connect(self._notify_vcs_activity)
            self.base_model.rowsRemoved.connect(self._notify_vcs_activity)
            self.base_model.dataChanged.connect(self._notify_vcs_activity)
        except Exception:
            pass
        get_status_service().statuses_updated.connect(self._on_vcs_statuses_updated)
        self._setup_vfs_watcher()
        self._connect_dirty_tracker()
        self._setup_gitignore_service()

    def _on_vcs_statuses_updated(self, repo_root: str, snapshot: dict) -> None:
        """
        Translate a published snapshot into the proxy color index.

        Args:
            repo_root: Repository working directory from the scan.
            snapshot: Repo-relative path to ``M``/``U``/``A`` symbols.
        """
        if not repo_root or not snapshot:
            self.proxy_model.apply_vcs_index({})
            return
        self.proxy_model.apply_vcs_index(build_status_index(repo_root, snapshot))

    def _notify_vcs_activity(self, *args) -> None:
        """Request a rescan after a local mutating operation."""
        get_status_service().request_scan("explorer")

    def _setup_vfs_watcher(self) -> None:
        """Watch workspace root for external file add/delete/modify events."""
        try:
            self._fs_watcher = QFileSystemWatcher(self)
            self._fs_watcher.directoryChanged.connect(self._notify_vcs_activity)
            self._fs_watcher.fileChanged.connect(self._notify_vcs_activity)
            if self._root_path and os.path.isdir(self._root_path):
                self._fs_watcher.addPath(self._root_path)
        except Exception:
            self._fs_watcher = None

    def _refresh_vfs_watcher(self) -> None:
        """Re-point the filesystem watcher at the current workspace root."""
        watcher = getattr(self, "_fs_watcher", None)
        if watcher is None:
            return
        try:
            for p in watcher.directories():
                watcher.removePath(p)
            for p in watcher.files():
                watcher.removePath(p)
            if self._root_path and os.path.isdir(self._root_path):
                watcher.addPath(self._root_path)
        except Exception:
            pass

    def _connect_dirty_tracker(self) -> None:
        """Wire dirty-state changes from code editors to VCS activity.

        Covers requirements:
        1. Dirty state true for a file inside the code editor.
        2. Dirty state updated (true->false or false->true).
        This hooks every ``dirty_state_changed`` signal found in the
        application, including future editors created after startup.
        """

        def _hook() -> None:
            if not hasattr(self, "_dirty_hook_timer") or self._dirty_hook_timer is None:
                return
            app = QApplication.instance()
            if app is None:
                return
            for w in app.allWidgets():
                if hasattr(w, "dirty_state_changed"):
                    try:
                        # Skip deleted wrappers
                        if not w:
                            continue
                        if sip is not None and sip.isdeleted(w):
                            continue
                        if not getattr(w, "_vcs_dirty_connected", False):
                            w.dirty_state_changed.connect(self._notify_vcs_activity)
                            w._vcs_dirty_connected = True  # type: ignore
                            # Auto-cleanup on destruction
                            try:
                                w.destroyed.connect(
                                    lambda _=None, ww=w: self._on_editor_destroyed_for_vcs(
                                        ww
                                    )
                                )
                            except Exception:
                                pass
                    except RuntimeError:
                        pass
                    except Exception:
                        pass

        QTimer.singleShot(400, _hook)
        self._dirty_hook_timer = QTimer(self)
        self._dirty_hook_timer.setInterval(1200)
        self._dirty_hook_timer.timeout.connect(_hook)
        self._dirty_hook_timer.start()
        try:
            self.destroyed.connect(self._cleanup_dirty_tracker)
        except Exception:
            pass

    def _on_editor_destroyed_for_vcs(self, obj):
        try:
            if hasattr(obj, "_vcs_dirty_connected"):
                delattr(obj, "_vcs_dirty_connected")
        except Exception:
            pass

    def _cleanup_dirty_tracker(self):
        t = getattr(self, "_dirty_hook_timer", None)
        if t is not None:
            try:
                t.stop()
                t.deleteLater()
            except Exception:
                pass
            self._dirty_hook_timer = None

    def closeEvent(self, event):
        self._cleanup_dirty_tracker()
        super().closeEvent(event)

    def _setup_gitignore_service(self) -> None:
        """Wire the gitignore parser service to the proxy model.

        - Reads ``.gitignore`` line by line via :mod:`editor.utils.explorer.gitignore`.
        - Highlights ignored files with a faded-gray text color (VSCode-like).
        - Updates each time ``.gitignore`` is modified (resaved).
        - If no ``.gitignore`` exists the service emits ``[]`` and stays
          idle until the file is created for the first time.
        """
        try:
            service = get_gitignore_service()
            try:
                service.patterns_updated.disconnect(self._on_gitignore_updated)
            except Exception:
                pass
            service.patterns_updated.connect(self._on_gitignore_updated)
            if self._root_path:
                service.set_root(self._root_path)
                patterns = service.patterns()
                self.proxy_model.apply_gitignore_patterns(patterns)
        except Exception as exc:
            logger.debug("GitIgnore setup failed: %s", exc)

    def _on_gitignore_updated(self, patterns: list) -> None:
        """Apply new gitignore patterns to the proxy and repaint.

        Args:
            patterns: Raw pattern list emitted by :class:`GitIgnoreService`.
                Empty list means no ``.gitignore`` – highlighting disabled.
        """
        try:
            self.proxy_model.apply_gitignore_patterns(patterns or [])
            if self.tree_view is not None:
                try:
                    self.tree_view.viewport().update()
                    self.tree_view.update()
                except Exception:
                    pass
        except Exception:
            pass

    def _setup_options_menu(self) -> None:
        self._options_menu = ExplorerOptionsMenu(
            proxy_model=self.proxy_model,
            workspace_root_fn=lambda: self._root_path,
            parent=self,
        )

        self._options_btn = create_options_button(
            self._options_menu,
            parent=self,
        )
        self._status_row.addWidget(self._options_btn)

    def _wire_menu_callbacks(self) -> None:
        """
        Binds registry identifiers to internal file manipulation utility methods.
        """
        callbacks = {
            "cut": self._menu_cut,
            "copy": self._menu_copy,
            "paste": self._menu_paste,
            "copy_path": self._menu_copy_path,
            "rename": self._menu_rename,
            "delete": self._menu_delete,
            "open_explorer": self._menu_open_explorer,
            "toggle_header_visibility": self._menu_toggle_header_visibility,
        }

        for action_name, handler in callbacks.items():
            self._context_menu.register_callback(action_name, handler)

    def set_workspace(self, root_path: str) -> None:
        """
        Sets, cleans, and updates the local repository system directory
        path context.
        """
        resolved = os.path.abspath(os.path.expanduser(root_path))
        if not os.path.exists(resolved):
            resolved = os.getcwd()

        self._root_path = resolved
        self.proxy_model.set_root_path(self._root_path)
        self.base_model.setRootPath(self._root_path)

        source_index = self.base_model.index(self._root_path)
        proxy_index = self.proxy_model.mapFromSource(source_index)

        self.tree_view.setRootIndex(proxy_index)
        self.tree_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        self._update_directory_label()
        self._update_status_label()
        self.proxy_model.set_search_text(self.search_bar.text())
        self._ensure_root_visible()
        self._refresh_vfs_watcher()
        try:
            get_gitignore_service().set_root(self._root_path)
        except Exception:
            pass
        # Propagate workspace to the Packages tab so pip operations run in the right directory.
        if hasattr(self, "packages_view") and self.packages_view is not None:
            try:
                self.packages_view.set_workspace(self._root_path)
            except Exception as exc:
                logger.warning("Packages explorer re-point failed: %s", exc)

    def set_root_path(self, root_path: str) -> None:
        """
        Redirects workspace targets seamlessly down to path parameters.
        """
        self.set_workspace(root_path)

    def _display_name(self, path: str) -> str:
        """
        Extracts readable baseline directories or file headers safely.
        """
        normalized = os.path.normpath(path)
        name = os.path.basename(normalized)
        return name or normalized

    def _workspace_name(self) -> str:
        """
        Retrieves user-friendly representation text of current directory
        context.
        """
        return self._display_name(self._root_path)

    def _update_directory_label(self) -> None:
        """
        Synchronizes label views with current project location details.
        """
        self._dir_label.setText(f"Workspace: {self._workspace_name()}")

    def _selected_selection(self) -> Optional[ExplorerSelection]:
        """
        Resolves active index references into complete path metrics data
        snapshots.
        """
        index = self.current_index()
        if not index.isValid():
            return None

        source_index = self.proxy_model.mapToSource(index)
        if not source_index.isValid():
            return None

        path = self.base_model.filePath(source_index)
        if not path:
            return None

        return ExplorerSelection(
            path=path,
            is_dir=self.base_model.isDir(source_index),
            name=self.base_model.fileName(source_index) or self._display_name(path),
        )

    def _selected_path(self) -> Optional[str]:
        """
        Fetches active item locations from user node selections safely.
        """
        selection = self._selected_selection()
        return selection.path if selection else None

    def current_index(self) -> QModelIndex:
        """
        Retrieves current tree locator selection indices safely.
        """
        if self.tree_view is None:
            return QModelIndex()
        return self.tree_view.currentIndex()

    def _current_directory(self) -> Optional[str]:
        """
        Deduces working directory baselines derived from active node indices.
        """
        selection = self._selected_selection()
        if selection is None:
            return self._root_path
        if selection.is_dir:
            return selection.path
        parent = ExplorerAPI.parent_dir(selection.path)
        return parent or self._root_path

    def _run_if_selected(self, action: Callable[[str], None]) -> None:
        """
        Guards and forwards valid path parameters safely toward active routines.
        """
        path = self._selected_path()
        if path:
            action(path)

    def _run_if_directory(self, action: Callable[[str], None]) -> None:
        """
        Guards and maps system paths dynamically into local location operations.
        """
        target = self._current_directory()
        if target:
            action(target)

    def _menu_cut(self) -> None:
        self._run_if_selected(ExplorerAPI.cut_item)

    def _menu_copy(self) -> None:
        self._run_if_selected(ExplorerAPI.copy_item)

    def _menu_paste(self) -> None:
        target = self._current_directory()
        if target:
            ExplorerAPI.paste_item(self, target)
        self._notify_vcs_activity()

    def _menu_copy_path(self) -> None:
        self._run_if_selected(ExplorerAPI.copy_path)

    def _menu_rename(self) -> None:
        path = self._selected_path()
        if path:
            result = ExplorerAPI.rename_item(self, path)
            if result:
                self._notify_vcs_activity()
            else:
                self._notify_vcs_activity()

    def _menu_delete(self) -> None:
        path = self._selected_path()
        if path:
            result = ExplorerAPI.delete_item(self, path)
            if result:
                self._notify_vcs_activity()
            else:
                self._notify_vcs_activity()
        else:
            self._notify_vcs_activity()

    def _menu_open_explorer(self) -> None:
        self._run_if_selected(ExplorerAPI.open_in_system_explorer)

    def _menu_toggle_header_visibility(self) -> None:
        """
        Toggles horizontal table headers and metadata descriptors cleanly.
        """
        self._header_visible = not self._header_visible
        self.tree_view.setHeaderHidden(not self._header_visible)
        for col in (1, 2, 3):
            self.tree_view.setColumnHidden(col, not self._header_visible)

    def _hide_extra_columns(self) -> None:
        """
        Hides non-primary structural data sections from standard listings.
        """
        for col in (1, 2, 3):
            self.tree_view.setColumnHidden(col, True)

    def _toolbar_new_file(self) -> None:
        self._run_if_directory(lambda target: ExplorerAPI.new_file(self, target))
        self._notify_vcs_activity()

    def _toolbar_new_folder(self) -> None:
        self._run_if_directory(lambda target: ExplorerAPI.new_folder(self, target))
        self._notify_vcs_activity()

    def _toolbar_delete_item(self) -> None:
        self._run_if_selected(lambda path: ExplorerAPI.delete_item(self, path))
        self._notify_vcs_activity()

    def _toolbar_refresh(self) -> None:
        self.refresh()

    def _toolbar_collapse_all(self) -> None:
        ExplorerAPI.collapse_all(self.tree_view)

    def _toolbar_expand_all(self) -> None:
        ExplorerAPI.expand_all(self.tree_view)

    def _on_search_text_changed(self, _text: str) -> None:
        self._search_timer.start()

    def _apply_search_text(self) -> None:
        text = self.search_bar.text()
        self.handle_search(text)

    def handle_search(self, text: str) -> None:
        """
        Applies input filter guidelines against active layout proxies safely.
        """
        cleaned = (text or "").strip()
        self.proxy_model.set_search_text(cleaned)
        self._ensure_root_visible()
        self._update_status_label()

    def refresh(self) -> None:
        """
        Re-scans disk changes without dumping or dropping user search states.
        """
        current_search = self.search_bar.text()

        self.base_model.setRootPath(self._root_path)
        source_index = self.base_model.index(self._root_path)
        proxy_index = self.proxy_model.mapFromSource(source_index)
        self.tree_view.setRootIndex(proxy_index)

        self.proxy_model.invalidate()
        self.proxy_model.set_search_text(current_search)
        self.tree_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        self._ensure_root_visible()
        self._update_status_label()
        self._notify_vcs_activity()

    def go_to_parent_workspace(self) -> None:
        """
        Ascends standard path tracks to process parent storage workspace tiers.
        """
        parent = os.path.dirname(self._root_path.rstrip(os.sep))
        if parent and parent != self._root_path:
            self.set_workspace(parent)

    def set_show_hidden(self, show_hidden: bool) -> None:
        """
        Toggles system node filtering configs for operating system hidden
        attributes.
        """
        self.proxy_model.set_show_hidden(show_hidden)
        self._ensure_root_visible()
        self._update_status_label()

    def toggle_show_hidden(self) -> None:
        self.set_show_hidden(not self.proxy_model.show_hidden())

    def is_show_hidden_enabled(self) -> bool:
        return self.proxy_model.show_hidden()

    def _ensure_root_visible(self) -> None:
        """
        Enforces structural alignment to guarantee project root directories
        map cleanly.
        """
        source_index = self.base_model.index(self._root_path)
        proxy_index = self.proxy_model.mapFromSource(source_index)
        if proxy_index.isValid():
            self.tree_view.setRootIndex(proxy_index)

    def _update_status_label(self) -> None:
        """
        Refreshes system descriptor labels based on selection metrics.
        """
        selection = self._selected_selection()
        search_text = self.proxy_model.search_text()

        if selection is None:
            selection_text = "No selection"
        else:
            kind = "Folder" if selection.is_dir else "File"
            selection_text = f"{kind}: {selection.name}"

        if search_text:
            self._status_label.setText(f"{selection_text}  |  Filter: {search_text}")
        else:
            self._status_label.setText(selection_text)

    def _on_selection_changed(
        self, current: QModelIndex, previous: QModelIndex
    ) -> None:
        self._update_status_label()

    def _on_app_focus_changed(self, old, new) -> None:
        """
        Monitors workspace environment focus structures to polish style changes.
        """
        focused = False
        if new is not None:
            w = new
            while w is not None:
                if w is self:
                    focused = True
                    break
                try:
                    w = w.parent()
                except (TypeError, RuntimeError):
                    break
        self._set_frame_focused(focused)

    def _set_frame_focused(self, focused: bool) -> None:
        self._frame.setProperty("focused", focused)
        self._frame.style().unpolish(self._frame)
        self._frame.style().polish(self._frame)

    def populate_toolbar(self, buttons_dict: dict[str, tuple[str, str]]) -> None:
        """
        Purges and rebuilds toolbar actions from structured navigation
        dictionaries.
        """
        for btn in list(self._explr_toolbox._buttons):
            self._explr_toolbox.removeWidget(btn)
            btn.deleteLater()

        self._explr_toolbox._buttons.clear()

        for tooltip, (method_name, icon_path) in buttons_dict.items():
            callback = getattr(self, method_name, None) if method_name.strip() else None
            self._explr_toolbox.add_button(
                icon_path=icon_path,
                tooltip=tooltip,
                callback=callback,
            )

    def selected_path(self) -> Optional[str]:
        return self._selected_path()

    def workspace_root(self) -> str:
        return self._root_path

    def set_current_path(self, path: str) -> None:
        """
        Focuses and centers project view tracking nodes over explicit
        target files.
        """
        if not path:
            return

        resolved = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(resolved):
            return

        self.set_workspace(
            os.path.dirname(resolved) if os.path.isfile(resolved) else resolved
        )

        source_index = self.base_model.index(resolved)
        if not source_index.isValid():
            return

        proxy_index = self.proxy_model.mapFromSource(source_index)
        if proxy_index.isValid():
            self.tree_view.setCurrentIndex(proxy_index)
            self.tree_view.scrollTo(
                proxy_index, QAbstractItemView.ScrollHint.PositionAtCenter
            )
            self._update_status_label()

    def open_workspace(self, root_path: str) -> None:
        self.set_workspace(root_path)

    def expand_workspace(self) -> None:
        ExplorerAPI.expand_all(self.tree_view)

    def collapse_workspace(self) -> None:
        ExplorerAPI.collapse_all(self.tree_view)

    def focus_search(self) -> None:
        self.search_bar.setFocus(Qt.FocusReason.OtherFocusReason)
        self.search_bar.selectAll()

    def clear_search(self) -> None:
        self.search_bar.clear()

    def selected_directory(self) -> str:
        return self._current_directory() or self._root_path

    def create_file_here(self) -> None:
        target = self.selected_directory()
        ExplorerAPI.new_file(self, target)
        self._notify_vcs_activity()

    def create_folder_here(self) -> None:
        target = self.selected_directory()
        result = ExplorerAPI.new_folder(self, target)
        self._notify_vcs_activity()

    def copy_selected_path(self) -> None:
        self._menu_copy_path()

    def rename_selected(self) -> None:
        self._menu_rename()

    def delete_selected(self) -> None:
        self._menu_delete()

    def open_in_system_explorer(self) -> None:
        self._menu_open_explorer()
