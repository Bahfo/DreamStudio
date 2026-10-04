from editor import *


class QErrorMessage(QWidget):
    """
    A guided tooltip-style message that appears in fixed positions.

    Can be used within problems diagnosis to show description of an exception or
    error, or within notifications popup.
    """

    BORDER_RADIUS = 6
    ARROW_HEIGHT = 8

    def __init__(self, message: str, parent=None):
        super().__init__(parent)

        self.message = message
        self._arrow_x = 40

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(60)
        self.setMinimumWidth(400)

    def set_message(self, message: str) -> None:
        self._message = message
        self.update()

    def set_arrow_x_position(self, x: int) -> None:
        self._arrow_x = max(
            self.BORDER_RADIUS + 6,
            min(x, self.width() - self.BORDER_RADIUS - 6),
        )
        self.update()

    def sizeHint(self):
        return QSize(420, 64)

    def paintEvent(self, a0):
        arrow_width = 12
        arrow_path = QPainterPath()

        painter = QPainter()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        body_rect = QRectF(
            0,
            self.ARROW_HEIGHT,
            self.width(),
            self.height() - self.ARROW_HEIGHT,
        )

        body_path = QPainterPath()
        body_path.addRoundedRect(
            body_rect,
            self.BORDER_RADIUS,
            self.BORDER_RADIUS,
        )

        arrow_left = self._arrow_x - arrow_width / 2
        arrow_right = self._arrow_x + arrow_width / 2

        arrow_path.moveTo(arrow_left, self.ARROW_HEIGHT)
        arrow_path.lineTo(self._arrow_x, 0)
        arrow_path.lineTo(arrow_right, self.ARROW_HEIGHT)
        arrow_path.closeSubpath()

        full_path = QPainterPath(body_path)
        full_path.addPath(arrow_path)

        painter.setPen(QPen(QColor("#D64545"), 1))
        painter.setBrush(QColor("#FFF4F4"))
        painter.drawPath(full_path)

        painter.setPen(QColor("#7A1F1F"))

        text_rect = QRectF(
            14,
            self.ARROW_HEIGHT + 8,
            self.width() - 28,
            self.height() - self.ARROW_HEIGHT - 16,
        )

        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
            | Qt.TextFlag.TextWordWrap,
            self.message,
        )
