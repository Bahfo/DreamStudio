from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QPainterPath,
    QLinearGradient, QBrush
)
from PyQt6.QtWidgets import (QWidget)


_CORE_COLORS = [
    "#E06C75", "#61AFEF", "#98C379", "#E5C07B",
    "#C678DD", "#56B6C2", "#D19A66", "#ABB2BF",
    "#BE5046", "#3E7BCC", "#7EC87E", "#D4A05A",
    "#F78C6C", "#89DDFF", "#C3E88D", "#FF9CAC",
]


class SystemGraphUtil(QWidget):
    """SystemGraphUtil with Antialiasing, Smooth Bezier Paths, and Gradients."""
    def __init__(self, parent=None, title="", unit="%", min_y=0, max_y=100, 
        _PLOT_HEIGHT = 140, _WINDOW_WIDTH = 780, _WINDOW_HEIGHT = 760):
        super().__init__(parent)
        self._title = title
        self._unit = unit
        self._min_y = min_y
        self._max_y = max_y
        self._series = {}
        self._colors = {}
        self._max_points = 60
        self._show_legend = True

        self.bg = QColor("#1E1E1E")
        self.grid_color = QColor("#2A2D30")
        self.text_color = QColor("#999999")
        self.border_color = QColor("#3F4145")

        self.setMinimumHeight(_PLOT_HEIGHT)
        self.setMaximumHeight(_PLOT_HEIGHT * 2)

    def add_series(self, name, color=None):
        self._series[name] = []
        if color is not None:
            self._colors[name] = QColor(color)
        else:
            idx = len(self._series)
            self._colors[name] = QColor(_CORE_COLORS[idx % len(_CORE_COLORS)])

    def append(self, name, value):
        if name not in self._series:
            self.add_series(name)
        self._series[name].append(value)
        if len(self._series[name]) > self._max_points:
            self._series[name].pop(0)

    def set_range(self, min_y, max_y):
        self._min_y = min_y
        self._max_y = max_y

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        painter.fillRect(self.rect(), self.bg)

        ml, mr, mt, mb = 50, 15, 25, 25
        px = ml
        py = mt
        pw = w - ml - mr
        ph = h - mt - mb

        if pw <= 0 or ph <= 0:
            painter.end()
            return

        painter.setPen(QPen(self.border_color, 1))
        painter.drawRect(px, py, pw, ph)

        painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
        for i in range(1, 4):
            y = py + int(ph * i / 4)
            painter.drawLine(px, y, px + pw, y)

        painter.setPen(self.text_color)
        f = QFont("JetBrains Mono", 8)
        painter.setFont(f)
        for i in range(5):
            y = py + ph - int(ph * i / 4)
            val = self._min_y + (self._max_y - self._min_y) * i / 4
            painter.drawText(2, y - 6, ml - 6, 12,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             f"{val:.0f}")

        tf = QFont("Inter", 10, QFont.Weight.Bold)
        painter.setFont(tf)
        painter.setPen(self.text_color)
        painter.drawText(px, 2, pw, 18,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f"{self._title} ({self._unit})")

        if not self._series:
            painter.end()
            return

        max_len = max((len(v) for v in self._series.values()), default=0)
        if max_len < 2:
            painter.end()
            return

        painter.save()
        painter.setClipRect(px, py, pw, ph)

        rng = max(self._max_y - self._min_y, 1)

        for name, values in self._series.items():
            if len(values) < 2:
                continue

            color = self._colors.get(name, QColor("#FFFFFF"))

            pts = []
            for i, val in enumerate(values):
                x = px + (i * pw / max(self._max_points - 1, 1))
                ratio = (val - self._min_y) / rng
                y = py + ph - int(ratio * ph)
                pts.append(QPointF(x, y))

            path = QPainterPath()
            path.moveTo(pts[0])

            n = len(pts)
            for i in range(n - 1):
                p0 = pts[i]
                p1 = pts[i + 1]

                if i == 0:
                    cx1 = p0.x() + (p1.x() - p0.x()) * 0.25
                    cy1 = p0.y()
                else:
                    pm1 = pts[i - 1]
                    cx1 = p0.x() + (p1.x() - pm1.x()) / 6
                    cy1 = p0.y() + (p1.y() - pm1.y()) / 6

                if i == n - 2:
                    cx2 = p1.x() - (p1.x() - p0.x()) * 0.25
                    cy2 = p1.y()
                else:
                    p2 = pts[i + 2]
                    cx2 = p1.x() - (p2.x() - p0.x()) / 6
                    cy2 = p1.y() - (p2.y() - p0.y()) / 6

                path.cubicTo(cx1, cy1, cx2, cy2, p1.x(), p1.y())

            fill_path = QPainterPath(path)
            fill_path.lineTo(px + pw, py + ph)
            fill_path.lineTo(px, py + ph)
            fill_path.closeSubpath()

            gradient = QLinearGradient(0, py, 0, py + ph)
            gradient.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 100))
            gradient.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))

            painter.fillPath(fill_path, QBrush(gradient))

            painter.setPen(QPen(color, 2))
            painter.drawPath(path)

        painter.restore()

        if self._show_legend and len(self._series) <= 8:
            lx = px + 6
            ly = py + 4
            for name, color in self._colors.items():
                if name not in self._series or not self._series[name]:
                    continue
                painter.setPen(QPen(color, 2.5))
                painter.drawLine(lx, ly + 5, lx + 14, ly + 5)
                painter.setPen(self.text_color)
                lf = QFont("JetBrains Mono", 7)
                painter.setFont(lf)
                painter.drawText(lx + 18, ly + 8, name)
                ly += 14

        painter.end()