from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import pyqtSignal, QSize
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PyQt6.QtGui import QColor

# Local Imports
from editor.widgets.QDreamTabEditor import DreamStudioIDETabBar


class UtilityTabBar(DreamStudioIDETabBar):
    """
    Inherits cleanly from DreamStudioIDETabBar.
    Overrides structural data lookups to point to the QStackedWidget.
    """

    def __init__(self, _parent=None):
        super().__init__(_parent)
        self.setExpanding(False)

    def tabSizeHint(self, index):
        text = self.tabText(index)
        fm = self.fontMetrics()
        w = fm.horizontalAdvance(text) + 40
        return QSize(w, 24)

    def set_theme(
        self,
        selected_bg: str,
        hover_bg: str,
        inactive_bg: str,
        text_selected: str,
        text_inactive: str,
        border_color: str = "#CCCEDB",
    ) -> None:
        """
        Dynamically re-theme color tokens at runtime.
        Defined locally to guarantee functionality even if the base class lacks it.
        """
        self.selected_bg = QColor(selected_bg)
        self.hover_bg = QColor(hover_bg)
        self.inactive_bg = QColor(inactive_bg)
        self.border_color = QColor(border_color)
        self.hover_border_color = QColor(hover_bg)
        self.inactive_border_color = QColor(inactive_bg)
        self._text_selected = QColor(text_selected)
        self._text_inactive = QColor(text_inactive)
        self.update()

    def rebuild_dirty_indices(self) -> None:
        self._dirty_indices.clear()
        if not self._parent or not hasattr(self._parent, "_stack"):
            return
        stack = self._parent._stack
        for i in range(stack.count()):
            w = stack.widget(i)
            if w is not None and hasattr(w, "is_dirty"):
                try:
                    if w.is_dirty():
                        self._dirty_indices.add(i)
                except RuntimeError:
                    pass

    def rebuild_readonly_indices(self) -> None:
        self._readonly_indices.clear()
        if not self._parent or not hasattr(self._parent, "_stack"):
            return
        stack = self._parent._stack
        for i in range(stack.count()):
            w = stack.widget(i)
            if w is not None and hasattr(w, "isReadOnly"):
                try:
                    if w.isReadOnly():
                        self._readonly_indices.add(i)
                except RuntimeError:
                    pass


class UtilityTabManager(QWidget):
    """
    Tabbed side-panel layout with tabs rendered safely underneath the panel
    contents.
    """

    panel_changed = pyqtSignal(str)
    panel_close_requested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("UtilityTabManager")
        self._panel_ids: list[str] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._stack = QStackedWidget(self)
        self._stack.setObjectName("UtilityStack")
        self._layout.addWidget(self._stack, 1)

        self._tab_bar = UtilityTabBar(self)
        self._tab_bar.setObjectName("UtilityTabBar")
        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        self._layout.addWidget(self._tab_bar)

    def set_theme(self, bg: str, fg: str, sel: str = "") -> None:
        pass

    def add_panel(self, panel_id: str, title: str, widget: QWidget) -> None:
        if panel_id in self._panel_ids:
            return
        self._panel_ids.append(panel_id)
        idx = self._tab_bar.addTab(title)
        self._stack.addWidget(widget)

        if hasattr(widget, "close_requested"):
            widget.close_requested.connect(
                lambda pid=panel_id: self.panel_close_requested.emit(pid)
            )

    def remove_panel(self, panel_id: str) -> None:
        if panel_id not in self._panel_ids:
            return
        idx = self._panel_ids.index(panel_id)
        self._panel_ids.pop(idx)
        self._tab_bar.removeTab(idx)
        w = self._stack.widget(idx)
        if w is not None:
            self._stack.removeWidget(w)
            w.deleteLater()

    def set_current_panel(self, panel_id: str) -> None:
        if panel_id not in self._panel_ids:
            return
        idx = self._panel_ids.index(panel_id)
        self._tab_bar.setCurrentIndex(idx)

    def current_panel_id(self) -> Optional[str]:
        idx = self._tab_bar.currentIndex()
        if 0 <= idx < len(self._panel_ids):
            return self._panel_ids[idx]
        return None

    def _on_tab_changed(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        if 0 <= index < len(self._panel_ids):
            self.panel_changed.emit(self._panel_ids[index])

    def _on_tab_close_requested(self, index: int) -> None:
        if 0 <= index < len(self._panel_ids):
            self.panel_close_requested.emit(self._panel_ids[index])
