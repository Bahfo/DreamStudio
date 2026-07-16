"""
(C) COPYRIGHT 2026 EXcellent TechStacks
Terminal Emulator Logic for DreamStudio.
"""

import os
import logging

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QPlainTextEdit,
    QMenu,
    QApplication,
)
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtCore import pyqtSignal, Qt, QSize

from editor.promptx import CommandLine, HELP
from editor.promptx.highlight import PromptXHighlighter
from editor.terminal.terminal_workspace import TerminalWorkspace
from editor.widgets.QDreamTabEditor import DreamStudioIDETabBar

logger = logging.getLogger(__name__)

TAB_SYSTEM_SHELL = 0
TAB_PROMPTX = 1
TAB_OUTPUT = 2


class _TerminalTabBar(DreamStudioIDETabBar):
    def tabSizeHint(self, index):
        return QSize(80, 32)


class OutputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._text = QPlainTextEdit(self)
        self._text.setObjectName("terminalOutputText")
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(10000)
        layout.addWidget(self._text)

    def append_text(self, text):
        self._text.moveCursor(QTextCursor.MoveOperation.End)
        self._text.insertPlainText(text)

    def clear(self):
        self._text.clear()


class TerminalEdit(QPlainTextEdit):
    def __init__(self, terminal_widget, parent=None):
        super().__init__(parent)
        self._tw = terminal_widget
        self._font_size = 14
        self.setObjectName("terminalTextEdit")
        self.setUndoRedoEnabled(False)
        self.setMaximumBlockCount(10000)
        self._apply_font()

    def _apply_font(self) -> None:
        font = QFont("JetBrains Mono, Consolas, monospace", self._font_size)
        self.setFont(font)

    def _zoom_font(self, delta: int) -> None:
        self._font_size = max(6, self._font_size + delta)
        self._apply_font()

    def set_theme(self, bg: str, fg: str, sel: str) -> None:
        pass

    # ------------------------------------------------------------------
    # Input boundary enforcement (Step 4)
    #
    # The PromptX terminal has a protected prompt prefix at the start of
    # the document.  Users must not be able to insert, delete, or modify
    # text before ``_input_pos`` through *any* input channel — keyboard,
    # mouse paste, drag-and-drop, or context menu.  The following
    # overrides close every one of those escape routes.
    # ------------------------------------------------------------------

    def insertFromMimeData(self, source):
        """Intercept paste operations (Ctrl+V, Shift+Insert, etc.) to
        prevent insertion before the prompt boundary.

        If the cursor currently sits inside the protected prompt zone it
        is silently relocated to ``_input_pos`` before the base-class
        insertion proceeds, so the pasted text always lands in the
        editable region.
        """
        cursor = self.textCursor()
        if cursor.position() < self._tw._input_pos:
            cursor.setPosition(self._tw._input_pos)
            self.setTextCursor(cursor)
        super().insertFromMimeData(source)

    def dropEvent(self, event):
        """Reject drag-and-drop operations that target the protected
        prompt area.  Drops landing in the editable input zone are
        accepted normally.
        """
        drop_cursor = self.cursorForPosition(event.position().toPoint())
        if drop_cursor.position() < self._tw._input_pos:
            event.ignore()
            return
        # Also guard the *current* text cursor — if it somehow ended up
        # before the prompt, snap it forward before the base-class drop.
        if self.textCursor().position() < self._tw._input_pos:
            c = self.textCursor()
            c.setPosition(self._tw._input_pos)
            self.setTextCursor(c)
        super().dropEvent(event)

    def contextMenuEvent(self, event):
        """Provide a minimal, filtered context menu that never allows
        editing of the protected prompt zone.

        * Copy is always available when there is a selection.
        * Paste is only offered when the cursor is inside the editable
          input zone (at or after ``_input_pos``).
        * Cut and all other mutation actions are omitted entirely to
          prevent accidental prompt corruption.
        """
        cursor = self.textCursor()
        has_selection = cursor.hasSelection()

        menu = QMenu(self)

        copy_action = menu.addAction("Copy")
        copy_action.setEnabled(has_selection)
        if has_selection:
            copy_action.triggered.connect(self._ctx_copy)

        # Only offer paste when the insertion point is in the safe zone.
        if cursor.position() >= self._tw._input_pos:
            paste_action = menu.addAction("Paste")
            paste_action.triggered.connect(self._ctx_paste)

        if menu.actions():
            menu.exec(event.globalPos())
        else:
            event.ignore()

    def _ctx_copy(self):
        """Copy the current selection to the system clipboard."""
        text = self.textCursor().selectedText()
        if text:
            QApplication.clipboard().setText(text)

    def _ctx_paste(self):
        """Paste from the system clipboard into the editable input zone,
        never into the protected prompt region."""
        text = QApplication.clipboard().text()
        if text:
            cursor = self.textCursor()
            if cursor.position() < self._tw._input_pos:
                cursor.setPosition(self._tw._input_pos)
                self.setTextCursor(cursor)
            cursor.insertText(text)

    # ------------------------------------------------------------------
    # Keyboard handling
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        tw = self._tw
        cursor = self.textCursor()
        key = event.key()
        mods = event.modifiers()

        if key == Qt.Key.Key_Return and mods == Qt.KeyboardModifier.NoModifier:
            tw._execute_current()
            return

        if key == Qt.Key.Key_Up and mods == Qt.KeyboardModifier.NoModifier:
            tw._history_navigate(-1)
            return

        if key == Qt.Key.Key_Down and mods == Qt.KeyboardModifier.NoModifier:
            tw._history_navigate(1)
            return

        if key == Qt.Key.Key_Left:
            if cursor.position() > tw._input_pos:
                super().keyPressEvent(event)
            return

        if key == Qt.Key.Key_Right:
            if cursor.position() < self.document().characterCount() - 1:
                super().keyPressEvent(event)
            return

        if key == Qt.Key.Key_Home:
            c = self.textCursor()
            c.setPosition(tw._input_pos)
            self.setTextCursor(c)
            return

        if key == Qt.Key.Key_End:
            self.moveCursor(QTextCursor.MoveOperation.End)
            return

        if key == Qt.Key.Key_Backspace:
            if cursor.hasSelection():
                if (
                    cursor.selectionStart() < tw._input_pos
                    or cursor.selectionEnd() < tw._input_pos
                ):
                    return
            elif cursor.position() <= tw._input_pos:
                return
            super().keyPressEvent(event)
            return

        if key == Qt.Key.Key_Delete:
            if cursor.hasSelection():
                if (
                    cursor.selectionStart() < tw._input_pos
                    or cursor.selectionEnd() < tw._input_pos
                ):
                    return
            super().keyPressEvent(event)
            return

        if (
            key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal)
            and mods == Qt.KeyboardModifier.ControlModifier
        ):
            self._zoom_font(1)
            return

        if key == Qt.Key.Key_Minus and mods == Qt.KeyboardModifier.ControlModifier:
            self._zoom_font(-1)
            return

        if key == Qt.Key.Key_0 and mods == Qt.KeyboardModifier.ControlModifier:
            self._font_size = 14
            self._apply_font()
            return

        if key == Qt.Key.Key_A and mods == Qt.KeyboardModifier.ControlModifier:
            c = self.textCursor()
            c.setPosition(tw._input_pos)
            c.movePosition(
                QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor
            )
            self.setTextCursor(c)
            return

        if cursor.position() < tw._input_pos:
            c = self.textCursor()
            c.setPosition(tw._input_pos)
            self.setTextCursor(c)

        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        tw = self._tw
        cursor = self.textCursor()
        if cursor.position() < tw._input_pos or cursor.anchor() < tw._input_pos:
            c = self.textCursor()
            c.setPosition(tw._input_pos)
            self.setTextCursor(c)

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        tw = self._tw
        cursor = self.textCursor()
        if cursor.position() < tw._input_pos or cursor.anchor() < tw._input_pos:
            c = self.textCursor()
            c.setPosition(tw._input_pos)
            c.movePosition(
                QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor
            )
            self.setTextCursor(c)

    def wheelEvent(self, event):
        super().wheelEvent(event)


class PromptXTerminalWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = CommandLine(os.getcwd())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        self._terminal = TerminalEdit(self)
        layout.addWidget(self._terminal)

        self._highlighter = PromptXHighlighter(self._terminal.document())

        self._input_pos = 0
        self._saved_input = ""
        self._navigating_history = False

        self._terminal.insertPlainText(HELP)
        self._show_prompt()

    def _show_prompt(self) -> None:
        prompt = self._engine.prompt
        self._terminal.moveCursor(QTextCursor.MoveOperation.End)
        self._terminal.insertPlainText(prompt)
        self._input_pos = self._terminal.textCursor().position()

    def _get_input(self) -> str:
        cursor = self._terminal.textCursor()
        cursor.setPosition(self._input_pos)
        cursor.movePosition(
            QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor
        )
        return cursor.selectedText()

    def _replace_input(self, text: str) -> None:
        cursor = self._terminal.textCursor()
        cursor.setPosition(self._input_pos)
        cursor.movePosition(
            QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor
        )
        cursor.removeSelectedText()
        cursor.insertText(text)
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._terminal.setTextCursor(cursor)

    def _history_navigate(self, direction: int) -> None:
        if not self._navigating_history:
            self._saved_input = self._get_input()
            self._navigating_history = True

        if direction < 0:
            cmd = self._engine.get_previous_command()
        else:
            cmd = self._engine.get_next_command()
            if not cmd and self._navigating_history:
                cmd = self._saved_input
                self._navigating_history = False

        self._replace_input(cmd)

    def _execute_current(self) -> None:
        cmd = self._get_input()
        self._terminal.moveCursor(QTextCursor.MoveOperation.End)
        self._terminal.insertPlainText("\n")
        self._navigating_history = False
        stripped = cmd.strip()

        if stripped.lower() == "clear":
            self._terminal.clear()
            self._show_prompt()
            return

        if stripped.lower() == "quit":
            self._terminal.insertPlainText(
                "Use the close button to close the terminal panel.\n"
            )
            self._show_prompt()
            return

        result = self._engine.onecmd(cmd)
        if result is not None:
            self._terminal.insertPlainText(str(result) + "\n")
        self._show_prompt()

    def focus_input(self) -> None:
        self._terminal.setFocus()
        cursor = self._terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._terminal.setTextCursor(cursor)


class TerminalPanel(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("terminalPanel")
        self.setWindowTitle("Terminal Panel")

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(0)

        self.stack = QStackedWidget()

        self.system_shell_tab = TerminalWorkspace(self)
        self.promptXShell_tab = PromptXTerminalWidget(self)
        self.output_tab = OutputWidget(self)

        # Connecting the close button to the system shell emulator
        self.system_shell_tab.close_requested.connect(self.close_requested.emit)

        self.tabs = {
            TAB_SYSTEM_SHELL: (self.system_shell_tab, "TERMINAL"),
            TAB_PROMPTX: (self.promptXShell_tab, "PROMPTX"),
            TAB_OUTPUT: (self.output_tab, "OUTPUT"),
        }

        for tab_id in sorted(self.tabs.keys()):
            widget, _ = self.tabs[tab_id]
            self.stack.addWidget(widget)

        # Custom tab bar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(0)

        self.tab_bar = _TerminalTabBar(self)
        self.tab_bar.setObjectName("terminalTabBar")
        self.tab_bar.setExpanding(False)
        for tab_id in sorted(self.tabs.keys()):
            _, label = self.tabs[tab_id]
            self.tab_bar.addTab(label)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        toolbar.addWidget(self.tab_bar, 0)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("terminalCloseBtn")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.clicked.connect(self.close_requested.emit)
        toolbar.addWidget(self.btn_close)

        main_layout.addLayout(toolbar)
        main_layout.addWidget(self.stack)

        self.switch_tab(TAB_SYSTEM_SHELL)

    def _on_tab_changed(self, index):
        if index < 0 or index >= self.stack.count():
            return
        self.stack.setCurrentIndex(index)

        if index == TAB_PROMPTX:
            self.promptXShell_tab.focus_input()

    def switch_tab(self, index):
        if index < 0 or index >= self.tab_bar.count():
            return
        self.tab_bar.setCurrentIndex(index)

    def count(self):
        return self.stack.count()

    def widget(self, index):
        return self.stack.widget(index)

    def set_theme(self, bg: str, fg: str, sel: str) -> None:
        self.system_shell_tab.set_theme(bg, fg, sel)

    def retheme(self, t) -> None:
        pass

    def append_output(self, text):
        self.output_tab.append_text(text)

    # ------------------------------------------------------------------
    # Cleanup (Step 7)
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Aggressively terminate every terminal session managed by this
        panel.  Called from application-lifetime hooks to guarantee no
        orphaned PTY descriptors or zombie child processes survive an
        IDE shutdown.
        """
        self.system_shell_tab.cleanup()

    def closeEvent(self, event) -> None:
        """Intercept close to prevent widget destruction; the workspace is
        toggled visible/hidden by the parent splitter.  Cleanup is
        handled separately through application lifetime hooks.
        """
        event.ignore()
