"""
DreamStudio: Application Integrated Development Environment.

DreamStudio: Quiet Valley Edition: Version 1.0.1

(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved
Developed and Maintained Mainly by DreamStudio Maintainers and Contributors, and
Supervised by EXcellent TechStacks Co.
"""

# TODO:
# Texteditor open, save, search, find, replace, cut, copy, paste, etc...
# Texteditor highlight
# Textedtior better autocompletion
# Treeview search, open, seek, new, delete, cut, copy, paste
# Implement the four options in welcome screen: new file, open file, etc...

# ONCE DOING THESE ABOVE WE CAN THINK OF OTHER STUFF LATER

# Main Imports
import logging
import os
import pathlib

# Third-Party Imports (GUI)
from PyQt6.QtCore import QDir, QEvent, QPoint, QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# Local Application Imports - Backend
from backend.dirty_tracker import DirtyTracker
from editor.lsp.jedi_worker import JediWorker

# Local Application Imports - UI Components
from editor.animations.splash import SplashOverlay
from editor.terminal.terminal_ui import TerminalPanel
from editor.texteditor.minimap import MiniMap
from editor.texteditor.tab_editor import (
    CodeEditor,
    DreamTabbedEditor,
    FastTutorialFrame,
    BackgroundHintsFrame,
)
from editor.utils.find_replace import FindReplaceWidget, GlobalFileSearchEngine
from editor.utils.file_explorer import DreamFileTreeWindow
from editor.utils.titleBar import DreamStudioTitleBar
from editor.utils.source_control import SourceControl
from editor.utils.theme_manager import ThemeManager
from editor.utils.marketplace import ExtensionsTab
from editor.utils.optionsBar import OptionsMenu
from editor.utils.statusBar import StatusBar

logger = logging.getLogger(__name__)


class DreamStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1300, 750)
        self._frame_has_started = False
        self._frame_has_exited = False
        self.etherAI_frame_visible = False
        self._splitter_initialized = False
        self.terminal_collapsed = True
        self.currentDirectory = QDir.currentPath()
        self.setWindowIcon(QIcon("assets/logos/dreamStudio_icon.png"))

        self.setWindowTitle("DreamStudio")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setStyleSheet("background-color: #1E1E1E; font-family: inter, Arial;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Jedi background worker
        self._jedi_worker = JediWorker(self)
        self._jedi_worker.results_ready.connect(self._on_jedi_results)
        self._jedi_worker.error_occurred.connect(self._on_jedi_error)
        self._pending_jedi_requests = {}
        self._jedi_request_counter = 0
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        venv_path = os.path.join(project_root, "venv", "bin", "python3")
        if not os.path.isfile(venv_path):
            venv_path = os.path.join(project_root, "venv", "bin", "python")
        if not os.path.isfile(venv_path):
            venv_path = None
        self._jedi_worker.set_virtual_environment(venv_path)

        self.theme_manager = ThemeManager(self)
        self.theme_manager.theme_changed.connect(self._on_theme_changed)

        self.setup_layout()

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

        self.find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.find_shortcut.activated.connect(self.toggle_find_replace)
        self.find_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)

        self.replace_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        self.replace_shortcut.activated.connect(self.toggle_find_replace)
        self.replace_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)

    def _on_theme_changed(self, theme_name: str):
        t = self.theme_manager
        tip_css = (
            f"QToolTip{{color: {t.color('tooltip.text')}; font-family: inter;"
            f" padding: 6px 5px; font-size: 12px;"
            f" background-color: {t.color('tooltip.background')};"
            f" border: 1px solid {t.color('tooltip.border')};}}"
        )

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(
                f"QToolTip{{background-color: {t.color('tooltip.background')};"
                f" color: {t.color('tooltip.text')};"
                f" border: 1px solid {t.color('tooltip.border')};"
                f" padding: 4px 8px;"
                f' font-family: "JetBrains Mono", monospace;'
                f" font-size: 11px;}}"
            )

        self.setStyleSheet(
            f"background-color: {t.color('window.background')};"
            f" color: {t.color('window.text')};"
            f" font-family: inter, Arial;" + tip_css
        )

        self.leftmost_bar.setStyleSheet(
            f"background: {t.color('leftmost.background')}; border: none;"
        )

        self.sidebar_frame.setStyleSheet(
            f"background-color: {t.color('sidebar.background')}; border: none;"
        )

        self.hero_splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {t.color('splitter.handle')}; }}"
            f"QSplitter::handle:pressed {{ background-color: {t.color('splitter.handle_pressed')}; }}"
        )
        self.workspace_splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {t.color('workspace_splitter')}; }}"
        )

        self.background_window.retheme(t)

        for i in range(self.tab_editors.count()):
            editor = self.tab_editors.widget(i)
            if isinstance(editor, CodeEditor):
                editor.apply_theme(t)
            elif isinstance(editor, FastTutorialFrame):
                editor.retheme(t)
            elif hasattr(editor, "apply_theme"):
                editor.apply_theme(t)
        self.tab_editors.tabBar().retheme(t)
        self.tab_editors.retheme(t)

        self.find_replace_widget.retheme(t)
        self.status_bar.retheme(t)
        self.options_menu.update_styles(t)
        self.treeview.retheme(t)
        self.terminalWidget.retheme(t)
        self.title_bar.retheme(t)

        self.minimap.retheme(t)

        for w in (self.search_menu, self.git_menu, self.extns_menu, self.infoBtn):
            if hasattr(w, "retheme"):
                w.retheme(t)

        btn_hover = t.color("sidebar.button_hover")
        btn_css = (
            f"QPushButton{{background-color: transparent; border: none; border-radius: 10px;}}"
            f"QPushButton:hover{{background-color: {btn_hover};}}" + tip_css
        )
        for btn in (
            self.explorerBtn,
            self.searchBtn,
            self.gitChangesBtn,
            self.extensionsBtn,
            self.infoBtn,
            self.terminalBtn,
            self.preferencesBtn,
        ):
            btn.setStyleSheet(btn_css)

    def toggle_find_replace(self):
        editor = self._get_current_editor()
        if editor is None:
            return
        if self.find_replace_widget.isVisible():
            self.find_replace_widget.hide()
        else:
            self.find_replace_widget.show()
            self.find_replace_widget.find_input.setFocus()

    def closeEvent(self, event):
        if self._jedi_worker.isRunning():
            self._jedi_worker.shutdown()
        for i in range(self.tab_editors.count()):
            editor = self.tab_editors.widget(i)
            if hasattr(editor, "_lexer") and hasattr(editor._lexer, "shutdown"):
                try:
                    editor._lexer.shutdown()
                except Exception:
                    pass
        event.accept()

    def _on_jedi_results(self, payload, request_id):
        editor = self._pending_jedi_requests.pop(request_id, None)
        if editor is None:
            return
        cmd, rid, data = payload
        if cmd == "complete":
            editor.handle_jedi_completion_results(data)
        elif cmd == "goto":
            editor.handle_jedi_goto_results(data)
        elif cmd == "hover":
            editor.handle_jedi_hover_results(data)

    def _on_jedi_error(self, error_msg, request_id):
        self._pending_jedi_requests.pop(request_id, None)

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
        self.options_menu.config_run_options.clicked.connect(
            lambda: self.tab_editors.open_configurations_json()
        )
        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(self.options_menu)

        #### Status Bar Creation
        self.status_bar = StatusBar(self)

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        main_layout.addLayout(self.body_layout, stretch=1)

        self.leftmost_bar = QFrame()
        self.leftmost_bar.setFixedWidth(50)
        self.leftmost_bar.setStyleSheet("background-color: #25272B; border: none;")
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

        ####################################################
        # Left Panel Stacked Widgets
        ####################################################
        # Services Sidebar
        self.sidebar_frame = QStackedWidget()
        self.sidebar_frame.setStyleSheet("background-color: #171717; border: none;")
        self.sidebar_frame.setMinimumWidth(150)

        self.treeview = DreamFileTreeWindow(self)
        self.treeview.tree.doubleClicked.connect(
            lambda idx: self.open_file_from_treeview(idx)
        )

        #### Some PlaceHolders
        self.search_menu = GlobalFileSearchEngine()
        self.git_menu = SourceControl()
        self.extns_menu = ExtensionsTab()

        self.sidebar_frame.addWidget(self.treeview)
        self.sidebar_frame.addWidget(self.search_menu)
        self.sidebar_frame.addWidget(self.git_menu)
        self.sidebar_frame.addWidget(self.extns_menu)

        self.sidebar_frame.setCurrentIndex(0)

        #### Leftmost Layout Buttons
        # Leftmost bar
        self.leftmost_layout = QVBoxLayout(self.leftmost_bar)
        self.leftmost_layout.setContentsMargins(5, 5, 5, 5)
        self.leftmost_layout.setSpacing(10)
        self.leftmost_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.explorerBtn = self.create_bar_option(
            text=None,
            image="assets/system/folder.png",
            image_size=QSize(30, 30),
            function=lambda: self.sidebar_frame.setCurrentIndex(0),
        )
        self.leftmost_layout.addWidget(self.explorerBtn)
        self.explorerBtn.setToolTip("File Explorer")

        self.searchBtn = self.create_bar_option(
            text=None,
            image="assets/system/find.png",
            image_size=QSize(30, 30),
            function=lambda: self.sidebar_frame.setCurrentIndex(1),
        )
        self.leftmost_layout.addWidget(self.searchBtn)
        self.searchBtn.setToolTip("Find and Replace")

        self.gitChangesBtn = self.create_bar_option(
            text=None,
            image="assets/system/git.png",
            image_size=QSize(30, 30),
            function=lambda: self.sidebar_frame.setCurrentIndex(2),
        )
        self.leftmost_layout.addWidget(self.gitChangesBtn)
        self.gitChangesBtn.setToolTip("Manage Changes")

        self.extensionsBtn = self.create_bar_option(
            text=None,
            image="assets/system/extensions.png",
            image_size=QSize(26, 26),
            function=lambda: self.sidebar_frame.setCurrentIndex(3),
        )
        self.leftmost_layout.addWidget(self.extensionsBtn)
        self.extensionsBtn.setToolTip("Open Marketplace")

        self.leftmost_layout.addStretch()

        self.infoBtn = self.create_bar_option(
            text=None, image="assets/system/info.png", image_size=QSize(26, 26)
        )
        self.leftmost_layout.addWidget(self.infoBtn)
        self.infoBtn.setToolTip("Manage Code Quality")

        self.terminalBtn = self.create_bar_option(
            text=None,
            image="assets/system/terminal.png",
            image_size=QSize(26, 26),
            function=lambda: self.toggle_terminal(),
        )
        self.leftmost_layout.addWidget(self.terminalBtn)
        self.terminalBtn.setToolTip("Open Terminals")

        self.preferencesBtn = self.create_bar_option(
            text=None,
            image="assets/system/version_control.png",
            image_size=QSize(26, 26),
            function=lambda: self._show_preferences_menu(self.preferencesBtn),
        )
        self.leftmost_layout.addWidget(self.preferencesBtn)
        self.preferencesBtn.setToolTip("Set Preferences")

        ####################################################
        # Main Editor
        ####################################################
        # Editor, Background screen, and other stacked layout widgets
        self.main_editor_area = QStackedWidget()

        self.background_window = BackgroundHintsFrame(self)

        # main editor area
        editor_container = QWidget()

        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        self._dirty_tracker = DirtyTracker(self)
        self.tab_editors = DreamTabbedEditor(self, dirty_tracker=self._dirty_tracker)
        self._dirty_tracker.start()

        editor_layout.addWidget(self.tab_editors)

        self.find_replace_widget = FindReplaceWidget(editor_container, self.tab_editors)
        self.find_replace_widget.hide()

        self.main_editor_area.addWidget(self.background_window)
        self.main_editor_area.addWidget(editor_container)

        # Minimap
        self.minimap = MiniMap(self)
        self.minimap.setMinimumWidth(100)
        self.minimap.setMaximumWidth(100)

        self.tab_editors.installEventFilter(self)

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
        self.terminalWidget = TerminalPanel(self)
        self.hero_splitter.addWidget(self.terminalWidget)
        self.hero_splitter.setOpaqueResize(True)
        self.terminalWidget.close_requested.connect(self.toggle_terminal)

        self.hero_splitter.setCollapsible(1, True)
        self.hero_splitter.setSizes([800, 0])

        main_layout.addWidget(self.status_bar)

        self.installEventFilter(self)
        self._jedi_worker.start()
        self.sync_changes_on_tab_switch(self.tab_editors.currentIndex())
        self.tab_editors.currentChanged.connect(self.sync_changes_on_tab_switch)
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

    def sync_changes_on_tab_switch(self, index):
        editor = self.tab_editors.widget(index) if index >= 0 else None
        self.minimap.bind_editor(editor if isinstance(editor, CodeEditor) else None)
        self.update_position_status()

    def update_position_status(self):
        editor = self._get_current_editor()
        if editor:
            line, col = editor.getCursorPosition()
            self.status_bar.lines_and_cols.setText(f"Ln {line + 1} : Col {col + 1}")
        else:
            self.status_bar.lines_and_cols.setText("")

    def _get_current_editor(self):
        """Returns the currently active QScintilla instance, or None."""
        current_widget = self.tab_editors.currentWidget()
        if isinstance(current_widget, CodeEditor):
            return current_widget
        return None

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
        logger.debug(f"[MAIN] moveEvent state={self._state_str()}")
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

    def _show_preferences_menu(self, button: QPushButton):
        THEMES = [
            ("dark", "Dark"),
            ("light", "Light"),
            ("ocean", "Ocean"),
            ("solarized_dark", "Solarized Dark"),
            ("solarized_light", "Solarized Light"),
            ("arcade", "Arcade"),
            ("hacker_blue", "Hacker Blue"),
            ("davy", "Davy"),
            ("high_contrast_dark", "High Contrast Dark"),
            ("coffee_dark", "Coffee Dark"),
            ("coffee_light", "Coffee Light"),
        ]

        menu = QMenu(self)

        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.theme_manager.color("menu.background")};
                color: {self.theme_manager.color("menu.text")};
                border: 1px solid {self.theme_manager.color("menu.border")};
                padding: 6px 0px;
                font-family: Inter, Arial;
                font-size: 13px;
            }}

            QMenu::item {{
                padding: 8px 28px 8px 18px;
                background: transparent;
            }}

            QMenu::item:selected {{
                background-color: {self.theme_manager.color("menu.selected")};
            }}

            QMenu::separator {{
                height: 1px;
                background: {self.theme_manager.color("menu.separator")};
                margin: 6px 10px;
            }}

            QMenu::right-arrow {{
                image: none;
            }}
        """)

        # Header (disabled action)
        header = QAction("General Settings", self)
        header.setEnabled(False)
        menu.addAction(header)

        menu.addSeparator()

        # Toggle actions
        auto_save = QAction("Enable Auto-Save", self)
        menu.addAction(auto_save)

        minimap = QAction("Minimap Enabled", self)
        menu.addAction(minimap)

        sound = QAction("Enable Sound Effects", self)
        menu.addAction(sound)

        line_numbers = QAction("Show Line Numbers", self)
        menu.addAction(line_numbers)

        menu.addSeparator()

        # Theme submenu
        theme_menu = QMenu("Theme", self)

        theme_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.theme_manager.color("menu.background")};
                color: {self.theme_manager.color("menu.text")};
                border: 1px solid {self.theme_manager.color("menu.border")};
            }}

            QMenu::item {{
                padding: 8px 28px 8px 18px;
            }}

            QMenu::item:selected {{
                background-color: {self.theme_manager.color("menu.selected")};
            }}
        """)

        for theme_key, theme_label in THEMES:
            action = QAction(theme_label, self)
            action.triggered.connect(
                lambda checked, t=theme_key: self.theme_manager.switch_to(t)
            )

            theme_menu.addAction(action)

        menu.addMenu(theme_menu)

        # Font size submenu
        font_menu = QMenu("Font Size", self)

        for size in [10, 12, 14, 16, 18]:
            action = QAction(str(size), self)

            action.triggered.connect(
                lambda checked, s=size: self.tab_editors.set_font_size(s)
            )

            font_menu.addAction(action)

        menu.addMenu(font_menu)

        menu.addSeparator()

        close_action = QAction("Close", self)
        menu.addAction(close_action)

        # Position menu relative to edge button, offset upward for clarity
        pos = button.mapToGlobal(button.rect().bottomRight())
        pos += QPoint(-180, -360)
        menu.exec(pos)

    def update_editor_visibility(self):
        if not hasattr(self, "minimap") or not hasattr(self, "main_editor_area"):
            return
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
            self.hero_splitter.setSizes([800, 700])
            self.terminal_collapsed = False
            self.terminalWidget.switch_tab(1)
        else:
            workspace_h = hero_total
            self.hero_splitter.setSizes([workspace_h, 0])
            self.terminal_collapsed = True
            self.terminalWidget.switch_tab(0)

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
        logger.debug(f"Current directory: {self.currentDirectory}")
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
            logger.error(f"Open file failed: {e}")
            return

    def ui_build_save_file(self):
        return self.tab_editors.save_current_file()

    def ui_build_save_all(self):
        return self.tab_editors.save_all_files()

    def ui_build_save_as(self):
        return self.tab_editors.save_current_file_as()

    def ui_build_close_all_editors(self):
        self.tab_editors.save_all_files()
        for i in range(self.tab_editors.count() - 1, -1, -1):
            tab_to_close = self.tab_editors.widget(i)
            if tab_to_close:
                self.tab_editors.close_editor(i)

    def ui_build_show_welcome(self):
        self.tab_editors.add_new_editor(welcome=True)
