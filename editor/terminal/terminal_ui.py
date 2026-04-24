import os
import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QSpacerItem,
    QSizePolicy,
)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt, QSize, pyqtSignal


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
        self.setStyleSheet(
            """
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
            """
        )

        self._setup_ui()

    def sizeHint(self):
        return QSize(900, 200)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def minimumSize(self):
        return QSize(0, 0)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(4)

        self.title_label = QPushButton("PROBLEMS")
        self.title_label.setFont(QFont("inter", 9, QFont.Weight.Bold))
        toolbar_layout.addWidget(self.title_label)

        self.title_label = QPushButton("TERMINAL")
        self.title_label.setFont(QFont("inter", 9, QFont.Weight.Bold))
        toolbar_layout.addWidget(self.title_label)

        self.title_label = QPushButton("DEBUG")
        self.title_label.setFont(QFont("inter", 9, QFont.Weight.Bold))
        toolbar_layout.addWidget(self.title_label)

        self.title_label = QPushButton("OUTPUT")
        self.title_label.setFont(QFont("inter", 9, QFont.Weight.Bold))
        toolbar_layout.addWidget(self.title_label)

        toolbar_layout.addItem(
            QSpacerItem(
                40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )

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

        main_layout.addLayout(toolbar_layout)

        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #333333;")
        main_layout.addWidget(separator)

        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setObjectName("terminalContentSplitter")
        self.content_splitter.setChildrenCollapsible(True)
        self.content_splitter.setHandleWidth(1)
        self.content_splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.terminal_display = QPlainTextEdit()
        self.terminal_display.setObjectName("terminalDisplay")
        self.terminal_display.setReadOnly(True)
        self.terminal_display.setMinimumHeight(0)
        self.terminal_display.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.terminal_display.setPlainText(
            "EXcellent Technologies DreamStudio.\n"
            "Copyright (C) Excellent Technologies. All rights reserved.\n\n"
            f"{os.getcwd()} >>> "
        )
        self.terminal_display.setStyleSheet(
            "font-family: JetBrains Mono; font-size: 15px;"
        )

        self.content_splitter.addWidget(self.terminal_display)
        self.content_splitter.setCollapsible(0, True)

        main_layout.addWidget(self.content_splitter, 1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TerminalWidget()
    window.show()
    sys.exit(app.exec())
