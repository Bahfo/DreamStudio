import logging

from PyQt6.QtWidgets import QApplication, QMainWindow

from editor.terminal.terminal_ui import (
    TAB_PROMPTX,
    TAB_SYSTEM_SHELL,
    TAB_PROBLEMS,
    TAB_DEBUG,
    TAB_OUTPUT,
)

logger = logging.getLogger(__name__)


def _get_main_window():
    app = QApplication.instance()
    if app is None:
        return None
    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget
    return None


COMMAND_MAP = {
    "open-explorer": lambda win: win.sidebar_frame.setCurrentIndex(0),
    "open-search": lambda win: win.toggle_find_replace(),
    "open-git": lambda win: win.sidebar_frame.setCurrentIndex(2),
    "open-extensions": lambda win: win.sidebar_frame.setCurrentIndex(3),
    "open-terminal": lambda win: win.toggle_terminal(),
    "open-promptx": lambda win: _open_terminal_tab(win, TAB_PROMPTX),
    "open-problems": lambda win: _open_terminal_tab(win, TAB_PROBLEMS),
    "open-debug": lambda win: _open_terminal_tab(win, TAB_DEBUG),
    "open-output": lambda win: _open_terminal_tab(win, TAB_OUTPUT),
    "new-terminal": lambda win: _new_terminal(win),
}


def _open_terminal_tab(win, tab_index):
    if not win.terminalWidget.isVisible():
        win.toggle_terminal()
    win.terminalWidget.switch_tab(tab_index)


def _new_terminal(win):
    if not win.terminalWidget.isVisible():
        win.toggle_terminal()
    win.terminalWidget.switch_tab(TAB_SYSTEM_SHELL)
    win.terminalWidget.system_shell_tab._on_add_session()


def execute_command(given_command):
    win = _get_main_window()
    if win is None:
        logger.warning("No main window found, cannot execute command: %s", given_command)
        return

    handler = COMMAND_MAP.get(given_command)
    if handler is not None:
        handler(win)
    else:
        logger.warning("Unknown command: %s", given_command)
