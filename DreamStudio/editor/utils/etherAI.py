from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QFrame,
    QLabel,
)
from PyQt6.QtGui import QIcon

from editor.widgets.QCustomLabels import AnimatedGradientLabel


class EtherAIMainScreen(QFrame):
    def __init__(self, master=None):
        super().__init__(master)

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background-color: #121212;")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(40, 40, 40, 40)
        self._layout.setSpacing(10)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._load_welcome_message()

        sub_text = QLabel("What can I help you build today?")
        sub_text.setStyleSheet(
            "color: #9aa0a6; font-size: 18px; font-family: 'Segoe UI';"
        )
        self._layout.addWidget(sub_text)

    def _load_welcome_message(self):
        self.welcome_message = AnimatedGradientLabel("Hi, DreamStudio Developer", self)
        self._layout.addWidget(self.welcome_message)
