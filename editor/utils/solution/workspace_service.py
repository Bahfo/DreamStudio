"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Central workspace/solution service that tracks the active project path and
re-points every path-dependent subsystem of the IDE when it changes.

Registered as ``workspace`` in the bootstrap ServiceRegistry. This is the
single source of truth for the currently opened solution.
"""

from editor import *

from editor.utils.git_control.status_service import get_status_service

logger = logging.getLogger(__name__)


def _lazy_solution_marker():
    """Import solution_marker lazily to avoid import-time cycles."""
    from editor.utils.solution.solution_marker import read_solution

    return read_solution


class WorkspaceService(QObject):
    """Track the active solution path and coordinate full workspace switches.

    Attributes:
        current_path (str): Absolute path of the active solution root.
        current_solution (dict): Metadata from ``.ds/solution.yaml`` when the
            active root carries a solution marker, otherwise an empty dict.
    """

    workspace_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._window = None
        self.current_path = ""
        self.current_solution: dict = {}

    # ------------------------------------------------------------------
    # Window attachment
    # ------------------------------------------------------------------

    def attach_window(self, window) -> None:
        """Bind the main IDE window that the hub re-points on every switch.

        Args:
            window: The DreamStudio QMainWindow instance.
        """
        self._window = window

    @property
    def window(self):
        """Return the attached DreamStudio window, or ``None``."""
        return self._window

    @property
    def solution_name(self) -> str:
        """Return a readable name for the active solution."""
        if self.current_solution.get("name"):
            return str(self.current_solution["name"])
        if self.current_path:
            return os.path.basename(self.current_path) or self.current_path
        return "DreamStudio"

    # ------------------------------------------------------------------
    # Workspace switching
    # ------------------------------------------------------------------

    def open_workspace(self, path: str) -> None:
        """Record *path* as active and run the full re-point hub.

        Args:
            path: Absolute path to the solution/folder to open.
        """
        self.current_path = os.path.abspath(path)
        self._reload_solution_marker()
        self.reset_workspace(self.current_path)
        self.workspace_changed.emit(self.current_path)
        logger.info("Workspace opened: %s", self.current_path)

    def reset_workspace(self, path: str) -> None:
        """Re-point every path-dependent subsystem of the attached IDE.

        Args:
            path: Absolute path to the solution/folder to activate.
        """
        path = os.path.abspath(path)
        self.current_path = path
        window = self._window
        if window is None:
            return

        window.currentDirectory = path
        try:
            window.setWindowTitle(f"{self.solution_name} - DreamStudio")
        except Exception:
            pass

        title_bar = getattr(window, "title_bar", None)
        if title_bar is not None:
            title_bar.directory = path

        status_bar = getattr(window, "status_bar", None)
        if status_bar is not None and hasattr(status_bar, "set_workspace"):
            status_bar.set_workspace(path)

        hero = getattr(window, "hero_window", None)
        if hero is not None:
            self._repoint_containers(hero, path)
            self._repoint_panels(hero, path)

        try:
            get_status_service().set_root(path)
        except Exception as exc:
            logger.warning("Git status service failed to re-root: %s", exc)

        find_replace = getattr(window, "_find_replace_window", None)
        if find_replace is not None:
            try:
                find_replace.current_directory = path
            except Exception:
                pass

        self._defer_problems_analysis(window, path)
        logger.info("Workspace re-pointed to: %s", path)

    # ------------------------------------------------------------------
    # Internal re-point helpers
    # ------------------------------------------------------------------

    def _reload_solution_marker(self) -> None:
        """Reload the active solution metadata from its marker file."""
        try:
            self.current_solution = _lazy_solution_marker()(self.current_path) or {}
        except Exception:
            self.current_solution = {}

    def _repoint_containers(self, hero, path: str) -> None:
        """Update the editor container cwd snapshots inside *hero*."""
        text_center = getattr(hero, "_text_editor_center", None)
        if text_center is not None:
            try:
                text_center.currentDirectory = path
                # Sync DreamTabbedEditor snapshot so "Open File" dialog follows the workspace.
                tabs = getattr(text_center, "tabs", None)
                if tabs is not None:
                    tabs.currentDirectory = path
            except Exception:
                pass
        lower_widget = getattr(hero, "_lower_widget", None)
        if lower_widget is not None:
            try:
                lower_widget.currentDirectory = path
            except Exception:
                pass
            # Re-point the integrated terminal (system shell default cwd + PromptX)
            term = getattr(lower_widget, "terminal_window", None)
            if term is not None and hasattr(term, "set_workspace"):
                try:
                    term.set_workspace(path)
                except Exception as exc:
                    logger.warning("Terminal re-point failed: %s", exc)

    def _repoint_panels(self, hero, path: str) -> None:
        """Update source control, explorer and TODO-search roots in *hero*."""
        source_control = getattr(hero, "_source_control", None)
        if source_control is not None and hasattr(source_control, "set_workspace"):
            try:
                source_control.set_workspace(path)
            except Exception as exc:
                logger.warning("Source control re-point failed: %s", exc)

        explorer = getattr(hero, "_solution_explorer", None)
        if explorer is not None and hasattr(explorer, "set_root_path"):
            try:
                explorer.set_root_path(path)
            except Exception as exc:
                logger.warning("Solution explorer re-point failed: %s", exc)

        todo = getattr(hero, "_todo_search", None)
        if todo is not None and hasattr(todo, "set_base_dir"):
            try:
                todo.set_base_dir(path)
            except Exception:
                pass

        # Properties panel — re-point to analyze the new workspace.
        properties = getattr(hero, "_properties_explorer", None)
        if properties is not None and hasattr(
            properties, "set_active_project_directory"
        ):
            try:
                properties.set_active_project_directory(path)
            except Exception as exc:
                logger.warning("Properties explorer re-point failed: %s", exc)

        # Server explorer — keep its base path in sync (placeholder panel).
        server = getattr(hero, "_server_explorer", None)
        if server is not None and hasattr(server, "set_workspace"):
            try:
                server.set_workspace(path)
            except Exception as exc:
                logger.warning("Server explorer re-point failed: %s", exc)

    def _defer_problems_analysis(self, window, path: str) -> None:
        """Schedule a workspace syntax analysis for the new root."""
        hero = getattr(window, "hero_window", None)
        lower = getattr(hero, "_lower_widget", None) if hero is not None else None
        problems = getattr(lower, "problems_window", None)
        if problems is None or not hasattr(problems, "run_workspace_analysis"):
            return
        QTimer.singleShot(0, lambda: self._safe_analysis(problems, path))

    def _safe_analysis(self, problems, path: str) -> None:
        """Best-effort problems analysis that never raises into the GUI."""
        try:
            problems.run_workspace_analysis(path)
        except Exception as exc:
            logger.warning("Workspace analysis failed: %s", exc)
