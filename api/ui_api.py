"""
UIAPI - Wraps DreamStudio main window UI operations.

Provides access to window management, editor visibility, and general UI controls.
"""


class UIAPI:
    """API for UI and window management."""

    def __init__(self, main_window):
        self._main = main_window

    def addNewEditor(self) -> None:
        """Add a new empty editor tab."""
        self._main.ui_build_add_new_editor()

    def openFile(self) -> None:
        """Open the file dialog to open a file."""
        self._main.ui_build_open_file()

    def openDirectory(self) -> None:
        """Open the directory chooser dialog."""
        self._main.open_directory()

    def saveFile(self) -> None:
        """Save the current file."""
        self._main.ui_build_save_file()

    def saveAllFiles(self) -> None:
        """Save all open files."""
        self._main.ui_build_save_all()

    def saveFileAs(self) -> None:
        """Save the current file with a new name."""
        self._main.ui_build_save_as()

    def closeAllEditors(self) -> None:
        """Close all editor tabs."""
        self._main.ui_build_close_all_editors()

    def showWelcome(self) -> None:
        """Show the welcome screen."""
        self._main.ui_build_show_welcome()

    def toggleTerminal(self) -> None:
        """Toggle terminal panel visibility."""
        self._main.toggle_terminal()

    def toggleSystemMonitor(self) -> None:
        """Toggle system monitor panel."""
        self._main.toggle_system_monitor()

    def openToolsPanel(self, tool_name: str) -> None:
        """Open a specific tool in the tools panel."""
        self._main.open_tools_panel(tool_name)

    def flashButton(self, button, color: str = "#4A6FA5", duration: int = 400) -> None:
        """Flash a button with a color animation."""
        self._main.flash_button(button, color, duration)

    def updateEditorVisibility(self) -> None:
        """Update editor stack visibility."""
        self._main.update_editor_visibility()

    def updatePositionStatus(self) -> None:
        """Update the cursor position in the status bar."""
        self._main.update_position_status()

    def getWidth(self) -> int:
        """Get the window width."""
        return self._main.width()

    def getHeight(self) -> int:
        """Get the window height."""
        return self._main.height()

    def resize(self, width: int, height: int) -> None:
        """Resize the main window."""
        self._main.resize(width, height)

    def setWindowTitle(self, title: str) -> None:
        """Set the window title."""
        self._main.setWindowTitle(title)

    def getWindowTitle(self) -> str:
        """Get the window title."""
        return self._main.windowTitle()

    def showMinimized(self) -> None:
        """Minimize the window."""
        self._main.showMinimized()

    def showMaximized(self) -> None:
        """Maximize the window."""
        self._main.showMaximized()

    def showNormal(self) -> None:
        """Restore the window to normal size."""
        self._main.showNormal()

    def close(self) -> None:
        """Close the main window."""
        self._main.close()

    def getWindow(self):
        """Get the raw QMainWindow instance."""
        return self._main

    def addButtonToLeftmostBar(self, text: str = None, image: str = None,
                               tooltip: str = "", callback=None):
        """Add a button to the leftmost sidebar bar.

        Args:
            text: Optional text for the button (usually None for icon-only).
            image: Path to the icon image file.
            tooltip: Optional tooltip text.
            callback: Optional callable to invoke when the button is clicked.

        Returns:
            The created QPushButton, or None if unavailable.
        """
        if not hasattr(self._main, "leftmost_bar"):
            return None
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import QPushButton

        btn = QPushButton() if text is None else QPushButton(text)
        btn.setFixedSize(QSize(40, 40))

        if image:
            btn.setIcon(QIcon(image))
            btn.setIconSize(QSize(30, 30))

        if tooltip:
            btn.setToolTip(tooltip)

        btn.setStyleSheet("""
        QPushButton{
            background-color: transparent;
            border: none;
            color: white;
            border-radius: 10px;
            padding-top:4px;
            padding-left:2px;
            padding-right:2px;
        }
        QPushButton:hover{background-color:#333}
        """)

        if callback:
            btn.clicked.connect(callback)

        layout = self._main.leftmost_bar.layout()
        insert_pos = layout.count() - 1
        layout.insertWidget(insert_pos, btn)
        return btn
