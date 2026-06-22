"""
ToolsManager - Central panel for managing and launching IDE tools.
"""
import logging
from PyQt6.QtWidgets import QStackedWidget, QVBoxLayout, QFrame
from editor.utils.tools.todo_search import TODOSearch
from editor.utils.tools.system_monitor import SystemMonitor

logger = logging.getLogger(__name__)


class ToolsManager(QFrame):
    def __init__(self, master=None):
        super().__init__(master)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumWidth(0)
        self.setMaximumWidth(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        self._tools: dict[str, int] = {}

        self._register_default_tools()

    def _register_default_tools(self):
        self.register_tool("todo", TODOSearch(self))
        self.register_tool("system_monitor", SystemMonitor(self))

    def register_tool(self, name: str, widget) -> None:
        """Register a tool widget that can be opened by name."""
        index = self.stacked_widget.addWidget(widget)
        self._tools[name] = index

    def retheme_tools(self, t) -> None:
        """Propagate theme to all registered tool widgets."""
        for i in range(self.stacked_widget.count()):
            widget = self.stacked_widget.widget(i)
            if hasattr(widget, "retheme"):
                widget.retheme(t)

    def get_tool(self, name: str):
        index = self._tools.get(name)
        if index is not None:
            return self.stacked_widget.widget(index)
        return None

    def _on_click_open(self, tool_name: str) -> None:
        """Switch to the requested tool by name."""
        index = self._tools.get(tool_name)
        if index is not None:
            self.stacked_widget.setCurrentIndex(index)
        else:
            logger.warning("Unknown tool requested: %s", tool_name)
