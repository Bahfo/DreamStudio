from PyQt6.QtCore import QPropertyAnimation, QVariantAnimation, Qt, QRect, QPoint, QSize
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QBrush
from PyQt6.QtWidgets import QWidget


class SplashOverlay(QWidget):
    def __init__(self, parent, color=QColor(255, 255, 255, 150)):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.color = color
        self.offset = -1.0

        self.resize(parent.size())
        self.raise_()  # ensure it's above

        parent.installEventFilter(self)

        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(-1.0)
        self.anim.setEndValue(2.0)
        self.anim.setDuration(800)
        self.anim.valueChanged.connect(self._update_sweep)
        self.anim.finished.connect(self.deleteLater)
        self.anim.start()

    def eventFilter(self, obj, event):
        if obj is self.parent() and event.type() == event.Type.Resize:
            self.resize(obj.size())
        return super().eventFilter(obj, event)

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