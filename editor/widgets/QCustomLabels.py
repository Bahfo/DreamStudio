"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved
Developed and Maintained Mainly by DreamStudio Maintainers and Contributors, and
Supervised by EXcellent TechStacks Co.

Custom Widgets for DreamStudio: Animated Label with Gradient Colors.
- Used primarily for Welcoming the Developer when he enters EtherAI.
"""

# Written By Bahaa Nofal 2026

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty

from fonts.font_strapper import Fonts
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QFont


class AnimatedGradientLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._gradient_offset = 0.0
        self.setStyleSheet("background-color: transparent;")

        self.setFont(Fonts.inter(24))
        self.setFixedHeight(60)

        # Animation setup
        self.animation = QPropertyAnimation(self, b"gradient_offset")
        self.animation.setDuration(2000)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setLoopCount(4)

    @pyqtProperty(float)
    def gradient_offset(self):
        return self._gradient_offset

    @gradient_offset.setter
    def gradient_offset(self, value):
        self._gradient_offset = value
        self.update()

    def start_animation(self):
        if self.animation.state() != QPropertyAnimation.State.Running:
            self.animation.start()

    def stop_animation(self):
        if self.animation.state() == QPropertyAnimation.State.Running:
            self.animation.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        gradient = QLinearGradient(-self.width(), 0, self.width() * 2, 0)

        c1 = QColor("#FDC830")
        c2 = QColor("#F37335")
        c3 = QColor("#FF5289")
        c4 = QColor("#7367F0")

        o = self._gradient_offset

        gradient.setColorAt((0.0 + o) % 1.0, c1)
        gradient.setColorAt((0.25 + o) % 1.0, c2)
        gradient.setColorAt((0.5 + o) % 1.0, c3)
        gradient.setColorAt((0.75 + o) % 1.0, c4)
        gradient.setColorAt((1.0 + o) % 1.0, c1)

        from PyQt6.QtGui import QPen, QBrush

        pen = QPen()
        pen.setBrush(QBrush(gradient))
        painter.setPen(pen)

        painter.setFont(self.font())
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.text(),
        )
