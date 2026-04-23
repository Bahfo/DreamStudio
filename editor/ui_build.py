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
from PyQt6.QtCore import Qt, QSize, QTimer, QEvent
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QFrame,
    QSplitter,
    QPushButton,
    QStackedWidget,
    QHBoxLayout,
)
from PyQt6.QtGui import QIcon, QShortcut, QKeySequence

"""
LOCAL IDE IMPORTS:
"""
from editor.utils.statusBar import StatusBar
from editor.texteditor.minimap import MiniMap
from editor.utils.optionsBar import OptionsMenu
from editor.animations.splash import SplashOverlay
from editor.utils.etherAI import EtherAIMainScreen
from editor.utils.titleBar import DreamStudioTitleBar
from editor.texteditor.editor import DreamTabbedEditor
from editor.utils.fast_tutorial import FastTutorialFrame
from editor.utils.file_explorer import DreamFileTreeWindow

from editor.terminal.terminal_ui import TerminalWidget


class DreamStudio(QMainWindow):
    def __init__(self):
        super().__init__()

        self._frame_has_started = False
        self._frame_has_exited = False
        self.etherAI_frame_visible = False

        self._minimap_bound_editor = None
        self._splitter_initialized = False

        self.setWindowTitle("DreamStudio")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setStyleSheet("background-color: #1E1E1E; font-family: inter, Arial;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.setup_layout()
        self.check_for_OS_compatability()

        # Keybindings and shortcutsof editor tabs management:
        # Find them in keybindings_reference.md

        self.new_tab_shortcut = QShortcut(
            QKeySequence("Ctrl + Alt + T"), self
        )  # Open a new tab
        self.new_tab_shortcut.activated.connect(
            lambda: self.tab_editors.add_new_editor()
        )
        self.new_tab_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)

        self.close_tab_shortcut = QShortcut(
            QKeySequence("Ctrl + Alt + W"), self
        )  # Close current tab
        self.close_tab_shortcut.activated.connect(self.tab_editors.close_current_tab)
        self.close_tab_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)

    def check_for_OS_compatability(self):
        if platform.system() == "Linux":
            pass

    def _widget_Focus(self, frame, color):
        overlay = SplashOverlay(frame, color)
        overlay.show()

    def setup_layout(self):
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title Bar
        self.title_bar = DreamStudioTitleBar(self)
        self.options_menu = OptionsMenu(self)
        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(self.options_menu)

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        main_layout.addLayout(self.body_layout, stretch=1)

        self.leftmost_bar = QFrame()
        self.leftmost_bar.setFixedWidth(50)
        self.leftmost_bar.setStyleSheet("background-color: #25272B; border: none;")

        # Leftmost bar
        self.leftmost_layout = QVBoxLayout(self.leftmost_bar)
        self.leftmost_layout.setContentsMargins(5, 5, 5, 5)
        self.leftmost_layout.setSpacing(10)
        self.leftmost_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

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

        self.body_layout.addWidget(self.leftmost_bar)

        ##### THE HERO SECTION
        self.hero_splitter = QSplitter(Qt.Orientation.Vertical)
        self.hero_splitter.setHandleWidth(1)
        self.hero_splitter.setStyleSheet(
            "QSplitter::handle { background-color: #1a1a1a; }"
        )
        self.body_layout.addWidget(self.hero_splitter)

        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setHandleWidth(1)
        self.workspace_splitter.setStyleSheet(
            "QSplitter::handle { background-color: #1a1a1a; }"
        )

        # Services Sidebar
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setStyleSheet("background-color: #171717; border: none;")
        self.sidebar_frame.setMinimumWidth(150)

        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self.treeview = DreamFileTreeWindow(self.sidebar_frame)
        sidebar_layout.addWidget(self.treeview)

        # Editor, Background screen, and other stacked layout widgets
        self.main_editor_area = QStackedWidget()
        self.tutorial_window = FastTutorialFrame(self)
        self.tab_editors = DreamTabbedEditor(self)

        # Minimap
        self.minimap = MiniMap(self)
        self.minimap.setMinimumWidth(100)
        self.minimap.setMaximumWidth(100)

        self.tab_editors.installEventFilter(self)
        self.main_editor_area.addWidget(self.tutorial_window)
        self.main_editor_area.addWidget(self.tab_editors)

        # Ether AI Main Screen
        self.etherAIScreen = EtherAIMainScreen()
        self.etherAIScreen.setMinimumWidth(0)
        self.etherAIScreen.setMaximumWidth(500)

        self.workspace_splitter.addWidget(self.sidebar_frame)
        self.workspace_splitter.addWidget(self.main_editor_area)
        self.workspace_splitter.addWidget(self.minimap)
        self.workspace_splitter.addWidget(self.etherAIScreen)

        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setStretchFactor(2, 0)
        self.workspace_splitter.setStretchFactor(3, 0)

        self.workspace_splitter.setCollapsible(0, True)
        self.workspace_splitter.setCollapsible(1, True)
        self.workspace_splitter.setCollapsible(2, False)
        self.workspace_splitter.setCollapsible(3, True)

        self.hero_splitter.addWidget(self.workspace_splitter)

        # Terminal, Console, Debugger, and Output Services
        self.terminalWidget = TerminalWidget(self)
        self.hero_splitter.addWidget(self.terminalWidget)

        self.hero_splitter.setOpaqueResize(True)

        self.hero_splitter.setStretchFactor(0, 3)  # Workspace gets main focus
        self.hero_splitter.setStretchFactor(1, 1)  # Terminal
        self.hero_splitter.setCollapsible(1, True)

        self.terminalWidget.setMaximumHeight(16777215)

        self.status_bar = StatusBar(self)
        main_layout.addWidget(self.status_bar)

        self.installEventFilter(self)
        self.sync_minimap_on_tab_switch(self.tab_editors.currentIndex())
        self.tab_editors.currentChanged.connect(self.sync_minimap_on_tab_switch)

    def showEvent(self, event):
        super().showEvent(event)

        if not self._splitter_initialized:
            self._splitter_initialized = True
            QTimer.singleShot(0, self._apply_initial_splitter_sizes)

    def _apply_initial_splitter_sizes(self):
        ws_total = self.workspace_splitter.width()
        if ws_total > 0:
            self.workspace_splitter.setSizes([450, ws_total - 350, 100, 0])

        hero_total = self.hero_splitter.height()
        if hero_total > 50:
            workspace_h = int(hero_total * 0.75)
            terminal_h = hero_total - workspace_h
            self.hero_splitter.setSizes([workspace_h, terminal_h])

    def changeEvent(self, event):
        """Handle window state changes like Maximize."""
        if event.type() == QEvent.Type.WindowStateChange:
            print(event.type())
            QTimer.singleShot(50, self._apply_initial_splitter_sizes)
        super().changeEvent(event)

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
        editor = self.tab_editors.widget(index) if index >= 0 else None

        if self._minimap_bound_editor is not None:
            try:
                self._minimap_bound_editor.textChanged.disconnect(
                    self._update_minimap_from_editor
                )
            except (TypeError, RuntimeError):
                pass
            self._minimap_bound_editor = None

        if editor is None:
            self.minimap.setText("")
            return

        self._minimap_bound_editor = editor
        editor.textChanged.connect(self._update_minimap_from_editor)
        self._update_minimap_from_editor()

    def _update_minimap_from_editor(self):
        editor = self._minimap_bound_editor
        if editor is None:
            self.minimap.setText("")
            return

        self.minimap.setText(editor.text())

    def _state_str(self):
        flags = []
        if self.isMaximized():
            flags.append("Maximized")
        if self.isMinimized():
            flags.append("Minimized")
        if self.isFullScreen():
            flags.append("FullScreen")
        if not flags:
            flags.append("Normal")
        return "|".join(flags)

    def _geo_str(self):
        g = self.geometry()
        return f"{g.x()},{g.y()} {g.width()}x{g.height()}"

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def moveEvent(self, event):
        print(f"[MAIN] moveEvent state={self._state_str()}")
        super().moveEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_T and event.modifiers() == (
                Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
            ):
                self.add_new_editor()
                self.update_editor_visibility()
                return True
        return super().eventFilter(obj, event)

    def update_editor_visibility(self):
        if self.tab_editors.count() == 0:
            self.main_editor_area.setCurrentIndex(0)
            self.minimap.hide()
        else:
            self.main_editor_area.setCurrentIndex(1)
            self.minimap.show()
