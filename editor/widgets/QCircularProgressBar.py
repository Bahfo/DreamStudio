from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtWidgets import QWidget


class CircularProgressBar(QWidget):
    def __init__(
        self,
        bg_color: QColor,
        fg_color: QColor,
        parent=None,
        diameter=25,
    ):
        super().__init__(parent)

        self.value = 0
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.setMinimumSize(diameter)

    def set_value(self, value):
        self.value = value
        self.update()  # Triggering paint event

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 15
        rect = QRectF(
            margin, margin, self.width() - margin * 2, self.height() - margin * 2
        )

        track_pen = QPen(self.bg_color, 15)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        progress_pen = QPen(self.fg_color, 15)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)

        start_angle = 90 * 16
        span_angle = int(-self.value * 3.6 * 16)
        painter.drawArc(rect, start_angle, span_angle)
