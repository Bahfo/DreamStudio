"""
ToolsAPI - Wraps ToolsManager functionality.

Provides access to IDE tools (TODO Hunter, Dev Containers, System Monitor, etc).
"""

from typing import Optional


class ToolsAPI:
    """API for IDE tools management."""

    def __init__(self, main_window):
        self._main = main_window

    def _manager(self):
        return getattr(self._main, "tools_manager", None)

    def openTool(self, tool_name: str) -> None:
        """Open a tool by name (e.g., 'TODO', 'Dev Containers', 'System Monitor')."""
        mgr = self._manager()
        if mgr is not None:
            mgr.open_tool(tool_name)

    def closeTool(self, index: int) -> None:
        """Close a tool tab by index."""
        mgr = self._manager()
        if mgr is not None:
            mgr.close_tool(index)

    def closeAllTools(self) -> None:
        """Close all open tools."""
        mgr = self._manager()
        if mgr is not None:
            mgr.close_all_tools()

    def hasTool(self, tool_name: str) -> bool:
        """Check if a specific tool is open."""
        mgr = self._manager()
        if mgr is None:
            return False
        return mgr.has_tool(tool_name)

    def searchTodos(self, directory: str = None) -> list:
        """Search for TODOs in the project."""
        if directory is None:
            directory = self._main.currentDirectory
        from editor.utils.tools.todo_search import TODOSearch
        search = TODOSearch()
        return search._scan_directory(directory)

    def getWidget(self):
        """Get the raw tools manager widget."""
        return self._manager()
