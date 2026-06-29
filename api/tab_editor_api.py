"""
TabEditorAPI - Wraps DreamTabbedEditor functionality.

Provides access to tab management, file opening, and editor lifecycle.
"""

import pathlib
from typing import Optional


class TabEditorAPI:
    """API for managing editor tabs."""

    def __init__(self, main_window):
        self._main = main_window

    def _tabs(self):
        return getattr(self._main, "tab_editors", None)

    def addNewEditor(self, file_name=None, content="", language=None,
                     file_path=None, welcome: bool = False):
        """Open a new editor tab. Returns the created widget."""
        tabs = self._tabs()
        if tabs is None:
            return None
        return tabs.add_new_editor(
            file_name=file_name, content=content, language=language,
            file_path=file_path, welcome=welcome
        )

    def closeEditor(self, index: int) -> None:
        """Close the editor tab at the given index."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.close_editor(index)

    def closeCurrentTab(self) -> None:
        """Close the currently active tab."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.close_tab()

    def closeAllEditors(self) -> None:
        """Close all editor tabs."""
        tabs = self._tabs()
        if tabs is not None:
            self._main.ui_build_close_all_editors()

    def getTabCount(self) -> int:
        """Get the number of open tabs."""
        tabs = self._tabs()
        if tabs is None:
            return 0
        return tabs.count()

    def getCurrentTabIndex(self) -> int:
        """Get the index of the current tab."""
        tabs = self._tabs()
        if tabs is None:
            return -1
        return tabs.currentIndex()

    def setCurrentTabIndex(self, index: int) -> None:
        """Switch to a specific tab by index."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.setCurrentIndex(index)

    def getTabText(self, index: int) -> str:
        """Get the text of a tab at a specific index."""
        tabs = self._tabs()
        if tabs is None:
            return ""
        return tabs.tabText(index)

    def setTabText(self, index: int, text: str) -> None:
        """Set the text of a tab at a specific index."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.setTabText(index, text)

    def openFile(self) -> None:
        """Open a file dialog and load the selected file in a new tab."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.open_file()

    def openFileAtLine(self, file_path: str, line: int) -> None:
        """Open a file and navigate to a specific line."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.open_file_at_line(file_path, line)

    def saveCurrentFile(self) -> None:
        """Save the currently active file."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.save_current_file()

    def saveCurrentFileAs(self) -> None:
        """Save the current file with a new name."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.save_current_file_as()

    def saveAllFiles(self) -> None:
        """Save all open files."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.save_all_files()

    def resolveViewerType(self, file_path: str) -> str:
        """Resolve the viewer type for a file (code, image, pdf, metadata)."""
        tabs = self._tabs()
        if tabs is None:
            return "default"
        return tabs.resolve_viewer_type(file_path)

    def resolveLanguage(self, file_ext: str) -> Optional[str]:
        """Resolve the language from a file extension."""
        tabs = self._tabs()
        if tabs is None:
            return None
        return tabs.set_language(file_ext)

    def getWidget(self, index: int):
        """Get the widget at a specific tab index."""
        tabs = self._tabs()
        if tabs is None:
            return None
        return tabs.widget(index)

    def addCloseInterceptor(self, callback) -> None:
        """Add a callback that intercepts tab close requests."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.add_close_interceptor(callback)

    def removeCloseInterceptor(self, callback) -> None:
        """Remove a close interceptor callback."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.remove_close_interceptor(callback)

    def getOpenedFiles(self) -> dict:
        """Get a dict of currently opened files {path: index}."""
        tabs = self._tabs()
        if tabs is None:
            return {}
        return dict(tabs.opened_files)

    def openNewWorkspace(self, path: str) -> None:
        """Switch to a new workspace directory."""
        tabs = self._tabs()
        if tabs is not None:
            tabs.open_new_workspace(path)
