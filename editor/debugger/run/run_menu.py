"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Controller for the Run dropdown of the options bar: dynamic
enable/disable state, saved-config entries, and execution of run
commands through DreamStudio's integrated terminal.
"""

import json
import logging
import os
import re
import sys

from editor import *

from editor.debugger.run.config_run import ConfigRun
from editor.debugger.run.run_config_dialog import RunConfigDialog
from editor.utils.notifications.notification_manager import get_notification_manager
from editor.utils.resource_path import resource_path
from editor.terminal.terminal_ui import TAB_SYSTEM_SHELL

logger = logging.getLogger(__name__)

RUN_MENU_TEXT = "Run"
RUN_ACTION_TEXT = "Run Current File"
DEBUG_ACTION_TEXT = "Run and Debug Current File"
CONFIG_ACTION_TEXT = "Configure Run Options ..."

PYTHON_SUFFIX = ".py"


def is_runnable_python_file(path: str | None) -> bool:
    """Check whether the given path is a Python file that exists on disk.

    Args:
        path: File path from the active editor (may be None for unsaved
          or absent documents).

    Returns:
        True only for existing ``.py`` files.
    """
    return bool(path) and path.endswith(PYTHON_SUFFIX) and os.path.isfile(path)


def run_configs_dir() -> str:
    """Return (and create) the directory holding saved run configurations.

    Uses the existing project ``.configs`` persistence location so run
    configurations survive restarts like every other setting.

    Returns:
        Absolute path to the run-configurations directory.
    """
    directory = resource_path(os.path.join(".configs", "run"))
    os.makedirs(directory, exist_ok=True)
    return directory


def _config_file_stem(config_name: str) -> str:
    """Derive a filesystem-safe file stem from a configuration name."""
    stem = re.sub(r"[^\w\-]+", "_", config_name).strip("_")
    return stem or "config"


class RunMenuController:
    """Owns the Run dropdown behavior.

    Responsibilities: synchronizing the enabled/disabled state of the
    built-in run actions with the active editor, inserting saved
    `ConfigRun` configurations into the dropdown, saving new
    configurations from the `RunConfigDialog`, and dispatching execution
    to the integrated terminal.
    """

    def __init__(self, window):
        self._window = window
        self._run_button = None
        self._run_action: QAction | None = None
        self._debug_action: QAction | None = None
        self._config_action: QAction | None = None
        self._dynamic_actions: list[QAction] = []

        self._discover_menu()
        if self._run_menu is not None:
            # Keep the state in sync right before every dropdown open,
            # in addition to the tab-change notifications.
            self._run_menu.aboutToShow.connect(self.refresh_state)
        self.refresh_state()

    # ------------------------------------------------------------------
    # Menu discovery
    # ------------------------------------------------------------------

    @property
    def _run_menu(self) -> QMenu | None:
        """The Run dropdown menu, or None when it could not be located."""
        if self._run_button is None:
            return None
        return self._run_button.menu

    def _discover_menu(self) -> None:
        """Locate the Run dropdown and its actions in the options bar."""
        options_menu = getattr(self._window, "options_menu", None)
        if options_menu is None:
            logger.warning("Run menu controller: options bar not found.")
            return

        self._run_button = getattr(options_menu, "_menu_buttons", {}).get(
            RUN_MENU_TEXT
        )
        actions = getattr(options_menu, "_menu_actions", {}).get(RUN_MENU_TEXT, {})
        self._run_action = actions.get(RUN_ACTION_TEXT)
        self._debug_action = actions.get(DEBUG_ACTION_TEXT)
        self._config_action = actions.get(CONFIG_ACTION_TEXT)

        if self._run_action is None or self._config_action is None:
            logger.warning("Run menu controller: Run dropdown actions not found.")

    # ------------------------------------------------------------------
    # State synchronization
    # ------------------------------------------------------------------

    def current_file_path(self) -> str | None:
        """Return the active editor's file path via the existing tab model.

        Returns:
            The active ``current_file_path``, or None when no editor is
            open or the document has no filesystem path yet.
        """
        tabs = getattr(self._window, "tab_editors", None)
        if tabs is None:
            return None
        widget = tabs.currentWidget()
        if widget is None:
            return None
        return getattr(widget, "current_file_path", None) or None

    def refresh_state(self, _index: int = -1) -> None:
        """Re-evaluate action states and rebuild the config entries.

        Args:
            _index: Optional tab index from ``currentChanged`` (ignored).
        """
        path = self.current_file_path()
        runnable = is_runnable_python_file(path)

        if self._run_action is not None:
            self._run_action.setEnabled(runnable)
        if self._debug_action is not None:
            self._debug_action.setEnabled(runnable)
        if self._config_action is not None:
            self._config_action.setEnabled(True)

        self._rebuild_config_actions()

    # ------------------------------------------------------------------
    # Saved configurations
    # ------------------------------------------------------------------

    def _load_config_files(self) -> list[tuple[str, str, dict]]:
        """Load every saved run configuration from disk.

        Returns:
            A list of ``(display_name, json_path, options)`` tuples;
            malformed files are skipped with a logged warning.
        """
        configs: list[tuple[str, str, dict]] = []
        try:
            entries = sorted(os.listdir(run_configs_dir()))
        except OSError as exc:
            logger.error("Cannot read run configuration directory: %s", exc)
            return configs

        for entry in entries:
            if not entry.endswith(".json"):
                continue
            path = os.path.join(run_configs_dir(), entry)
            try:
                options = ConfigRun(config_name=entry[:-5]).load_config(path)
            except FileNotFoundError:
                continue
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Skipping malformed run configuration %s: %s", path, exc
                )
                continue
            name = options.get("config_name") or entry[:-5]
            configs.append((str(name), path, options))
        return configs

    def save_configuration(self, options: dict) -> str:
        """Persist a run configuration via `ConfigRun`.

        Args:
            options: Config dict (``config_name``, ``file_path``, ``Arg``,
              ``Parameters``).

        Returns:
            The path of the saved JSON file.
        """
        name = str(options.get("config_name", "dsconfig") or "dsconfig")
        target = os.path.join(run_configs_dir(), f"{_config_file_stem(name)}.json")
        ConfigRun(
            file_path=options.get("file_path"),
            config_name=name,
            options=dict(options),
        ).save_config(save_path=target)
        return target

    def _rebuild_config_actions(self) -> None:
        """Re-insert one menu action per saved configuration.

        Entries are inserted between the built-in actions and the
        "Configure Run Options ..." entry; previously inserted actions
        are removed first so the list never duplicates.
        """
        menu = self._run_menu
        if menu is None or self._config_action is None:
            return

        for action in self._dynamic_actions:
            menu.removeAction(action)
        self._dynamic_actions.clear()

        configs = self._load_config_files()
        if not configs:
            return

        separator = menu.insertSeparator(self._config_action)
        self._dynamic_actions.append(separator)

        for name, path, _options in configs:
            action = QAction(name, menu)
            action.setData(path)
            action.triggered.connect(
                lambda checked=False, config_path=path: self.run_configuration(
                    config_path
                )
            )
            menu.insertAction(self._config_action, action)
            self._dynamic_actions.append(action)

    def open_config_dialog(self) -> None:
        """Open the run-configuration editor and save on acceptance."""
        current_path = self.current_file_path() or ""
        dialog = RunConfigDialog(
            parent=self._window, initial={"file_path": current_path}
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            options = dialog.get_config()
            saved_path = self.save_configuration(options)
        except (ValueError, OSError) as exc:
            self._notify_error("Configure Run Options", f"Failed to save: {exc}")
            return

        get_notification_manager().add_success(
            "Configure Run Options",
            f"Saved run configuration '{options['config_name']}' ({saved_path}).",
            source="Run",
        )
        self._rebuild_config_actions()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run_current_file(self) -> None:
        """Execute the active Python file inside a new integrated terminal."""
        path = self.current_file_path()
        if not is_runnable_python_file(path):
            self._notify_error(
                "Run Current File",
                "No saved Python file is currently active.",
            )
            return

        widget = self._window.tab_editors.currentWidget()
        if widget is not None and hasattr(widget, "isModified") and widget.isModified():
            if hasattr(widget, "save"):
                widget.save()

        config = ConfigRun(
            file_path=path,
            config_name="run_current_file",
            options={
                "config_name": "run_current_file",
                "file_path": path,
                "Arg": sys.executable,
                "Parameters": [],
            },
        )

        try:
            argv, work_dir = config.build_command()
        except (ValueError, OSError) as exc:
            self._notify_error(
                "Run Current File", f"Failed to resolve command: {exc}"
            )
            return

        self._execute_in_terminal(argv, work_dir, name=os.path.basename(path))

    def run_configuration(self, config_path: str) -> None:
        """Execute a saved run configuration inside a new terminal.

        Args:
            config_path: Path of the configuration JSON file.
        """
        try:
            options = ConfigRun().load_config(config_path)
        except (OSError, json.JSONDecodeError) as exc:
            self._notify_error("Run", f"Failed to load configuration: {exc}")
            return

        if not options.get("Arg"):
            self._notify_error(
                "Run", f"Malformed configuration (missing 'Arg'): {config_path}"
            )
            return

        target = os.path.expanduser(str(options.get("file_path") or ""))
        if not target or not os.path.isfile(target):
            self._notify_error(
                "Run", f"Configured file does not exist: {target or '(empty)'}"
            )
            return

        config = ConfigRun(options=options)
        try:
            argv, work_dir = config.build_command()
        except (ValueError, OSError) as exc:
            self._notify_error("Run", f"Failed to resolve command: {exc}")
            return

        self._execute_in_terminal(
            argv, work_dir, name=str(options.get("config_name") or "Run")
        )

    def _execute_in_terminal(self, argv: list[str], work_dir: str, name: str) -> None:
        """Create a new integrated terminal session and run the command in it.

        Args:
            argv: The full argument sequence to execute.
            work_dir: Working directory for the new session.
            name: Display name for the terminal session tab.
        """
        lower = self._window.hero_window._lower_widget
        panel = getattr(lower, "terminal_window", None)
        workspace = getattr(panel, "system_shell_tab", None)
        if panel is None or workspace is None:
            self._notify_error("Run", "The integrated terminal is not available.")
            return

        try:
            started = workspace.open_command_session(argv, cwd=work_dir, name=name)
        except (RuntimeError, OSError) as exc:
            self._notify_error("Run", f"Failed to start terminal session: {exc}")
            return

        if not started:
            self._notify_error("Run", "Failed to create a terminal session.")
            return

        # Surface the terminal panel without toggling it off when open.
        if not lower.isVisible():
            lower._stack.setCurrentWidget(panel)
            lower.setVisible(True)
            self._window.hero_window._main_vertical_splitter.setSizes([600, 400])
        panel.switch_tab(TAB_SYSTEM_SHELL)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def _notify_error(self, title: str, message: str) -> None:
        """Surface an error through the central notification manager.

        Args:
            title: Short notification title.
            message: Detailed error message.
        """
        logger.error("%s: %s", title, message)
        get_notification_manager().add_error(title, message, source="Run")
