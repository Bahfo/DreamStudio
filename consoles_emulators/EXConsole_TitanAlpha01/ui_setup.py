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


class BaseButton(QWidget):
    """
    The base button that builds other complex console buttons.
    """

    pressed_signal = pyqtSignal(str)
    released_signal = pyqtSignal(str)

    def __init__(self, name, parent=None):
        super().__init__(parent)

        self.name = name
        self.is_pressed = None
        self.setMouseTracking(True)

    def mousePressEvent(self, a0):
        self.is_pressed = True
        self.update()
        self.pressed_signal.emit(self.name)

    def mouseReleaseEvent(self, a0):
        self.is_pressed = False
        self.update()
        self.released_signal.emit(self.name)


class RoundButton(BaseButton):
    def __init__(self, text, size_x, size_y, parent=None):
        super().__init__(text, parent)

        self.text = text
        self.setFixedSize(size_x, size_y)

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        outer_color = "#00E04E" if self.is_pressed else "#2EFF7E"

        painter.setPen(QPen(QColor("#00C914"), 3))
        painter.setBrush(QBrush(QColor(outer_color)))

        size = min(rect.width(), rect.height())

        circle_rect = QRectF(
            (rect.width() - size) / 2, (rect.height() - size) / 2, size, size
        )

        painter.drawEllipse(circle_rect)

        painter.setPen(QPen(QColor("#06B000"), 2))

        font = QFont()
        font.setPointSize(18)
        font.setBold(True)

        painter.setFont(font)

        painter.setPen(QColor("black"))

        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text)


class DPadButton(BaseButton):

    def __init__(self, direction, parent=None):
        super().__init__(direction, parent)

        self.direction = direction

        self.setFixedSize(40, 40)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        color = "#353535" if self.is_pressed else "#474747"

        painter.setPen(QPen(QColor("#222222"), 3))
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


class JoystickWidget(QWidget):

    moved_signal = pyqtSignal(float, float)
    released_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedSize(160, 160)

        self.knob_radius = 28
        self.base_radius = 50

        self.center_x = self.width() / 2
        self.center_y = self.height() / 2

        self.knob_x = self.center_x
        self.knob_y = self.center_y

        self.dragging = False

    def mousePressEvent(self, event):
        self.dragging = True
        self.update_knob(event.position())

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.update_knob(event.position())

    def mouseReleaseEvent(self, event):

        self.dragging = False

        self.knob_x = self.center_x
        self.knob_y = self.center_y

        self.update()

        self.released_signal.emit()

    def update_knob(self, pos):

        dx = pos.x() - self.center_x
        dy = pos.y() - self.center_y

        distance = (dx**2 + dy**2) ** 0.5

        max_distance = self.base_radius - self.knob_radius

        if distance > max_distance:
            scale = max_distance / distance

            dx *= scale
            dy *= scale

        self.knob_x = self.center_x + dx
        self.knob_y = self.center_y + dy

        norm_x = dx / max_distance
        norm_y = dy / max_distance

        self.moved_signal.emit(norm_x, norm_y)

        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # BASE
        painter.setPen(QPen(QColor("#1E1E1E"), 4))
        painter.setBrush(QBrush(QColor("#2E2E2E")))

        painter.drawEllipse(
            QPointF(self.center_x, self.center_y), self.base_radius, self.base_radius
        )

        # INNER RING
        painter.setPen(QPen(QColor("#282828"), 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawEllipse(QPointF(self.center_x, self.center_y), 45, 45)

        # KNOB
        painter.setPen(QPen(QColor("#666"), 3))
        painter.setBrush(QBrush(QColor("#DDDDDD")))

        painter.drawEllipse(
            QPointF(self.knob_x, self.knob_y), self.knob_radius, self.knob_radius
        )


class EXConsole_TitanAlpha01(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EXConsole - TitanAlpha 01")
        self.resize(1200, 600)

        self.setup_buttons()

    def setup_buttons(self):

        # UP-DOWN-LEFT-RIGHT Buttons
        self.btn_up = DPadButton("UP", self)
        self.btn_down = DPadButton("DOWN", self)
        self.btn_left = DPadButton("LEFT", self)
        self.btn_right = DPadButton("RIGHT", self)

        pad_base_x = 70
        pad_base_y = 70

        self.btn_up.move(pad_base_x + 40, pad_base_y)
        self.btn_down.move(pad_base_x + 40, pad_base_y + 80)
        self.btn_left.move(pad_base_x, pad_base_y + 40)
        self.btn_right.move(pad_base_x + 80, pad_base_y + 40)

        for btn in [self.btn_up, self.btn_down, self.btn_left, self.btn_right]:
            btn.pressed_signal.connect(self.on_pressed)
            btn.released_signal.connect(self.on_released)

        # X-Y-A-B Button
        self.x_button = RoundButton("X", 40, 40, self)
        self.y_button = RoundButton("Y", 40, 40, self)
        self.a_button = RoundButton("A", 40, 40, self)
        self.b_button = RoundButton("B", 40, 40, self)

        base_x = 965
        base_y = 60

        self.x_button.move(base_x + 40, base_y)
        self.y_button.move(base_x, base_y + 40)
        self.a_button.move(base_x + 80, base_y + 40)
        self.b_button.move(base_x + 40, base_y + 80)

        for btn in [self.x_button, self.y_button, self.a_button, self.b_button]:
            btn.pressed_signal.connect(self.on_pressed)
            btn.released_signal.connect(self.on_released)

        # Joysticks
        self.leftJoyStick = JoystickWidget(self)
        self.leftJoyStick.move(50, 350)

        self.rightJoyStick = JoystickWidget(self)
        self.rightJoyStick.move(950, 350)

    def on_pressed(self, name):
        print(f"{name} PRESSED")

    def on_released(self, name):
        print(f"{name} RELEASED")

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # BACKGROUND
        painter.fillRect(self.rect(), QColor("#2D2D2D"))

        # DEVICE BODY
        body_rect = QRectF(50, 40, w - 140, h - 120)

        painter.setPen(QPen(QColor("#32D600"), 4))
        painter.setBrush(QBrush(QColor("#61F42B")))

        painter.drawRoundedRect(body_rect, 40, 40)

        # SCREEN FRAME
        screen_frame = QRectF(210, 70, 730, 415)

        painter.setPen(QPen(QColor("black"), 3))
        painter.setBrush(QBrush(QColor("black")))

        painter.drawRoundedRect(screen_frame, 25, 25)

        # SCREEN
        screen = QRectF(230, 90, 690, 375)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#132B36")))

        painter.drawRect(screen)


app = QApplication(sys.argv)

window = EXConsole_TitanAlpha01()
window.show()

sys.exit(app.exec())
