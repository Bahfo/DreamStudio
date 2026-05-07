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
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt, QSize, pyqtSignal

#### Terminal Emulator First GUI Class from PyQt
# from editor.terminal.PromptXShellGUIClass import PromptXShell

TAB_PROBLEMS = 0
TAB_TERMINAL = 1
TAB_DEBUG = 2
TAB_OUTPUT = 3


class TerminalWidget(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, _parent=None):
        super().__init__(_parent)
        self._parent = _parent
        self.setObjectName("terminalWidget")
        self.setWindowTitle("Native Terminal Emulator Structure")

        self.setMinimumHeight(0)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setStyleSheet("""
            QWidget#terminalWidget {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QWidget#terminalWidget QPushButton {
                background-color: transparent;
                border: none;
                padding: 5px;
            }
            QWidget#terminalWidget QPushButton:hover {
                background-color: #333333;
                border-radius: 3px;
            }
            QWidget#terminalWidget QListWidget {
                border: none;
                border-left: 1px solid #333333;
                background-color: #1e1e1e;
            }
            QWidget#terminalWidget QListWidget::item:selected {
                background-color: #37373d;
            }
            QWidget#terminalWidget QPlainTextEdit {
                border: none;
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            """)

        self._setup_ui()

    def sizeHint(self):
        return QSize(900, 200)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def minimumSize(self):
        return QSize(0, 0)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(0)

        # ------------------ CORE WIDGETS ------------------
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setObjectName("terminalContentSplitter")
        self.content_splitter.setChildrenCollapsible(True)
        self.content_splitter.setHandleWidth(1)
        self.content_splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.terminal_display = QStackedWidget()
        self.terminal_display.setObjectName("terminalDisplay")
        self.terminal_display.setMinimumHeight(0)
        self.terminal_display.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        # ------------------ TOOLBAR ------------------
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(4)

        # ------------------ TABS ------------------
        self.problems_tab = QWidget()
        self.prompt_x_shell_terminal = QWidget()
        self.debug_tab = QWidget()
        self.output_tab = QWidget()

        self.tabs = {
            TAB_PROBLEMS: (self.problems_tab, "PROBLEMS"),
            TAB_TERMINAL: (self.prompt_x_shell_terminal, "TERMINAL"),
            TAB_DEBUG: (self.debug_tab, "DEBUG"),
            TAB_OUTPUT: (self.output_tab, "OUTPUT"),
        }

        # Add tab content FIRST
        for i in range(4):
            widget, _ = self.tabs[i]
            self.terminal_display.addWidget(widget)

        # Create buttons
        self.tab_buttons = {}

        for i in range(4):
            widget, label = self.tabs[i]

            btn = QPushButton(label)
            btn.setFont(QFont("inter", 9, QFont.Weight.Bold))
            btn.setCheckable(True)

            btn.clicked.connect(lambda checked, index=i: self._switch_tab(index))

            toolbar_layout.addWidget(btn)
            self.tab_buttons[i] = btn

        # Spacer
        toolbar_layout.addItem(
            QSpacerItem(
                40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )

        # ------------------ ACTION BUTTONS ------------------
        self.btn_new = QPushButton()
        self.btn_new.setFixedSize(26, 26)
        self.btn_new.setIconSize(QSize(17, 17))
        self.btn_new.setIcon(QIcon("assets/system/add.png"))
        self.btn_new.setToolTip("New Terminal")

        self.btn_kill = QPushButton()
        self.btn_kill.setFixedSize(26, 26)
        self.btn_kill.setIconSize(QSize(17, 17))
        self.btn_kill.setIcon(QIcon("assets/system/trash.png"))
        self.btn_kill.setToolTip("Kill Terminal")

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setToolTip("Close Panel")
        self.btn_close.setStyleSheet("font-size: 15px;")
        self.btn_close.clicked.connect(self.close_requested.emit)

        toolbar_layout.addWidget(self.btn_new)
        toolbar_layout.addWidget(self.btn_kill)
        toolbar_layout.addWidget(self.btn_close)

        # ------------------ LAYOUT ORDER ------------------
        main_layout.addLayout(toolbar_layout)

        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #333333;")
        main_layout.addWidget(separator)

        # Add terminal display into splitter
        self.content_splitter.addWidget(self.terminal_display)
        self.content_splitter.setCollapsible(0, True)

        main_layout.addWidget(self.content_splitter, 1)

    def _switch_tab(self, index):
        self.terminal_display.setCurrentIndex(index)

        for i, btn in self.tab_buttons.items():
            if i == index:
                btn.setStyleSheet("color: #007acc; border-bottom: 2px solid #007acc;")
            else:
                btn.setStyleSheet("color: #cccccc; border-bottom: none;")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TerminalWidget()
    window.show()
    sys.exit(app.exec())
