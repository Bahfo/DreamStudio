"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Explorer options menu providing sort, hidden-files toggle, and path-copy
actions for the Solution Explorer status bar.
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup, QFont
from PyQt6.QtWidgets import QApplication, QMenu, QPushButton, QWidget

if TYPE_CHECKING:
    from editor.utils.explorer.proxy import ExplorerFilterProxy


class SortMode(IntEnum):
    """Enumeration of supported file-system sorting strategies."""

    EXTENSION = 0
    ALPHA_ASC = 1
    ALPHA_DESC = 2
    MODIFIED_NEWEST = 3
    MODIFIED_OLDEST = 4


class ExplorerOptionsMenu(QMenu):
    """Context-style popup menu anchored to the status-bar ``...`` button.

    Provides three groups of actions:
    1. **Sort by** -- file-ordering strategy applied to the proxy model.
    2. **Show Hidden Files** -- toggle visibility of dot-prefixed / OS-hidden
       entries through the proxy model.
    3. **Copy Solution Path** -- copies the current workspace root path to the
       system clipboard.
    """

    def __init__(
        self,
        proxy_model: ExplorerFilterProxy,
        workspace_root_fn,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._proxy = proxy_model
        self._workspace_root_fn = workspace_root_fn
        self._current_sort = SortMode.ALPHA_ASC

        self._build_sort_submenu()
        self.addSeparator()
        self._build_show_hidden_action()
        self.addSeparator()
        self._build_copy_path_action()

    def _build_sort_submenu(self) -> None:
        sort_menu = QMenu("Sort by", self)
        sort_menu.setStyleSheet(self.styleSheet())

        self._sort_group = QActionGroup(self)
        self._sort_group.setExclusive(True)

        entries: list[tuple[str, SortMode]] = [
            ("Extension", SortMode.EXTENSION),
            ("Alphabetical Order (A\u2011Z)", SortMode.ALPHA_ASC),
            ("Alphabetical Order (Z\u2011A)", SortMode.ALPHA_DESC),
            ("Last Modified", SortMode.MODIFIED_NEWEST),
            ("Oldest Modified", SortMode.MODIFIED_OLDEST),
        ]

        self._sort_actions: dict[SortMode, QAction] = {}
        for label, mode in entries:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(mode == self._current_sort)
            action.triggered.connect(lambda checked, m=mode: self._on_sort_changed(m))
            self._sort_group.addAction(action)
            sort_menu.addAction(action)
            self._sort_actions[mode] = action

        self.addMenu(sort_menu)

    def _build_show_hidden_action(self) -> None:
        self._show_hidden_action = QAction("Show Hidden Files", self)
        self._show_hidden_action.setCheckable(True)
        self._show_hidden_action.setChecked(self._proxy.show_hidden())
        self._show_hidden_action.triggered.connect(self._on_toggle_hidden)
        self.addAction(self._show_hidden_action)

    def _build_copy_path_action(self) -> None:
        action = QAction("Copy Solution Path", self)
        action.triggered.connect(self._on_copy_path)
        self.addAction(action)

    def _on_sort_changed(self, mode: SortMode) -> None:
        self._current_sort = mode
        self._proxy.set_sort_mode(mode)

    def _on_toggle_hidden(self) -> None:
        visible = self._show_hidden_action.isChecked()
        self._proxy.set_show_hidden(visible)

    def _on_copy_path(self) -> None:
        path = self._workspace_root_fn()
        clipboard = QApplication.clipboard()
        if clipboard is not None and path:
            clipboard.setText(path)


def create_options_button(
    menu: ExplorerOptionsMenu,
    parent: QWidget | None = None,
) -> QPushButton:
    """Factory that builds the ``...`` button wired to *menu*.

    Returns a flat, fixed-size ``QPushButton`` whose ``clicked`` signal
    opens *menu* directly below the button.
    """
    btn = QPushButton("\u2026", parent)
    btn.setObjectName("ExplorerOptionsButton")
    btn.setFixedSize(28, 28)
    btn.setFont(QFont(btn.font().family(), 14))
    btn.setToolTip("Explorer Options")

    def _open_menu() -> None:
        bottom_left = btn.rect().bottomLeft()
        global_pos = btn.mapToGlobal(bottom_left)
        menu.exec(global_pos)

    btn.clicked.connect(_open_menu)
    return btn
