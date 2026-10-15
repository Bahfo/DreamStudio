"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

A Command-Line Interface for the DreamScript Language.
This tool comes with the default distribution of DreamStudio, or can be installed
independently alongside DreamScript. The main purpose of DreamScript and this tool
is to automate developer's tasks by providing a very powerful and rich set of
commands and scripts to serve as a secondary terminal and an automation center.
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import sys

# Local Imports
from editor.widgets.QTitleBar import TitleBar
from DreamCLI.ui.DayTerminal import TerminalWidget


class DayDreamTitleBar(TitleBar):
    """
    Customized title bar for the DayDream Console.
    """

    TITLE = "DayDream Console"
    ICON_PATH = "assets/ds_gray.png"

    def __init__(self, parent=None, title=TITLE):
        super().__init__(parent, title, self.ICON_PATH)

        self._drag_position = None

        self.setFixedHeight(40)

        self._layout.setContentsMargins(8, 0, 8, 0)
        self._layout.setSpacing(8)

        # Application title
        self.icon_btn.setFixedHeight(30)
        self.icon_btn.setIconSize(QSize(22, 22))
        self.icon_btn.setCursor(Qt.CursorShape.OpenHandCursor)

        # Menu bar
        self.menubar.setNativeMenuBar(False)
        self.menubar.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        # Give the menu bar enough horizontal space for its menus.
        self._layout.setStretchFactor(self.menubar, 1)

        # Window controls
        self.btn_minimize.setFixedSize(30, 30)
        self.btn_close.setFixedSize(30, 30)

    #####################################################################
    # Window Dragging
    #####################################################################

    def _start_drag(self, event):
        self._drag_position = (
            event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
        )

        self.icon_btn.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _move_window(self, event):
        if (
            self._drag_position is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.window().move(event.globalPosition().toPoint() - self._drag_position)

    def _stop_drag(self):
        self._drag_position = None
        self.icon_btn.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_drag(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_position is not None:
            self._move_window(event)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._stop_drag()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def eventFilter(self, watched, event):
        if watched is self.icon_btn:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._start_drag(event)
                    return True

            elif event.type() == QEvent.Type.MouseMove:
                if self._drag_position is not None:
                    self._move_window(event)
                    return True

            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._stop_drag()
                    return True

        return super().eventFilter(watched, event)


class DayDream(QMainWindow):
    """
    Main and base class of DayDream terminal bundle.
    """

    HEIGHT = 600
    WIDTH = 900
    TITLE = "  DayDream Console"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setContentsMargins(0, 0, 0, 0)
        self.resize(self.WIDTH, self.HEIGHT)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setStyleSheet("border: none; background-color: #0F0F0F;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self._layout = QVBoxLayout(self.central_widget)

        self.title_bar = DayDreamTitleBar(self, self.TITLE)
        self._layout.insertWidget(0, self.title_bar)
        self._layout.addStretch()

        self.terminal = TerminalWidget(self.central_widget)
        self._layout.addWidget(self.terminal, 1)


if __name__ == "__main__":
    application = QApplication(sys.argv)
    app = DayDream()
    app.show()
    sys.exit(application.exec())
