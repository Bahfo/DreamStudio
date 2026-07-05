"""
(C) COPYRIGHT 2026 EXcellent TechStacks
Terminal Emulator Logic for DreamStudio.
"""

import os
import sys
import logging

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QFrame,
    QSplitter,
    QScrollBar,
    QMenu,
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon, QColor, QPixmap, QAction, QCursor

from editor.terminal.emulator import ShellEmulator
from editor.terminal.terminal_display import TerminalDisplay

logger = logging.getLogger(__name__)


class _SessionItem(QWidget):
    kill_clicked = pyqtSignal(int)

    def __init__(self, session_id: int, display_name: str, parent=None):
        super().__init__(parent)
        self.session_id = session_id

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)

        self._label = QLabel(display_name)
        self._label.setStyleSheet(
            "color: #cccccc; font-size: 12px; background:transparent;"
        )
        layout.addWidget(self._label)

        layout.addStretch()

        btn_kill = QPushButton()
        btn_kill.setIcon(QIcon("assets/menus/trash.png"))
        btn_kill.setFixedSize(20, 20)
        btn_kill.setToolTip("Kill this terminal session")
        btn_kill.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                color: #888888;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #ff4444;
                background-color: #3c3c3c6a;
                border-radius: 3px;
            }
        """
        )
        btn_kill.clicked.connect(self._on_kill)
        layout.addWidget(btn_kill)

    def _on_kill(self) -> None:
        self.kill_clicked.emit(self.session_id)

    def set_theme(self, bg: str, fg: str) -> None:
        self._label.setStyleSheet(
            f"color: {fg}; font-size: 12px; background:transparent;"
        )


class _TerminalView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.display = TerminalDisplay()
        layout.addWidget(self.display, 1)

        self._scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self._scrollbar.setStyleSheet(
            """
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 8px;
                margin: 0;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #424242;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555555;
            }
            QScrollBar:horizontal {
                background: #1e1e1e;
                height: 8px;
                margin: 0;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: #424242;
                min-width: 24px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #555555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                height: 0;
                width: 0;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
                border: none;
            }
        """
        )
        layout.addWidget(self._scrollbar)

        self.display.history_changed.connect(self._on_display_history)
        self._scrollbar.valueChanged.connect(self._on_scrollbar_changed)

    def _on_display_history(self, offset: int, max_offset: int) -> None:
        self._scrollbar.blockSignals(True)
        self._scrollbar.setRange(0, max_offset)
        self._scrollbar.setPageStep(self.display.rows)
        self._scrollbar.setValue(offset)
        self._scrollbar.blockSignals(False)

    def _on_scrollbar_changed(self, value: int) -> None:
        self.display.set_scroll_offset(value)

    def set_theme(self, bg: str, fg: str, sel: str) -> None:
        self.display.set_theme(bg, fg, sel)
        bg_q = QColor(bg)
        if bg_q.lightness() > 50:
            handle = bg_q.darker(130).name()
            handle_hover = bg_q.darker(150).name()
        else:
            handle = bg_q.lighter(150).name()
            handle_hover = bg_q.lighter(170).name()
        self._scrollbar.setStyleSheet(
            f"""
            QScrollBar:vertical {{
                background: {bg};
                width: 8px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {handle};
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {handle_hover};
            }}
            QScrollBar:horizontal {{
                background: {bg};
                height: 8px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {handle};
                min-width: 24px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {handle_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                height: 0;
                width: 0;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
                border: none;
            }}
        """
        )


class _EmptyTerminalPlaceholder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self._icon = QLabel()
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap("assets/system/sleeping.png")
        if not pixmap.isNull():
            self._icon.setPixmap(pixmap.scaled(
                64, 64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        layout.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel("No Terminals Open")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet(
            "color: #cccccc; font-size: 14px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(self._title, 0, Qt.AlignmentFlag.AlignCenter)

        self._subtitle = QLabel(
            "Click the (+) button to add a new system terminal,\n"
            "or click the tools menu (...) to configure a terminal."
        )
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setWordWrap(True)
        self._subtitle.setStyleSheet(
            "color: #888888; font-size: 12px; background: transparent;"
        )
        layout.addWidget(self._subtitle, 0, Qt.AlignmentFlag.AlignCenter)

    def retheme(self, bg: str, fg: str) -> None:
        self.setStyleSheet(f"background: transparent;")
        self._title.setStyleSheet(
            f"color: {fg}; font-size: 14px; font-weight: bold; background: transparent;"
        )
        fg_q = QColor(fg)
        muted = QColor(
            min(255, fg_q.red() + (0 - fg_q.red()) // 2),
            min(255, fg_q.green() + (0 - fg_q.green()) // 2),
            min(255, fg_q.blue() + (0 - fg_q.blue()) // 2),
        )
        self._subtitle.setStyleSheet(
            f"color: {muted.name()}; font-size: 12px; background: transparent;"
        )


class TerminalWorkspace(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sessions: dict[int, dict] = {}
        self._id_counter = 0
        self._active_id: int | None = None
        self._theme_bg: str | None = None
        self._theme_fg: str | None = None
        self._theme_sel: str | None = None
        self._menu_bg: str = "#1E1E1E"
        self._menu_fg: str = "#cccccc"
        self._menu_border: str = "#3F4145"
        self._menu_sel_bg: str = "#2E436E"
        self._menu_sel_fg: str = "#ffffff"
        self._menu_disabled_fg: str = "#555555"
        self._menu_sep: str = "#3F4145"

        self.setObjectName("terminalWorkspace")
        self.setStyleSheet(
            """
            QWidget#terminalWorkspace {
                background-color: #252526;
            }
        """
        )

        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 0, 0, 0)
        outer.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(1)
        self._splitter.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #3c3c3c;
            }
        """
        )

        self._stack = QStackedWidget()
        self._empty_placeholder = _EmptyTerminalPlaceholder()
        self._stack.addWidget(self._empty_placeholder)
        self._stack.setCurrentWidget(self._empty_placeholder)
        self._splitter.addWidget(self._stack)

        self._sidebar = self._build_sidebar()
        self._splitter.addWidget(self._sidebar)

        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 0)
        self._splitter.setSizes([600, 200])

        outer.addWidget(self._splitter)

    def _build_sidebar(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("terminalSidebar")
        widget.setMinimumWidth(160)
        widget.setMaximumWidth(320)
        widget.setStyleSheet(
            """
            QWidget#terminalSidebar {
                background-color: #252526;
                border-left: 1px solid #3c3c3c;
            }
        """
        )

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("terminalSidebarHeader")
        header.setFixedHeight(30)
        header.setStyleSheet("""background:transparent;""")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(0)

        self._sidebar_title = QLabel("TERMINALS")
        self._sidebar_title.setObjectName("terminalSidebarTitle")
        self._sidebar_title.setStyleSheet(
            """color: #888888; font-size: 10px; font-weight: bold; 
            letter-spacing: 1px; background:transparent"""
        )
        header_layout.addWidget(self._sidebar_title)
        header_layout.addStretch()

        self._sidebar_add_btn = QPushButton("+")
        self._sidebar_add_btn.setObjectName("terminalSidebarAddBtn")
        self._sidebar_add_btn.setFixedSize(22, 22)
        self._sidebar_add_btn.setToolTip("Create new terminal session")
        self._sidebar_add_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                color: #cccccc;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3c3c3c;
                border-radius: 4px;
                color: #ffffff;
            }
        """
        )
        self._sidebar_add_btn.clicked.connect(self._show_terminal_type_menu)
        header_layout.addWidget(self._sidebar_add_btn)

        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list.setStyleSheet(
            """
            QListWidget {
                background: transparent;
                border: none;
                color: #cccccc;
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
            }
            QListWidget::item:selected {
                background-color: #37373d;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
        """
        )
        self._list.currentRowChanged.connect(self._on_list_row_changed)
        layout.addWidget(self._list)

        return widget

    def _build_menu_style(self) -> str:
        return f"""
        QMenu {{
            background-color: {self._menu_bg};
            color: {self._menu_fg};
            border: 1px solid {self._menu_border};
            border-radius: 0px;
            padding: 4px 0px;
            font-family: 'inter', Arial;
            font-size: 13px;
        }}
        QMenu::item {{
            padding: 6px 24px 6px 32px;
            background-color: transparent;
        }}
        QMenu::item:selected {{
            background-color: {self._menu_sel_bg};
            color: {self._menu_sel_fg};
        }}
        QMenu::item:disabled {{
            color: {self._menu_disabled_fg};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {self._menu_sep};
            margin: 4px 0px;
        }}
        QMenu::indicator {{
            width: 18px;
            height: 18px;
            margin-left: 6px;
            margin-right: 4px;
            border-radius: 4px;
            border: 1px solid {self._menu_border};
            background-color: transparent;
        }}
        QMenu::indicator:checked {{
            background-color: {self._menu_sel_bg};
            border: 1px solid {self._menu_sel_bg};
            image: url(assets/menus/check.png);
        }}
        """

    def _show_terminal_type_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(self._build_menu_style())

        is_windows = sys.platform == "win32"
        primary_label = "PowerShell" if is_windows else "Bash"
        primary_shell = "powershell.exe" if is_windows else os.environ.get("SHELL", "/bin/bash")

        primary_act = QAction(primary_label, menu)
        primary_act.triggered.connect(
            lambda checked, shell=primary_shell: self._on_add_session(shell=shell)
        )
        menu.addAction(primary_act)

        menu.addSeparator()

        placeholder_types = [
            "Zsh",
            "Fish",
            "cmd (Command Prompt)",
            "SSH Session",
            "Docker Container",
            "WSL",
        ]
        for label in placeholder_types:
            act = QAction(label, menu)
            act.setEnabled(False)
            menu.addAction(act)

        menu.exec(QCursor.pos())

    def _on_add_session(self, cwd: str | None = None, shell: str | None = None) -> None:
        self._id_counter += 1
        session_id = self._id_counter

        if shell is None:
            shell = os.environ.get("SHELL", "/bin/bash")
        shell_name = os.path.basename(shell)
        display_name = f"{shell_name}"

        view = _TerminalView()
        display = view.display
        emulator = ShellEmulator()

        emulator.raw_output_received.connect(display.feed)
        display.send_data.connect(
            lambda data, e=emulator: e.write(data.decode("utf-8", errors="replace"))
        )
        display.resized.connect(emulator.resize)
        display.set_emulator(emulator)

        emulator.start(cwd=cwd or os.getcwd())

        self._stack.addWidget(view)

        if self._stack.currentWidget() is self._empty_placeholder:
            self._stack.setCurrentWidget(view)

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, session_id)
        session_widget = _SessionItem(session_id, display_name)
        session_widget.kill_clicked.connect(self.kill_session)
        item.setSizeHint(session_widget.sizeHint())

        self._list.blockSignals(True)
        self._list.addItem(item)
        self._list.setItemWidget(item, session_widget)
        new_row = self._list.count() - 1
        self._list.blockSignals(False)

        if self._theme_bg is not None:
            view.set_theme(self._theme_bg, self._theme_fg, self._theme_sel)
            session_widget.set_theme(self._theme_bg, self._theme_fg)

        self._sessions[session_id] = {
            "view": view,
            "display": display,
            "emulator": emulator,
            "list_item": item,
            "session_widget": session_widget,
            "name": display_name,
        }

        self._list.setCurrentRow(new_row)

    def _on_list_row_changed(self, row: int) -> None:
        if row < 0:
            return
        item = self._list.item(row)
        if item is None:
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if session_id not in self._sessions:
            return

        view = self._sessions[session_id]["view"]
        self._stack.setCurrentWidget(view)
        display = view.display

        QTimer.singleShot(0, display.setFocus)

        self._active_id = session_id

    def kill_session(self, session_id: int) -> None:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return

        emulator = session["emulator"]
        view = session["view"]
        item = session["list_item"]

        idx = self._stack.indexOf(view)
        if idx >= 0:
            self._stack.removeWidget(view)
        view.deleteLater()

        row = self._list.row(item)
        self._list.blockSignals(True)
        self._list.takeItem(row)
        self._list.blockSignals(False)

        if self._active_id == session_id:
            self._active_id = None
            remaining = self._list.count()
            if remaining > 0:
                new_row = min(row, remaining - 1)
                self._list.setCurrentRow(new_row)

        emulator.kill()

        if len(self._sessions) == 0:
            self._stack.setCurrentWidget(self._empty_placeholder)

    def set_theme(self, bg: str, fg: str, sel: str) -> None:
        self._theme_bg = bg
        self._theme_fg = fg
        self._theme_sel = sel

        for session in self._sessions.values():
            session["view"].set_theme(bg, fg, sel)
            session["session_widget"].set_theme(bg, fg)

        self._apply_sidebar_theme()

    def _apply_sidebar_theme(self) -> None:
        bg = self._theme_bg or "#1e1e1e"
        fg = self._theme_fg or "#d4d4d4"

        bg_q = QColor(bg)
        fg_q = QColor(fg)

        if bg_q.lightness() > 50:
            sidebar_bg = bg_q.darker(103).name()
            border = bg_q.darker(115).name()
            hover_bg = bg_q.darker(108).name()
            selected_bg = bg_q.darker(112).name()
        else:
            sidebar_bg = bg_q.lighter(103).name()
            border = bg_q.lighter(150).name()
            hover_bg = bg_q.lighter(120).name()
            selected_bg = bg_q.lighter(115).name()

        title_fg = f"rgba({fg_q.red()}, {fg_q.green()}, {fg_q.blue()}, 0.6)"

        self._menu_bg = sidebar_bg
        self._menu_fg = fg
        self._menu_border = border
        self._menu_sel_bg = selected_bg
        self._menu_sel_fg = "#ffffff" if bg_q.lightness() < 50 else "#000000"
        self._menu_disabled_fg = f"rgba({fg_q.red()}, {fg_q.green()}, {fg_q.blue()}, 0.35)"
        self._menu_sep = border

        self.setStyleSheet(
            f"""
            QWidget#terminalWorkspace {{
                background-color: {sidebar_bg};
            }}
        """
        )

        self._sidebar.setStyleSheet(
            f"""
            QWidget#terminalSidebar {{
                background-color: {sidebar_bg};
                border-left: 1px solid {border};
            }}
        """
        )

        self._sidebar_title.setStyleSheet(
            f"""
            color: {title_fg}; font-size: 10px; font-weight: bold;
            letter-spacing: 1px; background:{sidebar_bg};
        """
        )

        self._sidebar_add_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {fg};
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border-radius: 4px;
                color: {fg};
            }}
        """
        )

        self._list.setStyleSheet(
            f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: {fg};
                font-size: 12px;
                outline: none;
            }}
            QListWidget::item {{
                border: none;
                padding: 0px;
            }}
            QListWidget::item:selected {{
                background-color: {selected_bg};
            }}
            QListWidget::item:hover {{
                background-color: {hover_bg};
            }}
        """
        )

        self._splitter.setStyleSheet(
            f"""
            QSplitter::handle {{
                background-color: {border};
            }}
        """
        )

        self._empty_placeholder.retheme(bg, fg)

    def active_session_id(self) -> int | None:
        return self._active_id

    def active_count(self) -> int:
        return len(self._sessions)

    def cleanup(self) -> None:
        for session_id in list(self._sessions.keys()):
            self.kill_session(session_id)

    def closeEvent(self, event) -> None:
        self.hide()
        event.ignore()
