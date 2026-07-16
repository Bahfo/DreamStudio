from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QPainterPath, QPen
from PyQt6.QtCore import Qt


class GradientBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(140)
        self._dark_mode = False

    def set_dark_mode(self, enabled: bool):
        self._dark_mode = enabled
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        painter.setPen(Qt.PenStyle.NoPen)

        if not self._dark_mode:
            top_grad = QLinearGradient(0, 0, w, 0)
            top_grad.setColorAt(0.0, QColor("#70A5BE"))
            top_grad.setColorAt(1.0, QColor("#5496E5"))
            painter.fillRect(0, 0, w, h, top_grad)

            path = QPainterPath()
            path.moveTo(0, h)
            path.lineTo(0, h * 0.75)
            path.cubicTo(w * 0.25, h * 0.2, w * 0.75, h * 1.1, w, h * 0.6)
            path.lineTo(w, h)
            path.closeSubpath()

            bottom_grad = QLinearGradient(0, 0, w, 0)
            bottom_grad.setColorAt(0.0, QColor("#004A94"))
            bottom_grad.setColorAt(1.0, QColor("#003A9F"))
            painter.fillPath(path, bottom_grad)

            pen = QPen(QColor("#5AFFFFFF"))
            pen.setWidth(1)
            pen.setStyle(Qt.PenStyle.DotLine)
            painter.setPen(pen)

        else:
            top_grad_dark = QLinearGradient(0, 0, w, 0)
            top_grad_dark.setColorAt(0.0, QColor("#191E2D"))
            top_grad_dark.setColorAt(1.0, QColor("#003453"))
            painter.fillRect(0, 0, w, h, top_grad_dark)

            path_dark = QPainterPath()
            path_dark.moveTo(0, h)
            path_dark.lineTo(0, h * 0.75)
            path_dark.cubicTo(w * 0.25, h * 0.2, w * 0.75, h * 1.1, w, h * 0.6)
            path_dark.lineTo(w, h)
            path_dark.closeSubpath()

            bottom_grad_dark = QLinearGradient(0, 0, w, 0)
            bottom_grad_dark.setColorAt(0.0, QColor("#003A81"))
            bottom_grad_dark.setColorAt(1.0, QColor("#081C45"))
            painter.fillPath(path_dark, bottom_grad_dark)

            pen_dark = QPen(QColor("#5A96BEFF"))
            pen_dark.setWidth(1)
            pen_dark.setStyle(Qt.PenStyle.DotLine)
            painter.setPen(pen_dark)

            painter.setPen(QColor("#334155"))
            painter.drawLine(0, h - 1, w, h - 1)
