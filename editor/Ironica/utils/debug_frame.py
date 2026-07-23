from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StackInfoFrame(QFrame):
    """
    An inline container widget with a red border to display breakpoint
    stack info.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet("""
            StackInfoFrame {
                border: 2px solid #E53935;
                border-radius: 6px;
                background-color: #1E1E1E;
            }
            QLabel {
                color: #D4D4D4;
                font-family: Consolas, "Fira Code", monospace;
                font-size: 12px;
                border: none;
            }
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 6, 10, 6)

        self.title_label = QLabel("<b>Stack Context</b> (Paused)", self)
        self.title_label.setTextFormat(Qt.TextFormat.RichText)

        self.content_label = QLabel("Line frame info goes here...", self)

        self._layout.addWidget(self.title_label)
        self._layout.addWidget(self.content_label)
