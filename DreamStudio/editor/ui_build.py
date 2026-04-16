"""
DreamStudio: Application Integrated Development Environment.
'The interpreted programming languages master builder'.

(C) COPYRIGHT 2026 The DreamStudio Project Contributors.
Developed and Maintained Mainly by Excellent Technologies.
"""

# Main Imports
import os
import sys
import json
import platform
import subprocess

# GUI Imports
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QFrame,
    QSplitter,
    QPlainTextEdit,
    QLabel,
)

from editor.utils.statusBar import StatusBar
from editor.utils.optionsBar import OptionsMenu
from editor.texteditor.editor import CodeEditor
from editor.animations.splash import SplashOverlay
from editor.utils.titleBar import DreamStudioTitleBar


class DreamStudio(QMainWindow):
    def __init__(self):
        super().__init__()

        #################################
        # Global Variables
        #################################
        self._frame_has_started = False
        self._frame_has_exited = False

        self.setWindowTitle("DreamStudio")
        self.resize(1000, 800)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background-color: #004073; font-family: inter, Arial;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.setup_layout()

    def check_for_OS_compatability(self):
        """
        Check if the Operating System compatability options.
        """
        if platform.system() == "Linux":
            # Compatability Features for Linux
            pass

    def _widget_Focus(self, frame, color):
        """
        Generates Highlight when a leftsidebar frame is loaded, which sets
        up a small animation for the window after formal initialization to
        call the user's attention.
        """
        overlay = SplashOverlay(frame, color)
        overlay.show()

    def setup_layout(self):
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Elements
        self.title_bar = DreamStudioTitleBar(self)
        self.options_menu = OptionsMenu(self)
        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(self.options_menu)

        # WORKSPACE SPLITTER (Horizontal)
        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setHandleWidth(1)
        self.workspace_splitter.setStyleSheet(
            "QSplitter::handle { background-color: #1a1a1a; }"
        )

        # Leftmost Bar
        self.leftmost_bar = QFrame()
        self.leftmost_bar.setFixedWidth(50)
        self.leftmost_bar.setStyleSheet("background-color: #25272B; border: none;")

        # Sidebar Placeholder (Explorer/Project Tree area) ---
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setStyleSheet("background-color: #111111; border: none;")
        self.sidebar_frame.setMinimumWidth(150)

        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_label = QLabel("PROJECT EXPLORER")
        sidebar_label.setStyleSheet(
            "color: #858585; font-weight: bold; font-size: 11px;"
        )
        sidebar_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter
        )
        sidebar_layout.addWidget(sidebar_label)
        sidebar_layout.addStretch()

        # Main Editor Placeholder
        self.editor_widget = CodeEditor(self)

        self.workspace_splitter.addWidget(self.leftmost_bar)
        self.workspace_splitter.addWidget(self.sidebar_frame)
        self.workspace_splitter.addWidget(self.editor_widget)

        self.workspace_splitter.setSizes([50, 350, 950])

        main_layout.addWidget(self.workspace_splitter, stretch=1)

        # Status Bar
        self.status_bar = StatusBar(self)
        main_layout.addWidget(self.status_bar)
