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
from PyQt6.QtCore import Qt, QSize, QTimer, QPoint
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QFrame,
    QSplitter,
    QPushButton,
    QLabel,
)
from PyQt6.QtGui import QIcon


from editor.utils.statusBar import StatusBar
from editor.texteditor.minimap import MiniMap
from editor.utils.optionsBar import OptionsMenu
from editor.animations.splash import SplashOverlay
from editor.utils.titleBar import DreamStudioTitleBar
from editor.widgets.QCustomLabels import CustomTooltip
from editor.utils.file_explorer import DreamFileTreeWindow
from editor.texteditor.editor import CodeEditor, DreamTabbedEditor


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
        self.setStyleSheet("background-color: #1E1E1E; font-family: inter, Arial;")

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

        self.leftmost_layout = QVBoxLayout(self.leftmost_bar)
        self.leftmost_layout.setContentsMargins(5, 5, 5, 5)  # L, T, R, B padding
        self.leftmost_layout.setSpacing(10)
        self.leftmost_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Leftmost Initial Widgets
        self.explorerBtn = self.create_bar_option(
            text=None, image="assets/system/folder.png", image_size=QSize(30, 30)
        )
        self.leftmost_layout.addWidget(self.explorerBtn)

        self.searchBtn = self.create_bar_option(
            text=None, image="assets/system/find.png", image_size=QSize(30, 30)
        )
        self.leftmost_layout.addWidget(self.searchBtn)

        self.gitChangesBtn = self.create_bar_option(
            text=None, image="assets/system/git.png", image_size=QSize(30, 30)
        )
        self.leftmost_layout.addWidget(self.gitChangesBtn)

        self.extensionsBtn = self.create_bar_option(
            text=None, image="assets/system/extensions.png", image_size=QSize(26, 26)
        )
        self.leftmost_layout.addWidget(self.extensionsBtn)

        self.leftmost_layout.addStretch()

        self.infoBtn = self.create_bar_option(
            text=None, image="assets/system/info.png", image_size=QSize(26, 26)
        )
        self.leftmost_layout.addWidget(self.infoBtn)

        self.terminalBtn = self.create_bar_option(
            text=None, image="assets/system/terminal.png", image_size=QSize(26, 26)
        )
        self.leftmost_layout.addWidget(self.terminalBtn)

        self.version_controlBtn = self.create_bar_option(
            text=None,
            image="assets/system/version_control.png",
            image_size=QSize(26, 26),
        )
        self.leftmost_layout.addWidget(self.version_controlBtn)

        # Sidebar
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setStyleSheet("background-color: #171717; border: none;")
        self.sidebar_frame.setMinimumWidth(150)

        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self.treeview = DreamFileTreeWindow(self.sidebar_frame)
        sidebar_layout.addWidget(self.treeview)

        # In your UI Builder __init__
        self.tab_editors = DreamTabbedEditor(self)
        self.minimap = MiniMap(self)

        # Connect the tab switch signal
        self.tab_editors.currentChanged.connect(self.sync_minimap_on_tab_switch)

        # Initial sync for the first tab
        self.sync_minimap_on_tab_switch(self.tab_editors.currentIndex())

        self.minimap.setMinimumWidth(100)
        self.minimap.setMaximumWidth(100)

        self.workspace_splitter.setStretchFactor(0, 0)  # leftmost bar (fixed)
        self.workspace_splitter.setStretchFactor(1, 0)  # sidebar (mostly fixed)
        self.workspace_splitter.setStretchFactor(2, 1)  # editor (takes all extra space)
        self.workspace_splitter.setStretchFactor(3, 0)  # minimap (fixed)

        self.workspace_splitter.addWidget(self.leftmost_bar)
        self.workspace_splitter.addWidget(self.sidebar_frame)
        self.workspace_splitter.addWidget(self.tab_editors)
        self.workspace_splitter.addWidget(self.minimap)

        self.workspace_splitter.setSizes([50, 350, 840, 110])

        main_layout.addWidget(self.workspace_splitter, stretch=1)

        # Status Bar
        self.status_bar = StatusBar(self)
        main_layout.addWidget(self.status_bar)

    def create_bar_option(
        self,
        image,
        image_size=QSize(35, 35),
        text=None,
        btn_size=QSize(40, 40),
        custom_css=None,
        function=None,
    ):
        btn = QPushButton(text) if text else QPushButton()
        btn.setFixedSize(btn_size)
        btn.setIcon(QIcon(image))
        btn.setIconSize(image_size)

        default_css = """
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
        """

        btn.setStyleSheet(custom_css if custom_css else default_css)

        if function:
            btn.clicked.connect(function)

        return btn

    def sync_minimap_on_tab_switch(self, index):
        # 1. Get the editor instance from the tab widget
        editor = self.tab_editors.widget(index)

        if editor:
            # 2. Update the minimap text immediately
            self.minimap.setText(editor.text())

            # 3. Handle live typing updates
            # We try to disconnect to prevent the same function firing 10 times
            # as you switch back and forth.
            try:
                editor.textChanged.disconnect()
            except TypeError:
                # This happens if it was never connected; we can ignore it
                pass

            # Connect the current editor's text change to the minimap
            editor.textChanged.connect(lambda: self.minimap.setText(editor.text()))
