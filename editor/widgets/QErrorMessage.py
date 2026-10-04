from editor import *


class QErrorMessage(QWidget):
    """
    A guided tooltip-style message that appears in fixed positions.

    Can be used within problems diagnosis to show description of an exception or
    error, or within notifications popup.
    """

    BORDER_RADIUS = 6
    ARROW_HEIGHT = 8

    #: (accent, background, text) per severity. The accents mirror the
    #: squiggle colours of ``ProblemsWidget.SEVERITY_COLORS`` so the bubble
    #: always looks native to the diagnostic it explains.
    SEVERITY_STYLES = {
        "error": ("#D64545", "#FFF4F4", "#7A1F1F"),
        "warning": ("#C08A00", "#FFF8E8", "#6B4A00"),
        "check": ("#A45BB5", "#FBF0FD", "#5E2A68"),
        "typo": ("#2F7FE0", "#EFF6FF", "#1B4676"),
        "info": ("#2F9E8C", "#EDFBF8", "#12574D"),
    }

    def __init__(self, message: str, parent=None):
        super().__init__(parent)

        self.message = message
        self._arrow_x = 40
        self._arrow_up = False
        self._severity = "error"

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(60)
        self.setMinimumWidth(400)

    def set_message(self, message: str) -> None:
        self.message = message
        self.update()

    def set_arrow_x_position(self, x: int) -> None:
        self._arrow_x = max(
            self.BORDER_RADIUS + 6,
            min(x, self.width() - self.BORDER_RADIUS - 6),
        )
        self.update()

    def set_severity(self, severity: str) -> None:
        """Tint the bubble for *severity* (``error``, ``warning``, ``check``,
        ``typo`` or ``info``). Unknown values fall back to ``error``.
        """
        key = str(severity or "error").strip().lower()
        if key not in self.SEVERITY_STYLES:
            key = "error"
        self._severity = key
        self.update()

    def severity(self) -> str:
        """Return the severity this bubble is currently tinted for."""
        return self._severity

    def set_arrow_up(self, up: bool) -> None:
        """Point the arrow up (``True``) or down (``False``)."""
        self._arrow_up = bool(up)
        self.update()

    def arrow_up(self) -> bool:
        """Return ``True`` when the arrow points up."""
        return self._arrow_up

    def sizeHint(self):
        return QSize(420, 64)

    def paintEvent(self, a0):
        arrow_width = 12
        arrow_path = QPainterPath()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        arrow_tip_y = 0 if self._arrow_up else self.ARROW_HEIGHT
        arrow_base_y = self.ARROW_HEIGHT if self._arrow_up else 0
        body_top = self.ARROW_HEIGHT if self._arrow_up else 0
        body_height = self.height() - self.ARROW_HEIGHT

        body_rect = QRectF(
            0,
            body_top,
            self.width(),
            body_height,
        )

        body_path = QPainterPath()
        body_path.addRoundedRect(
            body_rect,
            self.BORDER_RADIUS,
            self.BORDER_RADIUS,
        )

        arrow_left = self._arrow_x - arrow_width / 2
        arrow_right = self._arrow_x + arrow_width / 2

        arrow_path.moveTo(arrow_left, arrow_base_y)
        arrow_path.lineTo(self._arrow_x, arrow_tip_y)
        arrow_path.lineTo(arrow_right, arrow_base_y)
        arrow_path.closeSubpath()

        full_path = QPainterPath(body_path)
        full_path.addPath(arrow_path)

        accent, background, text_color = self.SEVERITY_STYLES.get(
            self._severity, self.SEVERITY_STYLES["error"]
        )

        painter.setPen(QPen(QColor(accent), 1))
        painter.setBrush(QColor(background))
        painter.drawPath(full_path)

        painter.setPen(QColor(text_color))

        text_rect = QRectF(
            14,
            body_top + 8,
            self.width() - 28,
            body_height - 16,
        )

        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
            | Qt.TextFlag.TextWordWrap,
            self.message,
        )
