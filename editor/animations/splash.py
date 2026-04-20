from PyQt6.QtCore import QPropertyAnimation, QVariantAnimation, Qt, QRect, QPoint, QSize
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QBrush
from PyQt6.QtWidgets import QWidget


class SplashOverlay(QWidget):
    def __init__(self, parent, color=QColor(255, 255, 255, 150)):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.color = color
        self.offset = -1.0

        self.setGeometry(parent.rect())

        # Animation Setup
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(-1.0)
        self.anim.setEndValue(2.0)
        self.anim.setDuration(800)  # 0.8 seconds
        self.anim.valueChanged.connect(self._update_sweep)
        self.anim.finished.connect(self.deleteLater)
        self.anim.start()

    def _update_sweep(self, value):
        self.offset = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, self.width(), self.height())

        stop_pos = self.offset

        gradient.setColorAt(max(0, min(1, stop_pos - 0.2)), QColor(0, 0, 0, 0))
        gradient.setColorAt(max(0, min(1, stop_pos)), self.color)
        gradient.setColorAt(max(0, min(1, stop_pos + 0.2)), QColor(0, 0, 0, 0))

        painter.fillRect(self.rect(), QBrush(gradient))
