"""
DreamStudio: Application Integrated Development Environment.

DreamStudio: Quiet Valley Edition: Version 1.0.1

(C) COPYRIGHT - 2026 Excellent Technologies Cooperation - All Rights Reserved
Developed and Maintained Mainly by DreamStudio Maintainers and Contributors, and
Supervised by Excellent Technologies Co.
"""

# TODO:
# Texteditor open, save, search, find, replace, cut, copy, paste, etc...
# Texteditor highlight
# Textedtior better autocompletion
# Treeview search, open, seek, new, delete, cut, copy, paste
# Implement the four options in welcome screen: new file, open file, etc...

# ONCE DOING THESE ABOVE WE CAN THINK OF OTHER STUFF LATER

# Main Imports
import os
import sys
import json
import pathlib
import platform
import subprocess

# GUI Imports
from PyQt6.QtCore import Qt, QSize, QEvent, QDir
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QFrame,
    QSplitter,
    QPushButton,
    QStackedWidget,
    QHBoxLayout,
    QFileDialog,
)
from PyQt6.QtGui import QIcon, QShortcut, QKeySequence

# Local IDE Imports
from editor.utils.statusBar import StatusBar
from editor.texteditor.minimap import MiniMap
from editor.utils.optionsBar import OptionsMenu
from editor.animations.splash import SplashOverlay
from editor.utils.etherAI import EtherAIMainScreen
from editor.utils.titleBar import DreamStudioTitleBar
from editor.terminal.terminal_ui import TerminalWidget
from editor.texteditor.editor import DreamTabbedEditor
from editor.utils.fast_tutorial import FastTutorialFrame
from editor.utils.file_explorer import DreamFileTreeWindow


class DreamStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1300, 750)
        self._frame_has_started = False
        self._frame_has_exited = False
        self.etherAI_frame_visible = False
        self._minimap_bound_editor = None
        self._splitter_initialized = False
        self.currentDirectory = QDir.currentPath()

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
        self.close_tab_shortcut.activated.connect(self.tab_editors.close_tab)
        self.close_tab_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)

        self.open_file_shortcut = QShortcut(QKeySequence("Ctrl + O"), self)  # Open File
        self.open_file_shortcut.activated.connect(self.ui_build_open_file)
        self.open_file_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)

        self.open_directory_shortcut = QShortcut(
            QKeySequence("Ctrl + Alt + O"), self
        )  # Open Directory in Treeview
        self.open_directory_shortcut.activated.connect(self.open_directory)
        self.open_directory_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)

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
        self.terminalBtn.clicked.connect(self.toggle_terminal)
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
        self.hero_splitter.setHandleWidth(4)
        self.hero_splitter.setOpaqueResize(True)
        self.hero_splitter.setStyleSheet(
            "QSplitter::handle { background-color: #2a2a2a; }"
            "QSplitter::handle:pressed { background-color: #3a7bd5; }"
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

        self.treeview = DreamFileTreeWindow(self)
        sidebar_layout.addWidget(self.treeview)
        self.treeview.tree.doubleClicked.connect(
            lambda idx: self.open_file_from_treeview(idx)
        )

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
        self.etherAIScreen = QFrame()
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

        self.workspace_splitter.setSizes(
            [450, self.workspace_splitter.width() - 450, 100, 0]
        )

        self.hero_splitter.addWidget(self.workspace_splitter)

        # Terminal, Console, Debugger, and Output Services
        self.terminalWidget = TerminalWidget(self)
        self.hero_splitter.addWidget(self.terminalWidget)
        self.hero_splitter.setOpaqueResize(True)
        self.terminalWidget.close_requested.connect(self.toggle_terminal)

        self.hero_splitter.setCollapsible(1, True)
        self.hero_splitter.setSizes([800, 0])

        self.terminal_collapsed = True

        self.status_bar = StatusBar(self)
        main_layout.addWidget(self.status_bar)

        self.installEventFilter(self)
        self.sync_minimap_on_tab_switch(self.tab_editors.currentIndex())
        self.tab_editors.currentChanged.connect(self.sync_minimap_on_tab_switch)
        self.title_bar.setStyleSheet("background-color: #00438A;")

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
            except (TypeError, RuntimeError, AttributeError):
                pass
            self._minimap_bound_editor = None

        if editor is None:
            self.minimap.setText("")
            return

        if not hasattr(editor, "textChanged"):
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
                self.tab_editors.add_new_editor()
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

    def toggle_terminal(self):
        if self.hero_splitter.sizes()[1] > 1:
            self.terminal_collapsed = False
        hero_total = self.hero_splitter.height()

        if self.terminal_collapsed:
            self.hero_splitter.setSizes([800, 400])
            self.terminal_collapsed = False
        else:
            workspace_h = hero_total
            self.hero_splitter.setSizes([workspace_h, 0])
            self.terminal_collapsed = True

    def ui_build_add_new_editor(self):
        """A higher heirarchy call for adding a new editor tab instead
        of implementing PyQt signals."""
        self.tab_editors.add_new_editor()

    def ui_build_open_file(self):
        """A higher heirarchy call for opening an existing file instead
        of implementing PyQt signals."""
        self.tab_editors.open_file()

    def open_directory(self):
        """
        Opens a directory based on QFileDialog and updates the treeview
        class, implemented here to reduce variables caching and PyQt
        signals.
        """
        path = QFileDialog.getExistingDirectory(
            parent=None,
            caption="Select Directory",
            directory="",
            options=QFileDialog.Option.ShowDirsOnly,
        )
        self.tab_editors.open_new_workspace(path)
        print(self.currentDirectory)
        self.treeview.set_treeview_directory(path)

    def open_file_from_treeview(self, proxy_index):
        """
        Opens a file from the treeview if double clicked.
        Supports all file types via central editor routing.
        """

        if not proxy_index.isValid():
            return

        source_index = self.treeview.proxy_model.mapToSource(proxy_index)
        file_path = self.treeview.model.filePath(source_index)
        file_extn = pathlib.Path(file_path).suffix

        if not os.path.isfile(file_path):
            return

        try:
            _editor = self.tab_editors.add_new_editor(
                file_name=pathlib.Path(file_path).name,
                file_path=file_path,
                language=self.tab_editors.set_language(file_extn),
            )
        except Exception as e:
            print("Open file failed:", e)
            return
