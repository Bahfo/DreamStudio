"""
SourceControlAPI - Wraps SourceControl and GitCommitHistory functionality.

Provides access to source control panel operations.
"""

from typing import Optional


class SourceControlAPI:
    """API for the source control panel."""

    def __init__(self, main_window):
        self._main = main_window

    def _sc(self):
        return getattr(self._main, "source_control", None)

    def refresh(self) -> None:
        """Refresh the source control panel."""
        sc = self._sc()
        if sc is not None:
            sc._refresh()

    def updateWorkspace(self, directory: str) -> None:
        """Update the source control workspace directory."""
        sc = self._sc()
        if sc is not None:
            sc.update_workspace(directory)

    def getChangedFiles(self) -> list:
        """Get the list of changed files displayed in source control."""
        sc = self._sc()
        if sc is None:
            return []
        return sc._get_checked_files() if hasattr(sc, "_get_checked_files") else []

    def doCommit(self) -> None:
        """Execute the commit action."""
        sc = self._sc()
        if sc is not None:
            sc._do_commit()

    def expandAll(self) -> None:
        """Expand all items in the file tree."""
        sc = self._sc()
        if sc is not None:
            sc._expand_all()

    def collapseAll(self) -> None:
        """Collapse all items in the file tree."""
        sc = self._sc()
        if sc is not None:
            sc._collapse_all()

    def toggleCheckAll(self) -> None:
        """Toggle check/uncheck all changed files."""
        sc = self._sc()
        if sc is not None:
            sc._toggle_check_all()

    def showDiff(self) -> None:
        """Show diff for the selected file."""
        sc = self._sc()
        if sc is not None:
            sc._show_diff()

    def getWidget(self):
        """Get the raw source control widget."""
        return self._sc()
