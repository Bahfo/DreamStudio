"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Diagnostics overview ruler for DreamStudio.
"""

from __future__ import annotations

from editor import *
from editor.analysis.types import ProblemSeverity

logger = logging.getLogger(__name__)

SEVERITY_RANK = {severity: index for index, severity in enumerate(ProblemSeverity)}
UNKNOWN_RANK = len(SEVERITY_RANK)


def _rank(severity) -> int:
    """
    Returns the precedence of severity.
    """

    try:
        return SEVERITY_RANK.get(severity, UNKNOWN_RANK)
    except Exception:
        return UNKNOWN_RANK


class DiagnosticsRuler(QWidget):
    """
    An overview lan showing where the editor's diagnostics live.
    """

    LANE_WIDTH = 12
    TICK_HEIGHT = 3
    TICK_RADIUS = 1
    MAX_TRICKS = 400
    RIGHT_PADDING = 2
    TOP_PADDING = 2
    BOTTOM_PADDING = 2

    #: Emitted with the hovered 0-based line, or ``-1`` when the pointer
    #: leaves the lane.
    line_hovered = pyqtSignal(int)

    def __init__(self, source, parent=None, width=None):
        super().__init__(parent)
        self._source = source
        self._ticks: list = []
        self._hover_line: int = -1
        self._hover_y: int = -1

        self.setObjectName("DiagnosticRuler")
        self.setFixedWidth(int(width or self.LANE_WIDTH))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setToolTip("")
        self.hide()

    def set_ticks(self, ticks) -> None:
        """
        Replace the lane contents with *ticks*.

        Args:
            ticks: Iterable of ``(line0, color_hex, severity)`` tuples.
                *line0* is a 0-based line index and *severity* may be
                ``None`` when the producer does not know it.
        """
        payload = []
        for item in ticks or ():
            try:
                line = int(item[0])
                color = str(item[1])
                severity = item[2] if len(item) > 2 else None
            except Exception:
                continue
            if line < 0:
                continue
            payload.append((line, color, severity))
        if payload == self._ticks:
            return
        self._ticks = payload
        self.setVisible(bool(payload))
        self.update()

    def ticks(self) -> list:
        """
        Return a copy of the current ``(line, color, severity)`` ticks.
        """
        return list(self._ticks)

    def hovered_line(self) -> int:
        """
        Return the hovered 0-based line, or ``-1`` when nothing is hovered.
        """
        return self._hover_line

    def _doc_length(self) -> int:
        """
        Return the source document length in bytes (``0`` when unknown).
        """
        try:
            return int(self._source.SendScintilla(QsciScintilla.SCI_GETLENGTH) or 0)
        except Exception:
            return 0

    def _track(self) -> tuple:
        """
        Return the ``(top, height)`` of the paintable track.
        """
        top = self.TOP_PADDING
        height = max(1, self.height() - self.TOP_PADDING - self.BOTTOM_PADDING)
        return top, height

    def y_for_line(self, line: int) -> int:
        """
        Return the lane Y coordinate for 0-based *line*.
        """
        length = self._doc_length()
        top, track = self._track()
        if length <= 0:
            return top
        try:
            position = self._source.SendScintilla(
                QsciScintilla.SCI_POSITIONFROMLINE, max(0, int(line))
            )
        except Exception:
            return top
        if position is None or position < 0:
            return top
        return int(round(top + (position / length) * track))

    def line_for_y(self, y: int) -> int:
        """
        Return the 0-based line closest to lane coordinate *y*.

        Returns:
            A line index in ``[0, lines() - 1]``, or ``-1`` when the source
            document is empty.
        """
        length = self._doc_length()
        if length <= 0:
            return -1
        top, track = self._track()
        ratio = max(0.0, min(1.0, (int(y) - top) / float(track)))
        try:
            # The forward map rounds to whole pixels, so the inverse has to
            # round to whole bytes as well: truncating here would drop clicks
            # onto the previous line whenever a boundary sits next to a pixel.
            position = int(round(ratio * length))
            position = max(0, min(position, length - 1))
            line = self._source.SendScintilla(
                QsciScintilla.SCI_LINEFROMPOSITION, position
            )
            total = int(self._source.lines())
        except Exception:
            return -1
        if line is None or line < 0 or total <= 0:
            return -1
        return max(0, min(int(line), total - 1))

    def _hover_color(self) -> QColor:
        """
        Return the translucent highlight drawn behind the hovered tick.
        """
        try:
            color = self._source.palette().color(QPalette.ColorRole.Highlight)
        except Exception:
            return QColor(128, 128, 128, 40)
        color = QColor(color)
        color.setAlpha(48)
        return color

    def _paint_ticks(self, painter: QPainter, x: int, width: int) -> None:
        """
        Paint one merged tick per occupied pixel row.
        """
        rows: dict = {}
        for line, color, severity in self._ticks:
            y = self.y_for_line(line)
            current = rows.get(y)
            if current is None or _rank(severity) < _rank(current[1]):
                rows[y] = (color, severity)
        painter.setPen(Qt.PenStyle.NoPen)
        for y, (color, _severity) in rows.items():
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(
                x, y, width, self.TICK_HEIGHT, self.TICK_RADIUS, self.TICK_RADIUS
            )

    def _paint_density(
        self, painter: QPainter, x: int, top: int, track: int, width: int
    ) -> None:
        """
        Collapse an overflowing tick list into one stacked bar per severity.
        """
        buckets: dict = {}
        for _line, color, severity in self._ticks:
            key = severity if severity in SEVERITY_RANK else None
            entry = buckets.setdefault(key, [0, QColor(color)])
            entry[0] += 1
        total = max(1, len(self._ticks))
        y = float(top)
        painter.setPen(Qt.PenStyle.NoPen)
        for severity in sorted(buckets, key=_rank):
            count, color = buckets[severity]
            height = max(1.0, (count / total) * track)
            painter.setBrush(color)
            painter.drawRoundedRect(
                x,
                int(y),
                width,
                max(1, int(height)),
                self.TICK_RADIUS,
                self.TICK_RADIUS,
            )
            y += height

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Draw the severity ticks, loudest colour winning each pixel row.
        """
        if not self._ticks:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        width = max(2, self.width() - self.RIGHT_PADDING)
        x = self.width() - self.RIGHT_PADDING - width
        top, track = self._track()

        if self._hover_y >= 0:
            painter.fillRect(
                0,
                max(0, self._hover_y - 1),
                self.width(),
                self.TICK_HEIGHT + 2,
                self._hover_color(),
            )

        if len(self._ticks) > self.MAX_TRICKS:
            self._paint_density(painter, x, top, track, width)
        else:
            self._paint_ticks(painter, x, width)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Jump the source editor to the clicked line.
        """
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        line = self.line_for_y(int(event.position().y()))
        if line >= 0:
            try:
                self._source.setCursorPosition(line, 0)
                self._source.ensureLineVisible(line)
            except Exception:
                pass
            self.clear_hover()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Highlight the tick nearest the pointer and report its line.
        """
        line = self.line_for_y(int(event.position().y()))
        if line < 0 or not self._ticks:
            self.clear_hover()
            super().mouseMoveEvent(event)
            return
        self._hover_line = line
        self._hover_y = self.y_for_line(line)
        self.update()
        self.line_hovered.emit(line)
        event.accept()

    def leaveEvent(self, event: QEvent) -> None:
        """
        Drop the hover highlight when the pointer leaves the lane.
        """
        self.clear_hover()
        super().leaveEvent(event)

    def clear_hover(self) -> None:
        """
        Clear the hover highlight and report that nothing is hovered.
        """
        if self._hover_y < 0 and self._hover_line < 0:
            return
        self._hover_y = -1
        self._hover_line = -1
        self.update()
        self.line_hovered.emit(-1)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Repaint so ticks follow the new track height.
        """
        super().resizeEvent(event)
        self.update()
