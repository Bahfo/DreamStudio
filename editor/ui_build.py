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
import pathlib
import os

from typing import Optional

# Third-Party Imports (GUI)
from PyQt6.QtCore import QDir, QEvent, QPoint, QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QStackedWidget,
    QApplication,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QSplitter,
    QWidget,
    QDialog,
    QFrame,
    QLabel,
    QMenu,
)

# Local Application Imports - Backend
from backend.dirty_tracker import DirtyTracker
from editor.lsp.jedi_worker import JediWorker

# Local Application Imports - UI Components
from editor.widgets.QSplashOverlay import SplashOverlay
from editor.terminal.terminal_ui import TerminalPanel
from editor.texteditor.minimap import MiniMap
from editor.texteditor.tab_editor import (
    CodeEditor,
    DreamTabbedEditor,
    FastTutorialFrame,
    BackgroundHintsFrame,
)
from editor.utils.find_replace import FindReplaceWidget, GlobalFileSearchEngine
from editor.utils.theme_manager import ThemeManager, SyntaxThemeManager
from editor.utils.file_explorer import DreamFileTreeWindow
from editor.utils.titleBar import DreamStudioTitleBar
from editor.utils.source_control import SourceControl
from editor.utils.marketplace import ExtensionsTab
from editor.utils.optionsBar import OptionsMenu
from editor.utils.statusBar import StatusBar
from editor.utils.tools.tools_manager import ToolsManager

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
        self.setStyleSheet("background-color: #1E1E1E; font-family: 'inter', Arial;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Jedi background worker
        self._jedi_worker = JediWorker()
        self._jedi_worker.results_ready.connect(self._on_jedi_results)
        self._jedi_worker.error_occurred.connect(self._on_jedi_error)
        self._pending_jedi_requests = {}
        self._jedi_request_counter = 0
        self._update_jedi_venv(None)

        self.setup_layout()

        self.theme_manager = ThemeManager(self)
        self.theme_manager.theme_changed.connect(self._on_theme_changed)
        self._on_theme_changed(self.theme_manager.name)

        self.syntax_theme_manager = SyntaxThemeManager(self.theme_manager, self)
        self.syntax_theme_manager.theme_changed.connect(self._on_syntax_theme_changed)

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
        self._apply_theme_colors(self.theme_manager)

    def _apply_theme_colors(self, t):
        border_c = t.color("widget.border", "#3F4145")
        tip_css = (
            f"QToolTip{{color: {t.color('tooltip.text')}; font-family: 'inter', sans-serif;"
            f" padding: 8px 8px; font-size: 12px; line-height: 1.5;"
            f" background-color: {t.color('tooltip.background')};"
            f" border: 1px solid {border_c};"
            f" border-radius: 8px;}}"
        )

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(
                f"QToolTip{{background-color: {t.color('tooltip.background')};"
                f" color: {t.color('tooltip.text')};"
                f" border: 1px solid {border_c};"
                f" border-radius: 8px;"
                f" padding: 8px 8px;"
                f" font-family: 'inter', sans-serif;"
                f" font-size: 12px;"
                f" line-height: 1.5;}}"
            )

        self.setStyleSheet(
            f"background-color: {t.color('window.background')};"
            f" color: {t.color('window.text')};"
            f" font-family: 'inter', Arial;" + tip_css
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
        self.center_splitter.setStyleSheet(
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
            elif hasattr(editor, "retheme"):
                editor.retheme(t)
        self.tab_editors.tabBar().retheme(t)
        self.tab_editors.retheme(t)

        self.find_replace_widget.retheme(t)
        self.status_bar.retheme(t)
        self.options_menu.update_styles(t)
        self.treeview.retheme(t)
        self.terminalWidget.retheme(t)
        self.title_bar.retheme(t)

        self.minimap.retheme(t)
        self.tools_manager.retheme_tools(t)

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

    def _on_syntax_theme_changed(self, theme_name: str):
        t = self.syntax_theme_manager
        for i in range(self.tab_editors.count()):
            editor = self.tab_editors.widget(i)
            if isinstance(editor, CodeEditor):
                editor.apply_syntax_only(t)
            elif hasattr(editor, "apply_syntax_only"):
                editor.apply_syntax_only(t)
            elif hasattr(editor, "retheme"):
                editor.retheme(t)

    def flash_button(
        self, button: QPushButton, color: str = "#4A6FA5", duration: int = 400
    ):
        original = button.styleSheet()
        flash_css = (
            f"""QPushButton{{background-color: {color}; 
                border: none; border-radius: 10px;}}"""
            f"QPushButton:hover{{background-color: {color};}}"
        )
        button.setStyleSheet(flash_css)
        QTimer.singleShot(duration, lambda: button.setStyleSheet(original))

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
        if hasattr(self, "_project_bootstrap") and self._project_bootstrap is not None:
            self._project_bootstrap.wait(5000)
            self._project_bootstrap = None
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
        entry = self._pending_jedi_requests.pop(request_id, None)
        if entry is None:
            return
        if isinstance(entry, tuple):
            editor, req_type = entry
        else:
            editor, req_type = entry, "unknown"
        cmd, rid, data = payload
        if cmd == "complete":
            editor.handle_jedi_completion_results(data)
        elif cmd == "goto":
            editor.handle_jedi_goto_results(data)
        elif cmd == "hover":
            editor.handle_jedi_hover_results(data)
        elif cmd == "references":
            editor.handle_jedi_references_results(data)

    def _on_jedi_error(self, error_msg, request_id):
        self._pending_jedi_requests.pop(request_id, None)

    def _widget_Focus(self, frame, color):
        overlay = SplashOverlay(frame, color)
        overlay.show()

    def setup_layout(self):
        main_layout = self._build_main_layout()
        self._build_title_bar(main_layout)
        self._build_sidebars()
        self._build_editor_area()
        self._build_splitters()
        self._build_terminal(main_layout)
        self._connect_signals()

    def _build_main_layout(self) -> QVBoxLayout:
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        main_layout.addLayout(self.body_layout, stretch=1)

        self.status_bar = StatusBar(self)
        self.status_bar.statusBtn.clicked.connect(
            self.status_bar.show_bootstrap_details
        )
        main_layout.addWidget(self.status_bar)
        return main_layout

    def _build_title_bar(self, main_layout: QVBoxLayout) -> None:
        self.title_bar = DreamStudioTitleBar(self)
        self.options_menu = OptionsMenu(self)
        main_layout.insertWidget(0, self.title_bar)
        main_layout.insertWidget(1, self.options_menu)

    def _build_sidebars(self) -> None:
        self.leftmost_bar = QFrame()
        self.leftmost_bar.setFixedWidth(50)
        self.leftmost_bar.setStyleSheet("background-color: #25272B; border: none;")
        self.body_layout.addWidget(self.leftmost_bar)
        self._build_leftmost_buttons()

        self.sidebar_frame = QStackedWidget()
        self.sidebar_frame.setStyleSheet("background-color: #171717; border: none;")
        self.sidebar_frame.setMinimumWidth(150)

        self.treeview = DreamFileTreeWindow(self)
        self.treeview.tree.doubleClicked.connect(
            lambda idx: self.open_file_from_treeview(idx)
        )

        self.search_menu = GlobalFileSearchEngine()
        self.git_menu = SourceControl(self)
        self.extns_menu = ExtensionsTab()

        self.sidebar_frame.addWidget(self.treeview)
        self.sidebar_frame.addWidget(self.search_menu)
        self.sidebar_frame.addWidget(self.git_menu)
        self.sidebar_frame.addWidget(self.extns_menu)
        self.sidebar_frame.setCurrentIndex(0)

    def _build_leftmost_buttons(self) -> None:
        self.leftmost_layout = QVBoxLayout(self.leftmost_bar)
        self.leftmost_layout.setContentsMargins(5, 5, 5, 5)
        self.leftmost_layout.setSpacing(10)
        self.leftmost_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        btn_cfg = [
            (
                "explorerBtn",
                "assets/system/folder.png",
                QSize(30, 30),
                lambda: self.sidebar_frame.setCurrentIndex(0),
                "File Explorer",
            ),
            (
                "searchBtn",
                "assets/system/find.png",
                QSize(30, 30),
                lambda: self.sidebar_frame.setCurrentIndex(1),
                "Find and Replace",
            ),
            (
                "gitChangesBtn",
                "assets/system/git.png",
                QSize(30, 30),
                lambda: self.sidebar_frame.setCurrentIndex(2),
                "Manage Changes",
            ),
            (
                "extensionsBtn",
                "assets/system/extensions.png",
                QSize(26, 26),
                lambda: self.sidebar_frame.setCurrentIndex(3),
                "Open Marketplace",
            ),
        ]
        for name, icon, size, cb, tip in btn_cfg:
            btn = self.create_bar_option(
                text=None, image=icon, image_size=size, function=cb
            )
            btn.setToolTip(tip)
            setattr(self, name, btn)
            self.leftmost_layout.addWidget(btn)

        self.leftmost_layout.addStretch()

        self.infoBtn = self.create_bar_option(
            text=None, image="assets/system/info.png", image_size=QSize(26, 26)
        )
        self.infoBtn.setToolTip("Manage Code Quality")
        self.leftmost_layout.addWidget(self.infoBtn)

        self.terminalBtn = self.create_bar_option(
            text=None,
            image="assets/system/terminal.png",
            image_size=QSize(26, 26),
            function=lambda: self.toggle_terminal(),
        )
        self.terminalBtn.setToolTip("Open Terminals")
        self.leftmost_layout.addWidget(self.terminalBtn)

        self.preferencesBtn = self.create_bar_option(
            text=None,
            image="assets/system/version_control.png",
            image_size=QSize(26, 26),
            function=lambda: self._show_preferences_menu(self.preferencesBtn),
        )
        self.preferencesBtn.setToolTip("Set Preferences")
        self.leftmost_layout.addWidget(self.preferencesBtn)

    def _build_editor_area(self) -> None:
        self.main_editor_area = QStackedWidget()
        self.background_window = BackgroundHintsFrame(self)

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

        self.minimap = MiniMap(self)
        self.minimap_wrapper = QWidget()
        self.minimap_wrapper.setMinimumWidth(100)
        self.minimap_wrapper.setMaximumWidth(120)
        wrapper_layout = QVBoxLayout(self.minimap_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self.minimap)

        self.tab_editors.installEventFilter(self)

    def _build_splitters(self) -> None:
        self.hero_splitter = QSplitter(Qt.Orientation.Vertical)
        self.hero_splitter.setHandleWidth(4)
        self.hero_splitter.setOpaqueResize(True)
        self.hero_splitter.setStyleSheet(
            "QSplitter::handle { background-color: #2a2a2a; }"
            "QSplitter::handle:pressed { background-color: #3a7bd5; }"
        )
        self.body_layout.addWidget(self.hero_splitter)

        self.center_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.center_splitter.setHandleWidth(0)
        self.center_splitter.setChildrenCollapsible(False)
        self.center_splitter.addWidget(self.main_editor_area)
        self.center_splitter.addWidget(self.minimap_wrapper)
        self.center_splitter.setStretchFactor(0, 1)
        self.center_splitter.setStretchFactor(1, 0)
        self.center_splitter.setSizes([800, 100])

        self.tools_manager = ToolsManager(self)
        self.tools_manager.all_tabs_closed.connect(self._collapse_tools_panel)

        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setHandleWidth(1)
        self.workspace_splitter.setStyleSheet(
            "QSplitter::handle { background-color: #1a1a1a; }"
        )

        self.workspace_splitter.addWidget(self.sidebar_frame)
        self.workspace_splitter.addWidget(self.center_splitter)
        self.workspace_splitter.addWidget(self.tools_manager)

        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setStretchFactor(2, 0)

        self.workspace_splitter.setCollapsible(0, True)
        self.workspace_splitter.setCollapsible(1, False)
        self.workspace_splitter.setCollapsible(2, True)

        self.workspace_splitter.setSizes(
            [450, self.workspace_splitter.width() - 450, 0]
        )

        self.hero_splitter.addWidget(self.workspace_splitter)

    def _build_terminal(self, main_layout: QVBoxLayout) -> None:
        self.terminalWidget = TerminalPanel(self)
        self.hero_splitter.addWidget(self.terminalWidget)
        self.hero_splitter.setCollapsible(1, True)
        self.hero_splitter.setSizes([800, 0])
        self.hero_splitter.setOpaqueResize(True)
        self.terminalWidget.close_requested.connect(self.toggle_terminal)

    def _connect_signals(self) -> None:
        self.installEventFilter(self)
        self._jedi_worker.start()
        self.sync_changes_on_tab_switch(self.tab_editors.currentIndex())
        self.tab_editors.currentChanged.connect(self.sync_changes_on_tab_switch)
        self.tab_editors.currentChanged.connect(
            lambda idx: self.title_bar._update_file_menu_states()
        )
        self.tab_editors.currentChanged.connect(
            lambda idx: self.title_bar._update_edit_menu_states()
        )
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
        menu = self._build_preferences_menu()
        pos = button.mapToGlobal(button.rect().bottomRight())
        pos += QPoint(-180, -360)
        menu.exec(pos)

    def _build_preferences_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(self._pref_menu_css())

        header = QAction("General Settings", self)
        header.setEnabled(False)
        menu.addAction(header)
        menu.addSeparator()

        for label in (
            "Enable Auto-Save",
            "Minimap Enabled",
            "Enable Sound Effects",
            "Show Line Numbers",
        ):
            menu.addAction(QAction(label, self))
        menu.addSeparator()

        menu.addMenu(self._build_theme_submenu())
        menu.addMenu(self._build_syntax_theme_submenu())
        menu.addMenu(self._build_font_submenu())
        menu.addSeparator()
        menu.addAction(QAction("Close", self))
        return menu

    def _pref_menu_css(self) -> str:
        t = self.theme_manager
        return f"""
            QMenu {{
                background-color: {t.color("menu.background")};
                color: {t.color("menu.text")};
                border: 1px solid {t.color("menu.border")};
                padding: 6px 0px;
                font-family: 'inter', Arial;
                font-size: 13px;
            }}
            QMenu::item {{ padding: 8px 28px 8px 18px; 
                background: transparent; }}
            QMenu::item:selected {{background-color: {t.color("menu.selected")};}}
            QMenu::separator {{ height: 1px; 
                background: {t.color("menu.separator")}; margin: 6px 10px; }}
            QMenu::right-arrow {{ image: none; }}
        """

    def _menu_theme_css(self) -> str:
        t = self.theme_manager
        return f"""
            QMenu {{
                background-color: {t.color("menu.background")};
                color: {t.color("menu.text")};
                border: 1px solid {t.color("menu.border")};
            }}
            QMenu::item {{ padding: 8px 28px 8px 18px; }}
            QMenu::item:selected {{ background-color: {t.color("menu.selected")}; }}
        """

    def _build_theme_submenu(self) -> QMenu:
        THEMES = [
            ("dark", "Dark"),
            ("light", "Light"),
            ("ocean", "Ocean"),
            ("solarized_dark", "Solarized Dark"),
            ("solarized_light", "Solarized Light"),
            ("Moses", "Moses"),
            ("hacker_blue", "Hacker Blue"),
            ("davy", "Davy"),
            ("high_contrast_dark", "High Contrast Dark"),
            ("coffee_dark", "Coffee Dark"),
            ("coffee_light", "Coffee Light"),
        ]
        sub = QMenu("Theme", self)
        sub.setStyleSheet(self._menu_theme_css())
        for key, label in THEMES:
            a = QAction(label, self)
            a.triggered.connect(lambda checked, t=key: self.theme_manager.switch_to(t))
            sub.addAction(a)
        return sub

    def _build_syntax_theme_submenu(self) -> QMenu:
        THEMES = [
            ("dark", "Dark"),
            ("light", "Light"),
            ("ocean", "Ocean"),
            ("solarized_dark", "Solarized Dark"),
            ("solarized_light", "Solarized Light"),
            ("Moses", "Moses"),
            ("hacker_blue", "Hacker Blue"),
            ("davy", "Davy"),
            ("high_contrast_dark", "High Contrast Dark"),
            ("coffee_dark", "Coffee Dark"),
            ("coffee_light", "Coffee Light"),
        ]
        sub = QMenu("Syntax Theme", self)
        sub.setStyleSheet(self._menu_theme_css())
        for key, label in THEMES:
            a = QAction(label, self)
            a.triggered.connect(
                lambda checked, t=key: self.syntax_theme_manager.switch_to(t)
            )
            sub.addAction(a)
        return sub

    def _build_font_submenu(self) -> QMenu:
        sub = QMenu("Font Size", self)
        for size in (10, 12, 14, 16, 18):
            a = QAction(str(size), self)
            a.triggered.connect(
                lambda checked, s=size: self.tab_editors.set_font_size(s)
            )
            sub.addAction(a)
        return sub

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

    def toggle_system_monitor(self):
        self.open_tools_panel("system_monitor")

    def open_tools_panel(self, tool_name: str) -> None:
        """Opens the tools panel and switches to the requested tool."""
        self.tools_manager._on_click_open(tool_name)
        sizes = self.workspace_splitter.sizes()
        if sizes[2] == 0:
            self.workspace_splitter.setSizes([sizes[0], sizes[1], 400])

    def _collapse_tools_panel(self) -> None:
        """Collapse the tools panel when all tool tabs are closed."""
        sizes = self.workspace_splitter.sizes()
        if sizes[2] > 0:
            self.workspace_splitter.setSizes([sizes[0], sizes[1] + sizes[2], 0])

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

    def bootstrap_project(
        self, manifest_path: str, target_path: str, project_type: str
    ) -> None:
        from editor.init.project_bootstrap import ProjectBootstrap

        if hasattr(self, "_project_bootstrap") and self._project_bootstrap is not None:
            old = self._project_bootstrap
            old.wait(5000)
            self._project_bootstrap = None

        self._project_target_path = target_path
        self.currentDirectory = target_path
        self.treeview.set_treeview_directory(target_path)
        if hasattr(self, "git_menu"):
            self.git_menu.update_workspace(target_path)
        self.status_bar.clear_bootstrap_log()

        self._project_bootstrap = ProjectBootstrap(
            manifest_path=manifest_path,
            target_path=target_path,
            requested_project_type=project_type,
        )
        self._project_bootstrap.step_changed.connect(self._on_bootstrap_step)
        self._project_bootstrap.step_progress.connect(self._on_bootstrap_progress)
        self._project_bootstrap.step_failed.connect(self._on_bootstrap_failed)
        self._project_bootstrap.finished.connect(self._on_bootstrap_finished)
        self._project_bootstrap.start()

    def _find_ide_root(self) -> str:
        path = os.path.abspath(__file__)
        for _ in range(3):
            path = os.path.dirname(path)
        return path

    def _update_jedi_venv(self, project_path: Optional[str]) -> None:
        if project_path:
            candidates = [
                os.path.join(project_path, ".venv", "bin", "python3"),
                os.path.join(project_path, ".venv", "bin", "python"),
                os.path.join(project_path, "venv", "bin", "python3"),
                os.path.join(project_path, "venv", "bin", "python"),
                os.path.join(project_path, ".venv", "Scripts", "python.exe"),
                os.path.join(project_path, "venv", "Scripts", "python.exe"),
            ]
            for c in candidates:
                if os.path.isfile(c):
                    self._jedi_worker.set_virtual_environment(
                        os.path.dirname(os.path.dirname(c))
                    )
                    return
        ide_root = self._find_ide_root()
        fallbacks = [
            os.path.join(ide_root, "venv", "bin", "python3"),
            os.path.join(ide_root, "venv", "bin", "python"),
        ]
        for fb in fallbacks:
            if os.path.isfile(fb):
                self._jedi_worker.set_virtual_environment(
                    os.path.dirname(os.path.dirname(fb))
                )
                return
        self._jedi_worker.set_virtual_environment(None)

    def refresh_project_environment(self, path: str) -> None:
        self.treeview.set_treeview_directory(path)
        self._update_jedi_venv(path)

        if hasattr(self, "git_menu"):
            self.git_menu.update_workspace(path)

        if hasattr(self, "tools_manager"):
            todo_tool = self.tools_manager.get_tool("todo")
            if todo_tool is not None and hasattr(todo_tool, "set_base_dir"):
                todo_tool.set_base_dir(path)

    def _on_bootstrap_step(self, step_name: str, description: str) -> None:
        self.status_bar.set_bootstrap_status(step_name, description)

    def _on_bootstrap_progress(self, message: str) -> None:
        self.status_bar.set_bootstrap_status("progress", message)

    def _on_bootstrap_failed(self, step_name: str, error: str) -> None:
        logger.error("Bootstrap failed at step '%s': %s", step_name, error)
        self.status_bar.set_bootstrap_status("failed", f"Failed: {step_name}")

    def _on_bootstrap_finished(self, success: bool) -> None:
        self.status_bar.set_bootstrap_finished(success)
        if success and hasattr(self, "_project_target_path"):
            self.refresh_project_environment(self._project_target_path)
