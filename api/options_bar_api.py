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

    def addButton(self, text: str, tooltip: str = "", callback=None):
        """Add a text button to the options bar.

        Args:
            text: The display text for the button.
            tooltip: Optional tooltip text.
            callback: Optional callable to invoke when the button is clicked.

        Returns:
            The created QPushButton, or None if unavailable.
        """
        bar = self._bar()
        if bar is None:
            return None
        from PyQt6.QtCore import QSize
        from PyQt6.QtWidgets import QPushButton

        btn = QPushButton(text)
        btn.setFixedSize(QSize(100, 28))
        btn.setToolTip(tooltip)

        btn_css = """
        QPushButton{
            background-color: #34373C;
            font-size: 12px;
            border: none;
            color: white;
            border-radius: 0px;
            padding-left: 5px;
            padding-right: 10px;
        }
        QPushButton:hover{background-color: #333}
        """
        btn.setStyleSheet(btn_css)
        btn.setProperty("_custom_text_btn", True)

        if callback:
            btn.clicked.connect(callback)

        layout = bar.layout()
        layout.addWidget(btn)
        return btn

    def addSeparator(self):
        """Add a visual separator to the options bar.

        Returns:
            The created VSeparator, or None if unavailable.
        """
        bar = self._bar()
        if bar is None:
            return None
        from PyQt6.QtCore import Qt
        from editor.utils.optionsBar import VSeparator

        sep = VSeparator()
        layout = bar.layout()
        layout.addWidget(sep, alignment=Qt.AlignmentFlag.AlignVCenter)
        return sep
