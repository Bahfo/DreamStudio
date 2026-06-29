"""
FileExplorerAPI - Wraps DreamFileTreeWindow functionality.

Provides access to file tree navigation, file operations, and directory management.
"""

import os
from typing import Optional


class FileExplorerAPI:
    """API for the file explorer."""

    def __init__(self, main_window):
        self._main = main_window

    def _explorer(self):
        return getattr(self._main, "fileTree", None)

    def getCurrentDirectory(self) -> str:
        """Get the current directory shown in the file explorer."""
        return getattr(self._main, "currentDirectory", "")

    def setDirectory(self, path: str) -> None:
        """Set the root directory for the file explorer."""
        explorer = self._explorer()
        if explorer is not None:
            explorer.set_treeview_directory(path)

    def refresh(self) -> None:
        """Refresh the file tree."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._refresh()

    def collapseAll(self) -> None:
        """Collapse all folders in the file tree."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._collapse_all()

    def expandSelected(self) -> None:
        """Expand the currently selected folder."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._expand_selected()

    def toggleDetails(self) -> None:
        """Toggle the file details header (size, type, date)."""
        explorer = self._explorer()
        if explorer is not None:
            explorer.toggle_details()

    def searchFiles(self, query: str) -> None:
        """Filter the file tree by a search query."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._on_search(query)

    def createNewFile(self) -> None:
        """Create a new file in the current directory."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._add_new_file()

    def createNewFolder(self) -> None:
        """Create a new folder in the current directory."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._add_new_folder()

    def toggleHiddenFiles(self) -> None:
        """Toggle visibility of hidden files."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._toggle_hidden_files()

    def setSortMode(self, mode: int) -> None:
        """Set the sort mode (0=default, 1=type, 2=modified_newest, 3=modified_oldest)."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._set_sort_mode(mode)

    def clearCache(self) -> None:
        """Clear __pycache__, .mypy_cache, etc. from the project."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._clear_cache()

    def copyPath(self, file_path: str) -> None:
        """Copy the absolute path of a file to the clipboard."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._copy_path(file_path)

    def copyRelativePath(self, file_path: str) -> None:
        """Copy the relative path of a file to the clipboard."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._copy_relative_path(file_path)

    def cutFile(self, file_path: str) -> None:
        """Cut a file to the clipboard."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._cut_file(file_path)

    def copyFile(self, file_path: str) -> None:
        """Copy a file to the clipboard."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._copy_file(file_path)

    def pasteFile(self, target_dir: str) -> None:
        """Paste a file from the clipboard into the target directory."""
        explorer = self._explorer()
        if explorer is not None:
            explorer._paste_file(target_dir)

    def deleteFile(self, file_path: str) -> None:
        """Delete a file (with confirmation dialog)."""
        explorer = self._explorer()
        if explorer is not None:
            explorer.confirm_delete(file_path)

    def renameItem(self, file_path: str, new_name: str) -> None:
        """Rename a file or folder."""
        try:
            new_path = os.path.join(os.path.dirname(file_path), new_name)
            os.rename(file_path, new_path)
        except Exception:
            pass

    def getTreeViewRoot(self) -> str:
        """Get the root path currently shown in the file tree."""
        explorer = self._explorer()
        if explorer is None:
            return ""
        return getattr(explorer, "_parent", self._main).currentDirectory
