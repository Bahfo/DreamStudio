from editor import *


class QErrorMessage(QWidget):
    """
    A guided tooltip-style message that appears in fixed positions.

    Can be used within problems diagnosis to show description of an exception or
    error, or within notifications popup.

    The bubble is drawn as a single outline: a rounded body plus an arrow that
    *protrudes* from the body towards the anchored token, instead of pointing
    back into the body. Colours are derived from the current theme background
    so the card blends into light and dark themes alike.
    """

    BORDER_RADIUS = 3
    ARROW_HEIGHT = 10
    ARROW_WIDTH = 14
    ARROW_INSET = 9

    MIN_WIDTH = 460
    MIN_HEIGHT = 66

    APPEAR_DELAY_MS = 80
    APPEAR_FADE_MS = 160
    APPEAR_RISE_MS = 180
    APPEAR_RISE_PX = 4

    _SEVERITY_TITLES = {
        "error": "Error",
        "warning": "Warning",
        "check": "Check",
        "typo": "Typo",
        "info": "Info",
    }

    #: Accent (border + arrow) per severity. The final card colours are mixed
    #: from these against the theme background, so every DreamStudio theme
    #: gets a readable, native-looking bubble.
    SEVERITY_ACCENTS = {
        "error": "#E5484D",
        "warning": "#E2A03F",
        "check": "#B266CC",
        "typo": "#4C8DF6",
        "info": "#3AAE9A",
    }

    def __init__(self, message: str, parent=None):
        super().__init__(parent)

        self.message = message
        self._arrow_x = 40
        self._arrow_up = False
        self._severity = "error"
        self._theme_color = ""

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(self.MIN_HEIGHT)
        self.setMinimumWidth(self.MIN_WIDTH)

        self._fade_in = None
        self._rise_in = None
        self._fx = QGraphicsOpacityEffect(self)
        self._fx.setOpacity(1.0)
        self.setGraphicsEffect(self._fx)

    ###############################################
    # STATE
    ###############################################

    def set_message(self, message: str) -> None:
        self.message = message
        self.update()

    def set_arrow_x_position(self, x: int) -> None:
        """Pin the arrow tip to *x* pixels from the bubble's left edge."""
        self._arrow_x = max(
            self.ARROW_INSET,
            min(x, max(self.ARROW_INSET, self.width() - self.ARROW_INSET)),
        )
        self.update()

    def set_arrow_up(self, up: bool) -> None:
        """Point the arrow up (``True``) or down (``False``)."""
        self._arrow_up = bool(up)
        self.update()

    def arrow_up(self) -> bool:
        """Return ``True`` when the arrow points up."""
        return self._arrow_up

    def set_severity(self, severity: str) -> None:
        """Tint the bubble for *severity* (``error``, ``warning``, ``check``,
        ``typo`` or ``info``). Unknown values fall back to ``error``.
        """
        key = str(severity or "error").strip().lower()
        if key not in self.SEVERITY_ACCENTS:
            key = "error"
        self._severity = key
        self.update()

    def severity(self) -> str:
        """Return the severity this bubble is currently tinted for."""
        return self._severity

    def set_theme_color(self, color) -> None:
        """Adopt *color* as the surface this bubble is drawn on top of.

        Pass the editor background (for example ``QPalette.Base``) so the
        card matches the active theme. Without it the widget falls back to its
        own palette.
        """
        self._theme_color = self._as_color(color).name()
        self.update()

    def theme_color(self) -> str:
        """Return the background colour the bubble is themed against."""
        return self._theme_color or self._surface_color().name()

    def is_dark(self) -> bool:
        """Return ``True`` when the bubble is drawn on a dark surface."""
        return self._surface_color().lightness() < 128

    def style_colors(self) -> tuple:
        """Return the resolved ``(accent, fill, text)`` colours.

        Exposed so callers and tests can verify the bubble against the theme
        without having to read pixels.
        """
        surface = self._surface_color()
        dark = surface.lightness() < 128
        accent = QColor(self.SEVERITY_ACCENTS.get(self._severity, ""))
        if not accent.isValid():
            accent = QColor(self.SEVERITY_ACCENTS["error"])

        if dark:
            accent = self._mix(accent, QColor("#ffffff"), 0.22)
            fill = self._mix(surface, accent, 0.20)
            text = self._mix(accent, QColor("#ffffff"), 0.72)
        else:
            accent = self._mix(accent, QColor("#000000"), 0.18)
            fill = self._mix(surface, accent, 0.10)
            text = self._mix(accent, QColor("#000000"), 0.55)
        return accent.name(), fill.name(), text.name()

    ###############################################
    # GEOMETRY
    ###############################################

    def sizeHint(self):
        return QSize(520, 78)

    def body_rect(self) -> QRectF:
        """Return the rounded body rect, excluding the arrow strip."""
        arrow = float(self.ARROW_HEIGHT)
        if self._arrow_up:
            return QRectF(0.0, arrow, float(self.width()), float(self.height() - arrow))
        return QRectF(0.0, 0.0, float(self.width()), float(self.height() - arrow))

    def arrow_tip(self) -> QPointF:
        """Return the arrow's outermost point (outside the body)."""
        if self._arrow_up:
            return QPointF(float(self._arrow_x), 0.0)
        return QPointF(float(self._arrow_x), float(self.height()))

    def _bubble_path(self) -> QPainterPath:
        """Build one outline for body + protruding arrow.

        Tracing a single path (instead of drawing a rounded rect and a
        separate triangle) keeps the arrow free of any seam and guarantees it
        points *out* of the bubble towards the token.
        """
        body = self.body_rect()
        radius = min(
            float(self.BORDER_RADIUS),
            (body.height()) / 2.0,
            (body.width()) / 2.0,
        )
        left, right = body.left(), body.right()
        top, bottom = body.top(), body.bottom()

        half_arrow = self.ARROW_WIDTH / 2.0
        arrow_left = self._arrow_x - half_arrow
        arrow_right = self._arrow_x + half_arrow
        tip = self.arrow_tip()

        path = QPainterPath()
        # The arrow base sits *on* the body's edge and its apex reaches out to
        # the widget boundary, so the bubble keeps a straight edge.
        base_y = body.top() if self._arrow_up else body.bottom()
        path.moveTo(arrow_left, base_y)
        path.lineTo(tip.x(), tip.y())
        path.lineTo(arrow_right, base_y)

        if self._arrow_up:
            # Arrow on top: walk the body clockwise starting at its top edge.
            path.lineTo(right - radius, base_y)
            path.arcTo(QRectF(right - radius, base_y, radius, radius), 90, -90)
            path.lineTo(right, bottom - radius)
            path.arcTo(QRectF(right - radius, bottom - radius, radius, radius), 0, -90)
            path.lineTo(left + radius, bottom)
            path.arcTo(QRectF(left, bottom - radius, radius, radius), 270, -90)
            path.lineTo(left, top + radius)
            path.arcTo(QRectF(left, top, radius, radius), 180, -90)
        else:
            # Arrow at the bottom: mirror the traversal upwards.
            path.lineTo(right - radius, base_y)
            path.arcTo(QRectF(right - radius, base_y - radius, radius, radius), 270, 90)
            path.lineTo(right, top + radius)
            path.arcTo(QRectF(right - radius, top, radius, radius), 0, 90)
            path.lineTo(left + radius, top)
            path.arcTo(QRectF(left, top, radius, radius), 90, 90)
            path.lineTo(left, base_y - radius)
            path.arcTo(QRectF(left, base_y - radius, radius, radius), 180, 90)
        path.closeSubpath()
        return path

    ###############################################
    # PAINTING
    ###############################################

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(self.APPEAR_DELAY_MS, self._play_appear)

    def hideEvent(self, event):
        try:
            for animation in (self._fade_in, self._rise_in):
                if animation is not None:
                    animation.stop()
            self._fx.setOpacity(1.0)
        except Exception:
            pass
        super().hideEvent(event)

    def _play_appear(self):
        if not self.isVisible():
            return
        try:
            for animation in (self._fade_in, self._rise_in):
                if animation is not None:
                    animation.stop()
            target = self.pos()
            start = target + QPoint(0, self.APPEAR_RISE_PX)
            self._fx.setOpacity(0.0)
            self.move(start)
            self._fade_in = QPropertyAnimation(self._fx, b"opacity")
            self._fade_in.setDuration(self.APPEAR_FADE_MS)
            self._fade_in.setStartValue(0.0)
            self._fade_in.setEndValue(1.0)
            self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._rise_in = QPropertyAnimation(self, b"pos")
            self._rise_in.setDuration(self.APPEAR_RISE_MS)
            self._rise_in.setStartValue(start)
            self._rise_in.setEndValue(target)
            self._rise_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade_in.start()
            self._rise_in.start()
        except Exception:
            pass

    def paintEvent(self, a0):
        accent_hex, fill_hex, text_hex = self.style_colors()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        surface = self._surface_color()
        border = self._mix(QColor(accent_hex), surface, 0.55)

        painter.setPen(QPen(QColor(accent_hex), 1.4))
        painter.setBrush(QColor(fill_hex))
        painter.drawPath(self._bubble_path())

        body = self.body_rect()
        accent = QColor(accent_hex)
        base_font = QFont(painter.font())

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(
            QRectF(
                body.left() + 5.0,
                body.top() + 34.0,
                3.0,
                max(1.0, body.height() - 46.0),
            ),
            1.5,
            1.5,
        )

        dot_center = QPointF(body.left() + 26.0, body.top() + 16.0)
        painter.setBrush(accent)
        painter.drawEllipse(dot_center, 4.0, 4.0)

        title = self._SEVERITY_TITLES.get(self._severity, "Error")
        title_font = QFont(base_font)
        title_font.setBold(True)
        title_font.setPointSize(max(8, base_font.pointSize() - 1))
        painter.setFont(title_font)
        painter.setPen(QColor(text_hex))
        painter.drawText(
            QRectF(body.left() + 38.0, body.top() + 5.0, body.width() - 52.0, 22.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title.upper(),
        )

        divider_y = body.top() + 30.0
        painter.setPen(QPen(border, 1.0))
        painter.drawLine(
            QPointF(body.left() + 14.0, divider_y),
            QPointF(body.right() - 14.0, divider_y),
        )

        painter.setPen(QColor(text_hex))
        painter.setFont(base_font)
        text_rect = QRectF(
            body.left() + 16,
            divider_y + 6.0,
            max(1.0, body.width() - 32),
            max(1.0, body.bottom() - divider_y - 12.0),
        )
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
            | Qt.TextFlag.TextWordWrap,
            self.message,
        )

    ###############################################
    # HELPERS
    ###############################################

    def _surface_color(self) -> QColor:
        """Return the background the bubble is drawn on top of."""
        if self._theme_color:
            return QColor(self._theme_color)
        return QColor(self.palette().color(QPalette.ColorRole.Base))

    @staticmethod
    def _as_color(color) -> QColor:
        """Coerce *color* (``QColor``/``str``/``int``) into a valid ``QColor``."""
        if isinstance(color, QColor):
            return QColor(color)
        candidate = QColor()
        if isinstance(color, int):
            candidate.setRgb(color & 0xFFFFFF)
        elif color:
            candidate = QColor(str(color))
        return candidate if candidate.isValid() else QColor("#ffffff")

    @staticmethod
    def _mix(base: QColor, target: QColor, ratio: float) -> QColor:
        """Blend *ratio* of *target* into *base*."""
        ratio = max(0.0, min(1.0, ratio))
        return QColor(
            round(base.red() + (target.red() - base.red()) * ratio),
            round(base.green() + (target.green() - base.green()) * ratio),
            round(base.blue() + (target.blue() - base.blue()) * ratio),
        )
