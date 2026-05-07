import sys

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QFont,
    QBrush,
    QPainterPath,
)
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
)


################## BASE INTERACTIVE BUTTON ##################
class InteractiveButton(QWidget):

    pressed_signal = pyqtSignal(str)
    released_signal = pyqtSignal(str)

    def __init__(self, name, parent=None):
        super().__init__(parent)

        self.name = name
        self.is_pressed = False

        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        self.is_pressed = True
        self.update()

        self.pressed_signal.emit(self.name)

    def mouseReleaseEvent(self, event):
        self.is_pressed = False
        self.update()

        self.released_signal.emit(self.name)


################## ROUND BUTTON ##################
class RoundButton(InteractiveButton):

    def __init__(self, text, parent=None):
        super().__init__(text, parent)

        self.text = text

        self.setFixedSize(70, 70)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        outer_color = "#E0AA00" if self.is_pressed else "#FFD22E"

        painter.setPen(QPen(QColor("#C96F00"), 3))
        painter.setBrush(QBrush(QColor(outer_color)))

        painter.drawEllipse(rect)

        inner_rect = rect.adjusted(22, 22, -22, -22)

        painter.setBrush(QBrush(QColor("#EAEAEA")))
        painter.drawEllipse(inner_rect)

        painter.setPen(QPen(QColor("#B08A00"), 2))

        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text)


################## DPAD BUTTON ##################
class DPadButton(InteractiveButton):

    def __init__(self, direction, parent=None):
        super().__init__(direction, parent)

        self.direction = direction

        self.setFixedSize(50, 50)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        color = "#DFA900" if self.is_pressed else "#F5D94A"

        painter.setPen(QPen(QColor("#C68D00"), 3))
        painter.setBrush(QBrush(QColor(color)))

        painter.drawRoundedRect(rect, 18, 18)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("white")))

        center = rect.center()

        arrow = QPainterPath()

        if self.direction == "UP":
            arrow.moveTo(center.x(), center.y() - 12)
            arrow.lineTo(center.x() - 10, center.y() + 8)
            arrow.lineTo(center.x() + 10, center.y() + 8)

        elif self.direction == "DOWN":
            arrow.moveTo(center.x(), center.y() + 12)
            arrow.lineTo(center.x() - 10, center.y() - 8)
            arrow.lineTo(center.x() + 10, center.y() - 8)

        elif self.direction == "LEFT":
            arrow.moveTo(center.x() - 12, center.y())
            arrow.lineTo(center.x() + 8, center.y() - 10)
            arrow.lineTo(center.x() + 8, center.y() + 10)

        elif self.direction == "RIGHT":
            arrow.moveTo(center.x() + 12, center.y())
            arrow.lineTo(center.x() - 8, center.y() - 10)
            arrow.lineTo(center.x() - 8, center.y() + 10)

        arrow.closeSubpath()

        painter.drawPath(arrow)


################## MAIN DEVICE SHELL ##################
class EXConsole_Titanium_512(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("EXConsole - Titanium 512")

        self.resize(940, 700)

        self.setup_buttons()

    # BUTTON SETUP
    def setup_buttons(self):

        # A BUTTON
        self.btn_a = RoundButton("A", self)

        self.btn_a.move(600, 520)

        self.btn_a.pressed_signal.connect(self.on_pressed)
        self.btn_a.released_signal.connect(self.on_released)

        # B BUTTON
        self.btn_b = RoundButton("B", self)

        self.btn_b.move(500, 520)

        self.btn_b.pressed_signal.connect(self.on_pressed)
        self.btn_b.released_signal.connect(self.on_released)

        # DPAD
        self.btn_up = DPadButton("UP", self)
        self.btn_down = DPadButton("DOWN", self)
        self.btn_left = DPadButton("LEFT", self)
        self.btn_right = DPadButton("RIGHT", self)

        base_x = 170
        base_y = 500

        self.btn_up.move(base_x + 50, base_y - 50)
        self.btn_down.move(base_x + 50, base_y + 50)
        self.btn_left.move(base_x, base_y)
        self.btn_right.move(base_x + 100, base_y)

        for btn in [self.btn_up, self.btn_down, self.btn_left, self.btn_right]:
            btn.pressed_signal.connect(self.on_pressed)
            btn.released_signal.connect(self.on_released)

    # SIGNAL CALLBACKS
    def on_pressed(self, name):
        print(f"{name} PRESSED")

    def on_released(self, name):
        print(f"{name} RELEASED")

    # PAINT DEVICE
    def paintEvent(self, event):

        painter = QPainter(self)
        rect = self.rect()

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # BACKGROUND
        painter.fillRect(self.rect(), QColor("#2D2D2D"))

        # DEVICE BODY
        body_rect = QRectF(50, 40, w - 140, h - 120)

        painter.setPen(QPen(QColor("#D69E00"), 4))
        painter.setBrush(QBrush(QColor("#F4C62B")))

        painter.drawRoundedRect(body_rect, 40, 40)

        # SCREEN FRAME
        screen_frame = QRectF(150, 80, 600, 350)

        painter.setPen(QPen(QColor("black"), 3))
        painter.setBrush(QBrush(QColor("black")))

        painter.drawRoundedRect(screen_frame, 25, 25)

        # SCREEN
        screen = QRectF(180, 110, 540, 290)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#132B36")))

        painter.drawRect(screen)

        # SCREWS
        screws = [
            (80, 80),
            (820, 80),
            (80, 580),
            (820, 580),
        ]

        for x, y in screws:

            painter.setPen(QPen(QColor("#555"), 3))
            painter.setBrush(QBrush(QColor("#7D94A6")))

            painter.drawEllipse(QPointF(x, y), 18, 18)

            painter.setPen(QPen(QColor("#333"), 2))

            painter.drawLine(x - 6, y + 6, x + 6, y - 6)

        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        font.setItalic(True)

        painter.setFont(font)
        painter.setPen(QColor("red"))
        painter.drawText(510, 480, "EX Titanium")


app = QApplication(sys.argv)

window = EXConsole_Titanium_512()
window.show()

sys.exit(app.exec())
