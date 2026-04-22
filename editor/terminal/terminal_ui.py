import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QSpacerItem,
    QSizePolicy,
)
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QPalette
from PyQt6.QtCore import Qt


class TerminalWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Native Terminal Emulator Structure")
        self.resize(800, 300)

        # Apply a basic dark theme to mimic a terminal environment
        self.setStyleSheet(
            """
            QWidget {
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
            QListWidget {
                border: none;
                border-left: 1px solid #333333;
                background-color: #1e1e1e;
            }
            QListWidget::item:selected {
                background-color: #37373d;
            }
            QPlainTextEdit {
                border: none;
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
        """
        )

        self._setup_ui()

    def _setup_ui(self):
        # 1. Main Vertical Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 2. Top Toolbar (VSCode style header)
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(10, 5, 10, 5)

        # Terminal Title/Tabs
        self.title_label = QLabel("TERMINAL")
        self.title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        toolbar_layout.addWidget(self.title_label)

        # Spacer to push buttons to the right
        spacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        toolbar_layout.addItem(spacer)

        # Toolbar Actions
        self.btn_new = QPushButton("+")
        self.btn_new.setToolTip("New Terminal")
        self.btn_split = QPushButton("◫")
        self.btn_split.setToolTip("Split Terminal")
        self.btn_kill = QPushButton("🗑")
        self.btn_kill.setToolTip("Kill Terminal")
        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("Close Panel")

        toolbar_layout.addWidget(self.btn_new)
        toolbar_layout.addWidget(self.btn_split)
        toolbar_layout.addWidget(self.btn_kill)
        toolbar_layout.addWidget(self.btn_close)

        main_layout.addLayout(toolbar_layout)

        # Add a subtle separator line
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #333333;")
        main_layout.addWidget(separator)

        # 3. Content Area (Splitter for Terminal View and Side Panel)
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Main Terminal View (The actual emulator screen)
        self.terminal_display = QPlainTextEdit()
        self.terminal_display.setReadOnly(
            True
        )  # In a real app, you'd handle input dynamically
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.terminal_display.setFont(font)

        # Mocking standard terminal output
        self.terminal_display.setPlainText(
            "Windows PowerShell\n"
            "Copyright (C) Microsoft Corporation. All rights reserved.\n\n"
            "PS C:\\Users\\Developer\\Project> "
        )

        # Side Panel for Terminal Sessions (VSCode right sidebar style)
        self.session_list = QListWidget()
        self.session_list.setFixedWidth(150)
        self.session_list.addItem("1: pwsh")
        self.session_list.addItem("2: bash")
        self.session_list.addItem("3: node")
        self.session_list.setCurrentRow(0)

        # Add widgets to splitter
        self.content_splitter.addWidget(self.terminal_display)
        self.content_splitter.addWidget(self.session_list)

        # Set splitter sizes to give the terminal display more room
        self.content_splitter.setSizes([650, 150])

        main_layout.addWidget(self.content_splitter)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TerminalWidget()
    window.show()
    sys.exit(app.exec())
