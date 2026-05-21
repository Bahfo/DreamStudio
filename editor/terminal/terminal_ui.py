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
    QTextEdit,
)
from PyQt6.QtGui import QFont, QColor, QTextCursor, QPalette
from PyQt6.QtCore import pyqtSignal, Qt

from editor.lsp.runner import ProcessRunner

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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and not event.modifiers():
            text = self._input.toPlainText().strip()
            self._input.clear()
            if text:
                self.run_shell_command(text)
            return
        super().keyPressEvent(event)

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
        self.promptXShell_tab = QWidget()
        self.debug_tab = QWidget()
        self.output_tab = OutputWidget(self)

        self.tabs = {
            TAB_PROBLEMS: (self.problems_tab, "PROBLEMS"),
            TAB_TERMINAL: (self.terminal_tab, "TERMINAL"),
            TAB_PROMPTX: (self.promptXShell_tab, "PROMPTX"),
            TAB_DEBUG: (self.debug_tab, "DEBUG"),
            TAB_OUTPUT: (self.output_tab, "OUTPUT"),
        }

        for i in range(5):
            widget, _ = self.tabs[i]
            self.stack.addWidget(widget)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 5, 10, 5)

        self.buttons = {}

        for i in range(5):
            _, label = self.tabs[i]
            btn = QPushButton(label)
            btn.setFont(QFont("Inter", 9, QFont.Weight.Bold))
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, idx=i: self.switch_tab(idx))
            toolbar.addWidget(btn)
            self.buttons[i] = btn

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
