"""
(C) COPYRIGHT 2026 EXCELLENT TECHNOLGOIES

Custom Widgets for DreamStudio: Animated Label with Gradient Colors.
- Used primarily for Welcoming the Developer when he enters EtherAI.
"""

# Written By Bahaa Nofal 2026

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QFont


class AnimatedGradientLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._gradient_offset = 0.0

        self.setFont(QFont("inter", 28, QFont.Weight.Bold))
        self.setFixedHeight(60)

        # Animation setup
        self.animation = QPropertyAnimation(self, b"gradient_offset")
        self.animation.setDuration(3000)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setLoopCount(-1)
        self.animation.start()

    @pyqtProperty(float)
    def gradient_offset(self):
        return self._gradient_offset

    @gradient_offset.setter
    def gradient_offset(self, value):
        self._gradient_offset = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Essential for smooth color blending
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        gradient = QLinearGradient(-self.width(), 0, self.width() * 2, 0)

        # Denser color map for smoother transitions
        # Using more stops helps the 'middle' colors blend better
        c1 = QColor("#4285F4")  # Google Blue
        c2 = QColor("#9b59b6")  # Deep Purple
        c3 = QColor("#e91e63")  # Vivid Pink
        c4 = QColor("#34A853")  # Google Green (for extra spectrum)

        # Calculate offset
        o = self._gradient_offset

        # Mapping colors so they "slide" across the text
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


class CustomTooltip(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent, flags=Qt.WindowType.ToolTip)
        self.setStyleSheet(
            """
            QLabel {
                color: #e0e0e0;
                background-color: #1e1e1e;
                border: 1px solid #555;
                padding: 6px 10px;
                border-radius: 6px;
                font-family: "JetBrains Mono";
                font-size: 12px;
            }
        """
        )
        self.hide()
