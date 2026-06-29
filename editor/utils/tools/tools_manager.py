"""
ToolsManager - Central panel for managing and launching IDE tools.
"""
import logging
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QTabWidget, QVBoxLayout, QFrame
from editor.utils.tools.todo_search import TODOSearch
from editor.utils.tools.system_monitor import SystemMonitor
from editor.utils.tools.dev_containers import DevContainers
from editor.widgets.QDreamTabEditor import DreamStudioIDETabBar

logger = logging.getLogger(__name__)


class ToolsManager(QFrame):
    all_tabs_closed = pyqtSignal()

    def __init__(self, master=None):
        super().__init__(master)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumWidth(0)
        self.setMaximumWidth(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabBar(DreamStudioIDETabBar(self.tab_widget))
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.South)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.tab_widget)

        self._tool_factories: dict[str, type] = {
            "todo": TODOSearch,
            "system_monitor": SystemMonitor,
            "dev_containers": DevContainers,
        }
        self._open_tabs: dict[str, tuple[int, object]] = {}
        self._theme = None

    def retheme_tools(self, t) -> None:
        """Propagate theme to all open tool widgets."""
        self._theme = t
        if hasattr(self.tab_widget.tabBar(), "retheme"):
            self.tab_widget.tabBar().retheme(t)
        for _, widget in self._open_tabs.values():
            if hasattr(widget, "retheme"):
                widget.retheme(t)

    def get_tool(self, name: str):
        entry = self._open_tabs.get(name)
        if entry is not None:
            return entry[1]
        return None

    def _on_click_open(self, tool_name: str) -> None:
        """Open a tool tab or switch to it if already open."""
        if tool_name in self._open_tabs:
            index, _ = self._open_tabs[tool_name]
            self.tab_widget.setCurrentIndex(index)
            return

        factory = self._tool_factories.get(tool_name)
        if factory is None:
            logger.warning("Unknown tool requested: %s", tool_name)
            return

        widget = factory(self)
        index = self.tab_widget.addTab(widget, tool_name.replace("_", " ").title())
        self._open_tabs[tool_name] = (index, widget)
        self.tab_widget.setCurrentIndex(index)

        if self._theme is not None and hasattr(widget, "retheme"):
            widget.retheme(self._theme)

    def _on_tab_close(self, index: int) -> None:
        """Close and destroy the tool widget at the given tab index."""
        name = None
        for n, (idx, _) in self._open_tabs.items():
            if idx == index:
                name = n
                break

        if name is None:
            return

        widget = self._open_tabs[name][1]
        self.tab_widget.removeTab(index)
        widget.setParent(None)
        widget.deleteLater()
        del self._open_tabs[name]

        self._reindex_tabs()

        if not self._open_tabs:
            self.all_tabs_closed.emit()

    def _reindex_tabs(self) -> None:
        """Update stored indices after a tab is removed."""
        new_open: dict[str, tuple[int, object]] = {}
        for name, (_, widget) in self._open_tabs.items():
            for i in range(self.tab_widget.count()):
                if self.tab_widget.widget(i) is widget:
                    new_open[name] = (i, widget)
                    break
        self._open_tabs = new_open
