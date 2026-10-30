"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
A Command-Line Interface for the DreamScript Language.
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from editor.widgets.QTitleBar import TitleBar
from DreamCLI.ui.DayTerminal import TerminalTabController
from DreamCLI.ui.DayDreamTabBar import TerminalTabBar


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

        self.icon_btn.setFixedHeight(30)
        self.icon_btn.setIconSize(QSize(22, 22))
        self.icon_btn.setCursor(Qt.CursorShape.OpenHandCursor)

        self._layout.setStretchFactor(self.menubar, 1)

        self.btn_minimize.setFixedSize(30, 30)
        self.btn_close.setFixedSize(30, 30)

    def install_terminal_tabs(self, tab_bar):
        """
        Install the terminal tab bar into the title bar.
        """

        tab_bar.setFixedHeight(tab_bar.BAR_HEIGHT)
        self.menubar.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        self._layout.setStretchFactor(self.menubar, 0)
        index = self._layout.indexOf(self.btn_minimize)
        self._layout.insertWidget(index, tab_bar, 1)
        self._layout.setStretchFactor(tab_bar, 1)

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

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#151515"))


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
        self.setStyleSheet("border: none; background-color: #1E1E1E;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self._layout = QVBoxLayout(self.central_widget)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.title_bar = DayDreamTitleBar(self, self.TITLE)

        self._layout.addWidget(self.title_bar)
        self.terminal_tab_bar = TerminalTabBar(self.title_bar)
        self.title_bar.install_terminal_tabs(self.terminal_tab_bar)

        self.terminal_stack = QStackedWidget(self.central_widget)
        self.terminal_stack.setFrameShape(QFrame.Shape.NoFrame)

        self.terminal_stack.setLineWidth(0)
        self.terminal_stack.setMidLineWidth(0)

        self.terminal_stack.setContentsMargins(0, 0, 0, 0)

        self.terminal_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #202020;
                border: none;
                margin: 0px;
                padding: 0px;
            }

            QPlainTextEdit {
                background-color: #202020;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)

        self._layout.addWidget(self.terminal_stack, 1)

        self.terminal_manager = TerminalTabController(
            self.terminal_tab_bar, self.terminal_stack, self
        )

        self.terminal_manager.add_terminal("Terminal 1")
        self.title_bar.btn_add.clicked.connect(
            lambda checked=False: self.terminal_manager.add_terminal(
                f"Terminal {self.terminal_tab_bar.count() + 1}"
            )
        )

    def toggle_maximize(self):
        win = self.window()
        if win.isMaximized():
            win.showNormal()
            self.title_bar.btn_maximize.setText("◻")
            return

        self._restore_geometry = win.normalGeometry()
        if not self._restore_geometry.isValid():
            self._restore_geometry = win.geometry()

        win.showMaximized()
        self.title_bar.btn_maximize.setText("❐")


if __name__ == "__main__":
    application = QApplication(sys.argv)
    app = DayDream()
    app.show()
    sys.exit(application.exec())
