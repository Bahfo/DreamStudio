"""
SearchAPI - Wraps FindReplaceWidget and GlobalFileSearchEngine.

Provides access to find/replace functionality.
"""


class SearchAPI:
    """API for find and replace operations."""

    def __init__(self, main_window):
        self._main = main_window

    def _finder(self):
        return getattr(self._main, "find_replace", None)

    def toggleFindReplace(self) -> None:
        """Toggle the find/replace panel."""
        self._main.toggle_find_replace()

    def openPanel(self) -> None:
        """Open the find/replace panel."""
        finder = self._finder()
        if finder is not None:
            finder.open_panel()

    def closePanel(self) -> None:
        """Close the find/replace panel."""
        finder = self._finder()
        if finder is not None:
            finder.close_panel()

    def replaceNext(self) -> None:
        """Replace the next match."""
        finder = self._finder()
        if finder is not None:
            finder.replace_next()

    def replaceAll(self) -> None:
        """Replace all matches."""
        finder = self._finder()
        if finder is not None:
            finder.replace_all()

    def getMatchCount(self) -> int:
        """Get the number of matches found."""
        finder = self._finder()
        if finder is None:
            return 0
        return len(getattr(finder, "_matches", []))

    def getCurrentMatchIndex(self) -> int:
        """Get the index of the current match."""
        finder = self._finder()
        if finder is None:
            return -1
        return getattr(finder, "_current_match", -1)
