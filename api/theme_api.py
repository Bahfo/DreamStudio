"""
ThemeAPI - Wraps ThemeManager functionality.

Provides access to UI theme colors and switching.
"""

from typing import Optional


class ThemeAPI:
    """API for managing UI themes."""

    def __init__(self, main_window):
        self._main = main_window

    def _manager(self):
        return getattr(self._main, "theme_manager", None)

    def getCurrentTheme(self) -> str:
        """Get the current UI theme name."""
        mgr = self._manager()
        if mgr is None:
            return ""
        return mgr.name

    def switchTo(self, name: str) -> None:
        """Switch to a named UI theme."""
        mgr = self._manager()
        if mgr is not None:
            mgr.switch_to(name)

    def toggle(self) -> str:
        """Toggle between dark and light themes. Returns the new theme name."""
        mgr = self._manager()
        if mgr is None:
            return ""
        return mgr.toggle()

    def getColor(self, key: str, fallback: str = "#000000") -> str:
        """Get a color value from the current theme by key."""
        mgr = self._manager()
        if mgr is None:
            return fallback
        return mgr.color(key, fallback)


class SyntaxThemeAPI:
    """API for managing syntax highlighting themes."""

    def __init__(self, main_window):
        self._main = main_window

    def _manager(self):
        return getattr(self._main, "syntax_theme_manager", None)

    def getCurrentTheme(self) -> str:
        """Get the current syntax theme name."""
        mgr = self._manager()
        if mgr is None:
            return ""
        return mgr.name

    def switchTo(self, name: str) -> None:
        """Switch to a named syntax theme."""
        mgr = self._manager()
        if mgr is not None:
            mgr.switch_to(name)

    def toggle(self) -> str:
        """Toggle between dark and light syntax themes."""
        mgr = self._manager()
        if mgr is None:
            return ""
        return mgr.toggle()

    def getColor(self, key: str, fallback: str = "#000000") -> str:
        """Get a color value from the current syntax theme by key."""
        mgr = self._manager()
        if mgr is None:
            return fallback
        return mgr.color(key, fallback)
