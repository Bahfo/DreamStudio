import os
import sys
import logging

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QStackedWidget,
    QPlainTextEdit,
)
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtCore import pyqtSignal, Qt, QEvent

from editor.lsp.runner import ProcessRunner
from editor.terminal.PromptXEngine import CommandLine, HELP

logger = logging.getLogger(__name__)

TAB_PROBLEMS = 0
TAB_TERMINAL = 1
TAB_PROMPTX = 2
TAB_DEBUG = 3
TAB_OUTPUT = 4


class TerminalWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._runner = ProcessRunner(self)
        self._runner.output_received.connect(self._on_output)
        self._runner.error_received.connect(self._on_error)
        self._runner.process_finished.connect(self._on_finished)
        self._runner.process_errored.connect(self._on_runner_error)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._output = QPlainTextEdit(self)
        self._output.setReadOnly(True)
        self._output.setUndoRedoEnabled(False)
        self._output.setMaximumBlockCount(10000)
        self._output.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                font-family: "JetBrains Mono", "Consolas", monospace;
                font-size: 12px;
                selection-background-color: #264f78;
            }
        """)

        self._input = QPlainTextEdit(self)
        self._input.setMaximumBlockCount(1)
        self._input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._input.setFixedHeight(28)
        self._input.setPlaceholderText("Enter command...")
        self._input.setStyleSheet("""
            QPlainTextEdit {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                font-family: "JetBrains Mono", "Consolas", monospace;
                font-size: 12px;
                selection-background-color: #264f78;
            }
        """)
        self._input.installEventFilter(self)

        layout.addWidget(self._output, stretch=1)
        layout.addWidget(self._input)

        self._buffer = ""

    def _on_output(self, text):
        self._output.moveCursor(QTextCursor.MoveOperation.End)
        self._output.insertPlainText(text)
        self._output.moveCursor(QTextCursor.MoveOperation.End)

    def _on_error(self, text):
        self._output.moveCursor(QTextCursor.MoveOperation.End)
        self._output.insertPlainText(text)
        self._output.moveCursor(QTextCursor.MoveOperation.End)

    def _on_finished(self, returncode, reason):
        if reason == "TIMEOUT":
            self._output.appendPlainText("\n[Process timed out]")
        elif reason == "CANCELLED":
            self._output.appendPlainText("\n[Process cancelled]")
        else:
            self._output.appendPlainText(f"\n[Process exited with code {returncode}]")
        self._output.moveCursor(QTextCursor.MoveOperation.End)

    def _on_runner_error(self, error):
        self._output.appendPlainText(f"\n[Error: {error}]")
        self._output.moveCursor(QTextCursor.MoveOperation.End)

    def run_command(self, cmd, cwd=None):
        self._output.appendPlainText(f"$ {' '.join(cmd)}\n")
        self._output.moveCursor(QTextCursor.MoveOperation.End)
        self._runner.configure(cmd=cmd, cwd=cwd or os.getcwd())
        self._runner.start()

    def run_shell_command(self, command_text, cwd=None):
        shell = "powershell.exe" if sys.platform == "win32" else "bash"
        flag = "-c"
        self.run_command([shell, flag, command_text], cwd)

    def eventFilter(self, obj, event):
        if obj is self._input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not event.modifiers():
                text = self._input.toPlainText().strip()
                self._input.clear()
                if text:
                    self.run_shell_command(text)
                return True
        return super().eventFilter(obj, event)

    def stop(self):
        if self._runner.is_running():
            self._runner.stop()


class OutputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._text = QPlainTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(10000)
        self._text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                font-family: "JetBrains Mono", "Consolas", monospace;
                font-size: 12px;
            }
        """)
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
        self._bg = "#1e1e1e"
        self._fg = "#d4d4d4"
        self._sel = "#264f78"
        self.setUndoRedoEnabled(False)
        self.setMaximumBlockCount(10000)
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self._bg};
                color: {self._fg};
                border: none;
                font-family: "JetBrains Mono", "Consolas", "monospace";
                font-size: {self._font_size}px;
                selection-background-color: {self._sel};
            }}
        """)

    def _zoom_font(self, delta: int) -> None:
        self._font_size = max(6, self._font_size + delta)
        self._apply_style()

    def set_theme(self, bg: str, fg: str, sel: str) -> None:
        self._bg = bg
        self._fg = fg
        self._sel = sel
        self._apply_style()

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

        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal) and mods == Qt.KeyboardModifier.ControlModifier:
            self._zoom_font(1)
            return

        if key == Qt.Key.Key_Minus and mods == Qt.KeyboardModifier.ControlModifier:
            self._zoom_font(-1)
            return

        if key == Qt.Key.Key_0 and mods == Qt.KeyboardModifier.ControlModifier:
            self._font_size = 14
            self._apply_style()
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

    def contextMenuEvent(self, event):
        event.ignore()

    def wheelEvent(self, event):
        super().wheelEvent(event)


class PromptXTerminalWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = CommandLine(os.getcwd())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._terminal = TerminalEdit(self)
        layout.addWidget(self._terminal)

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

        self.setStyleSheet("""
            QWidget#terminalPanel {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-radius: 3px;
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(0)

        self.stack = QStackedWidget()

        self.problems_tab = QWidget()
        self.terminal_tab = TerminalWidget(self)
        self.promptXShell_tab = PromptXTerminalWidget(self)
        self.debug_tab = QWidget()
        self.output_tab = OutputWidget(self)

        self.tabs = {
            TAB_PROBLEMS: (self.problems_tab, "PROBLEMS"),
            TAB_TERMINAL: (self.terminal_tab, "TERMINAL"),
            TAB_PROMPTX: (self.promptXShell_tab, "PROMPTX"),
            TAB_DEBUG: (self.debug_tab, "DEBUG"),
            TAB_OUTPUT: (self.output_tab, "OUTPUT"),
        }

        for tab_id in range(len(self.tabs)):
            widget, _ = self.tabs[tab_id]
            self.stack.addWidget(widget)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 5, 10, 5)

        self.buttons = {}

        for tab_id in range(len(self.tabs)):
            _, label = self.tabs[tab_id]
            btn = QPushButton(label)
            btn.setFont(QFont("Inter", 9, QFont.Weight.Bold))
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, idx=tab_id: self.switch_tab(idx))
            toolbar.addWidget(btn)
            self.buttons[tab_id] = btn

        toolbar.addItem(
            QSpacerItem(
                40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.clicked.connect(self.close_requested.emit)
        toolbar.addWidget(self.btn_close)

        main_layout.addLayout(toolbar)
        main_layout.addWidget(self.stack)

        self.switch_tab(TAB_TERMINAL)

    def switch_tab(self, index):
        if index < 0 or index >= self.stack.count():
            return
        self.stack.setCurrentIndex(index)

        for i, btn in self.buttons.items():
            if i == index:
                btn.setStyleSheet("color: #007acc; border-bottom: 2px solid #007acc;")
                btn.setFixedWidth(90)
            else:
                btn.setStyleSheet("color: #cccccc; border-bottom: none;")
                btn.setFixedWidth(90)

        if index == TAB_PROMPTX:
            self.promptXShell_tab.focus_input()

    def retheme(self, t) -> None:
        bg = t.color("terminal.background")
        txt = t.color("terminal.text")
        input_bg = t.color("terminal.input_bg")
        input_border = t.color("terminal.input_border")
        sel = t.color("terminal.selection")
        self.setStyleSheet(f"""
            QWidget#terminalPanel {{
                background-color: {bg};
                color: {txt};
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                padding: 5px;
                color: {txt};
            }}
            QPushButton:hover {{
                background-color: {t.color("button.hover")};
                border-radius: 3px;
            }}
        """)
        self.terminal_tab._output.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {bg};
                color: {txt};
                border: none;
                font-family: "JetBrains Mono", "Consolas", monospace;
                font-size: 12px;
                selection-background-color: {sel};
            }}
        """)
        self.terminal_tab._input.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {input_bg};
                color: {txt};
                border: 1px solid {input_border};
                font-family: "JetBrains Mono", "Consolas", monospace;
                font-size: 12px;
                selection-background-color: {sel};
            }}
        """)
        self.promptXShell_tab._terminal.set_theme(bg, txt, sel)
        self.output_tab._text.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {bg};
                color: {txt};
                border: none;
                font-family: "JetBrains Mono", "Consolas", monospace;
                font-size: 12px;
            }}
        """)
        self.switch_tab(self.stack.currentIndex())

    def append_output(self, text):
        self.output_tab.append_text(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TerminalPanel()
    w.show()
    sys.exit(app.exec())
