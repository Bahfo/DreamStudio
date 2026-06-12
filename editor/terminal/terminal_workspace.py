"""
(C) COPYRIGHT 2026 EXcellent TechStacks
Terminal Emulator Logic for DreamStudio.
"""

import os
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
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon, QColor

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
        btn_kill.setStyleSheet("""
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
        """)
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
        self._scrollbar.setStyleSheet("""
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
        """)
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
        self._scrollbar.setStyleSheet(f"""
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
        """)


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

        self.setObjectName("terminalWorkspace")
        self.setStyleSheet("""
            QWidget#terminalWorkspace {
                background-color: #252526;
            }
        """)

        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 0, 0, 0)
        outer.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(1)
        self._splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3c3c3c;
            }
        """)

        self._stack = QStackedWidget()
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
        widget.setStyleSheet("""
            QWidget#terminalSidebar {
                background-color: #252526;
                border-left: 1px solid #3c3c3c;
            }
        """)

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
        self._sidebar_add_btn.setStyleSheet("""
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
        """)
        self._sidebar_add_btn.clicked.connect(self._on_add_session)
        header_layout.addWidget(self._sidebar_add_btn)

        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list.setStyleSheet("""
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
        """)
        self._list.currentRowChanged.connect(self._on_list_row_changed)
        layout.addWidget(self._list)

        return widget

    def _on_add_session(self, cwd: str | None = None) -> None:
        self._id_counter += 1
        session_id = self._id_counter

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

        self.setStyleSheet(f"""
            QWidget#terminalWorkspace {{
                background-color: {sidebar_bg};
            }}
        """)

        self._sidebar.setStyleSheet(f"""
            QWidget#terminalSidebar {{
                background-color: {sidebar_bg};
                border-left: 1px solid {border};
            }}
        """)

        self._sidebar_title.setStyleSheet(f"""
            color: {title_fg}; font-size: 10px; font-weight: bold;
            letter-spacing: 1px; background:{sidebar_bg};
        """)

        self._sidebar_add_btn.setStyleSheet(f"""
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
        """)

        self._list.setStyleSheet(f"""
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
        """)

        self._splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {border};
            }}
        """)

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
