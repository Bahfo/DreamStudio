from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPlainTextEdit,
)
from PyQt6.QtGui import QTextCursor


class ProblemsWidget(QWidget):
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
