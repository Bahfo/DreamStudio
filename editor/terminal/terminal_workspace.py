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
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QSize
from PyQt6.QtGui import QIcon

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
                background-color: #3c3c3c;
                border-radius: 3px;
            }
        """)
        btn_kill.clicked.connect(self._on_kill)
        layout.addWidget(btn_kill)

    def _on_kill(self) -> None:
        self.kill_clicked.emit(self.session_id)


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
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #424242;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
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


class TerminalWorkspace(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sessions: dict[int, dict] = {}
        self._id_counter = 0
        self._active_id: int | None = None

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

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3c3c3c;
            }
        """)

        self._stack = QStackedWidget()
        splitter.addWidget(self._stack)

        self._sidebar = self._build_sidebar()
        splitter.addWidget(self._sidebar)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([600, 200])

        outer.addWidget(splitter)

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
        header.setFixedHeight(30)
        header.setStyleSheet("""background:#252526;""")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(0)

        title = QLabel("TERMINALS")
        title.setStyleSheet("""color: #888888; font-size: 10px; font-weight: bold; 
            letter-spacing: 1px; background:#252526""")
        header_layout.addWidget(title)
        header_layout.addStretch()

        btn_add = QPushButton("+")
        btn_add.setFixedSize(22, 22)
        btn_add.setToolTip("Create new terminal session")
        btn_add.setStyleSheet("""
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
        btn_add.clicked.connect(self._on_add_session)
        header_layout.addWidget(btn_add)

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

        self._sessions[session_id] = {
            "view": view,
            "display": display,
            "emulator": emulator,
            "list_item": item,
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
        for session in self._sessions.values():
            session["view"].display.set_theme(bg, fg, sel)

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
