"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved

EditorContainer: Public wrapper around the tab editor that
exposes a clean interface for toolbar callbacks and the IDE.
"""

import logging
import os
from typing import Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout

from editor.texteditor.tab_editor import DreamTabbedEditor
from editor.texteditor.api import EditorAPI
from editor.texteditor.minimap import MiniMapHostWidget

logger = logging.getLogger(__name__)


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
    """Thin wrapper that owns the DreamTabbedEditor and
    exposes the methods, tabs, and public API that the
    IDE toolbar depends on."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.currentDirectory = os.getcwd()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = DreamTabbedEditor(self)
        layout.addWidget(self._tabs)

        self.methods = _EditorMethods(self)

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
        win = self._main_window()
        if win and hasattr(win, "update_editor_visibility"):
            win.update_editor_visibility()

    def _get_current_editor(self):
        return self.current_editor()

    @property
    def status_bar(self):
        win = self._main_window()
        return getattr(win, "status_bar", None)
