"""
OptionsBarAPI - Wraps OptionsMenu functionality.

Provides access to the options/toolbar bar.
"""


class OptionsBarAPI:
    """API for the options toolbar."""

    def __init__(self, main_window):
        self._main = main_window

    def _bar(self):
        return getattr(self._main, "options_bar", None)

    def createMenuButton(self, text: str):
        """Create a new menu button."""
        bar = self._bar()
        if bar is None:
            return None
        return bar.create_menu_button(text)
