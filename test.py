import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QScrollBar
from PyQt6.QtCore import Qt

from termqt import Terminal, TerminalPOSIXExecIO


class TerminalWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("termqt example")
        self.resize(800, 500)

        layout = QVBoxLayout(self)

        # Terminal widget
        self.terminal = Terminal(800, 500)
        self.terminal.set_font()
        self.terminal.maximum_line_history = 1000

        # Scrollbar (optional but recommended)
        self.scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self.terminal.connect_scroll_bar(self.scrollbar)

        layout.addWidget(self.terminal)
        layout.addWidget(self.scrollbar)

        # Backend (Linux/macOS)
        self.io = TerminalPOSIXExecIO(
            self.terminal.row_len, self.terminal.col_len, "/bin/bash"
        )

        # Required connections
        self.io.stdout_callback = self.terminal.stdout
        self.terminal.stdin_callback = self.io.write
        self.terminal.resize_callback = self.io.resize

        # Start shell
        self.io.spawn()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TerminalWindow()
    window.show()
    sys.exit(app.exec())
