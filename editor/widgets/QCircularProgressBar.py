"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Circular loading progress bar widget for DreamStudio.

Supports two modes:

- **Determinate** (``set_value``): draws a partial arc proportional to
  ``value`` (0-100).
- **Indeterminate** (``start`` / ``stop``): continuously rotates a fixed
  span arc via an internal ``QTimer``, ideal for notifying the user that
  a background process is still working.
"""

from editor import *

_DEFAULT_SPIN_INTERVAL_MS = 16


class CircularProgressBar(QWidget):
    """A circular progress indicator with determinate and spin modes.

    Args:
        bg_color: Colour of the static track ring.
        fg_color: Colour of the moving / progress arc.
        parent: Optional parent widget.
        diameter: Fixed square size of the widget in pixels.
    """

    def __init__(
        self,
        bg_color: QColor,
        fg_color: QColor,
        parent=None,
        diameter: int = 25,
    ):
        super().__init__(parent)

        self.bg_color = bg_color
        self.fg_color = fg_color
        self._diameter = diameter

        self.value = 0
        self._spinning = False
        self._angle = 0
        self._spin_span = 80 * 16

        self.setFixedSize(QSize(diameter, diameter))
        self.setStyleSheet("background-color: transparent;")

        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(_DEFAULT_SPIN_INTERVAL_MS)
        self._spin_timer.timeout.connect(self._advance_spin)

    # ------------------------------------------------------------------
    # Determinate mode
    # ------------------------------------------------------------------

    def set_value(self, value: int) -> None:
        """Set the determinate progress percentage (0-100)."""
        self.value = max(0, min(100, int(value)))
        self.update()

    # ------------------------------------------------------------------
    # Indeterminate spin mode
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the spinning animation."""
        if self._spinning:
            return
        self._spinning = True
        self._spin_timer.start()
        self.update()

    def stop(self) -> None:
        """Stop the spinning animation and reset the arc angle."""
        self._spinning = False
        self._spin_timer.stop()
        self._angle = 0
        self.update()

    def is_spinning(self) -> bool:
        """Return ``True`` while the spin animation is active."""
        return self._spinning

    def _advance_spin(self) -> None:
        """Advance the arc rotation by one animation tick."""
        self._angle = (self._angle - 6) % (360 * 16)
        self.update()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        """Draw the track ring and the moving / progress arc."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen_width = max(2, self._diameter // 5)
        margin = pen_width / 2.0

        rect = self.rect().adjusted(
            int(margin), int(margin), -int(margin), -int(margin)
        )

        track_pen = QPen(self.bg_color, pen_width)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        progress_pen = QPen(self.fg_color, pen_width)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)

        if self._spinning:
            start_angle = self._angle
            span_angle = self._spin_span
        else:
            start_angle = 90 * 16
            span_angle = int(-self.value * 3.6 * 16)

        painter.drawArc(rect, start_angle, span_angle)
