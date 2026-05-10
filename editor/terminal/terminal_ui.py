import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QStackedWidget,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import pyqtSignal

TAB_PROBLEMS = 0
TAB_TERMINAL = 1
TAB_PROMPTX = 2
TAB_DEBUG = 3
TAB_OUTPUT = 4


class TerminalPanel(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("terminalPanel")
        self.setWindowTitle("Terminal Panel")

        self.setStyleSheet("""
            QWidget#terminalPanel {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-radius: 3px;
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(0)

        # ---------------- STACK ----------------
        self.stack = QStackedWidget()

        self.problems_tab = QWidget()
        self.terminal_tab = QWidget()
        self.promptXShell_tab = QWidget()
        self.debug_tab = QWidget()
        self.output_tab = QWidget()

        self.tabs = {
            TAB_PROBLEMS: (self.problems_tab, "PROBLEMS"),
            TAB_TERMINAL: (self.terminal_tab, "TERMINAL"),
            TAB_PROMPTX: (self.promptXShell_tab, "PROMPTX"),
            TAB_DEBUG: (self.debug_tab, "DEBUG"),
            TAB_OUTPUT: (self.output_tab, "OUTPUT"),
        }

        for i in range(5):
            widget, _ = self.tabs[i]
            self.stack.addWidget(widget)

        # ---------------- TOOLBAR ----------------
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 5, 10, 5)

        self.buttons = {}

        for i in range(5):
            _, label = self.tabs[i]

            btn = QPushButton(label)
            btn.setFont(QFont("Inter", 9, QFont.Weight.Bold))
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, idx=i: self.switch_tab(idx))

            toolbar.addWidget(btn)
            self.buttons[i] = btn

        toolbar.addItem(
            QSpacerItem(
                40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.clicked.connect(self.close_requested.emit)

        toolbar.addWidget(self.btn_close)

        # ---------------- LAYOUT ----------------
        main_layout.addLayout(toolbar)
        main_layout.addWidget(self.stack)

        self.switch_tab(TAB_TERMINAL)

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)

        for i, btn in self.buttons.items():
            if i == index:
                btn.setStyleSheet("color: #007acc; border-bottom: 2px solid #007acc;")
                btn.setFixedWidth(90)
            else:
                btn.setStyleSheet("color: #cccccc; border-bottom: none;")
                btn.setFixedWidth(90)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TerminalPanel()
    w.show()
    sys.exit(app.exec())
