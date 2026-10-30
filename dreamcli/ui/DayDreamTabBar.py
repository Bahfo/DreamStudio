from PyQt6.QtWidgets import QTabBar, QToolButton
from PyQt6.QtGui import (
    QPainterPath,
    QPainter,
    QColor,
    QFont,
    QPen,
)
from PyQt6.QtCore import Qt, QSize, QRect


class TerminalTabBar(QTabBar):
    BAR_HEIGHT = 40
    TAB_HEIGHT = 38
    TAB_WIDTH = 190

    BACKGROUND = "#151515"
    ACTIVE_BACKGROUND = "#202020"
    INACTIVE_BACKGROUND = "#151515"

    BORDER = "#393939"

    CORNER_RADIUS = 9
    BOTTOM_RADIUS = 12
    TAB_EXTENSION = 10

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedHeight(self.BAR_HEIGHT)

        self.setDrawBase(False)
        self.setExpanding(False)
        self.setMovable(True)
        self.setUsesScrollButtons(True)

        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setMouseTracking(True)

        self.setContentsMargins(0, 0, 0, 0)

        self.setStyleSheet(f"""
            QTabBar {{
                background-color: {self.BACKGROUND};
                border: none;
                margin: 0px;
                padding: 0px;
            }}

            QTabBar::tab {{
                border: none;
                margin: 0px;
                padding: 0px;
            }}
        """)

    def tabSizeHint(self, index):
        return QSize(self.TAB_WIDTH, self.TAB_HEIGHT)

    def _tab_paths(self, rect):
        k = 0.55228475

        left = float(rect.left())
        top = float(rect.top())

        right = float(rect.right() + 1)
        bottom = float(rect.bottom())

        radius = self.CORNER_RADIUS
        bottom_radius = self.BOTTOM_RADIUS
        extension = self.TAB_EXTENSION

        top_control = radius * k
        bottom_control = bottom_radius * k

        fill_path = QPainterPath()
        outline_path = QPainterPath()

        # Upper edge.
        fill_path.moveTo(left + radius, top)
        fill_path.lineTo(right - radius, top)

        outline_path.moveTo(left + radius, top)
        outline_path.lineTo(right - radius, top)

        # Upper-right corner.
        fill_path.cubicTo(
            right - radius + top_control,
            top,
            right,
            top + radius - top_control,
            right,
            top + radius,
        )

        outline_path.cubicTo(
            right - radius + top_control,
            top,
            right,
            top + radius - top_control,
            right,
            top + radius,
        )

        # Right edge.
        fill_path.lineTo(right, bottom - bottom_radius)
        outline_path.lineTo(right, bottom - bottom_radius)

        # Outward lower-right curve.
        fill_path.cubicTo(
            right,
            bottom - bottom_radius + bottom_control,
            right + extension - bottom_control,
            bottom,
            right + extension,
            bottom,
        )

        outline_path.cubicTo(
            right,
            bottom - bottom_radius + bottom_control,
            right + extension - bottom_control,
            bottom,
            right + extension,
            bottom,
        )

        # Extended bottom edge.
        fill_path.lineTo(left - extension, bottom)

        # Outward lower-left curve.
        fill_path.cubicTo(
            left - extension + bottom_control,
            bottom,
            left,
            bottom - bottom_radius + bottom_control,
            left,
            bottom - bottom_radius,
        )

        outline_path.moveTo(left - extension, bottom)
        outline_path.cubicTo(
            left - extension + bottom_control,
            bottom,
            left,
            bottom - bottom_radius + bottom_control,
            left,
            bottom - bottom_radius,
        )

        # Left edge.
        fill_path.lineTo(left, top + radius)
        outline_path.lineTo(left, top + radius)

        # Upper-left corner.
        fill_path.cubicTo(
            left,
            top + radius - top_control,
            left + radius - top_control,
            top,
            left + radius,
            top,
        )

        outline_path.cubicTo(
            left,
            top + radius - top_control,
            left + radius - top_control,
            top,
            left + radius,
            top,
        )

        fill_path.closeSubpath()
        return fill_path, outline_path

    def _create_close_button(self, index):
        button = QToolButton(self)

        button.setText("×")
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        button.setFixedSize(22, 22)
        button.setFont(QFont("Arial", 13))

        button.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: #999999;
                border: none;
                border-radius: 11px;
                padding: 0px;
            }

            QToolButton:hover {
                background-color: #383838;
                color: #FFFFFF;
            }

            QToolButton:pressed {
                background-color: #505050;
                color: #FFFFFF;
            }
        """)

        button.clicked.connect(
            lambda checked=False, b=button: self._close_button_clicked(b)
        )

        self.setTabButton(index, QTabBar.ButtonPosition.RightSide, button)

    def _close_button_clicked(self, button):
        for index in range(self.count()):
            if self.tabButton(index, QTabBar.ButtonPosition.RightSide) is button:
                self.tabCloseRequested.emit(index)
                return

    def tabInserted(self, index):
        super().tabInserted(index)
        self._create_close_button(index)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.fillRect(self.rect(), QColor(self.BACKGROUND))
        selected = self.currentIndex()

        paint_order = [
            index for index in reversed(range(self.count())) if index != selected
        ]

        if selected >= 0:
            paint_order.append(selected)

        for index in paint_order:
            rect = QRect(self.tabRect(index))
            is_selected = index == selected
            rect.setBottom(self.height() + 2)
            background = QColor(
                self.ACTIVE_BACKGROUND if is_selected else self.INACTIVE_BACKGROUND
            )

            foreground = QColor("#F0F0F0" if is_selected else "#A0A0A0")
            fill_path, outline_path = self._tab_paths(rect)

            painter.fillPath(fill_path, background)

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(self.BORDER), 0.8))
            painter.drawPath(outline_path)
            text_rect = rect.adjusted(13, 0, -37, 0)
            font = QFont("Arial", 9)

            font.setWeight(
                QFont.Weight.DemiBold if is_selected else QFont.Weight.Normal
            )

            painter.setFont(font)
            painter.setPen(foreground)

            text = painter.fontMetrics().elidedText(
                self.tabText(index),
                Qt.TextElideMode.ElideRight,
                text_rect.width(),
            )

            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text,
            )
        painter.end()
