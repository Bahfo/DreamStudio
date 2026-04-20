from PyQt6.QtCore import Qt, QTimer, QRect, QEvent
from PyQt6.QtWidgets import QTabBar, QStyleOptionTab, QStyle
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen


class DreamStudioIDETabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDrawBase(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setUsesScrollButtons(True)

        self._sync_pending = False

    def _schedule_sync_close_buttons(self):
        if self._sync_pending:
            return
        self._sync_pending = True
        QTimer.singleShot(0, self._sync_close_buttons)

    def _sync_close_buttons(self):
        self._sync_pending = False

        if not self.tabsClosable():
            return

        for i in range(self.count()):
            button = self.tabButton(i, QTabBar.ButtonPosition.RightSide)
            if not button:
                continue

            rect = self.tabRect(i)
            if rect.isNull():
                continue

            target_height = min(18, max(16, rect.height() - 4))
            natural_width = button.sizeHint().width() + 12
            max_width = max(18, rect.width() // 3)
            final_width = min(natural_width, max_width)

            x = rect.right() - final_width - 6
            y = rect.center().y() - (target_height // 2)

            button.setGeometry(QRect(x, y, final_width, target_height))
            button.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_sync_close_buttons()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_sync_close_buttons()

    def tabLayoutChange(self):
        super().tabLayoutChange()
        self._schedule_sync_close_buttons()
        self.update()

    def tabInserted(self, index):
        super().tabInserted(index)
        self._schedule_sync_close_buttons()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self._schedule_sync_close_buttons()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
            QEvent.Type.PaletteChange,
        ):
            self._schedule_sync_close_buttons()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        selected_index = self.currentIndex()

        selected_bg = QColor("#25324D")
        inactive_bg = QColor("#1E1E1E")
        border_color = QColor("#35538F")
        inactive_border_color = QColor("#1E1E1E")

        for i in range(self.count()):
            if i == selected_index:
                continue
            self._draw_tab(painter, i, inactive_bg, inactive_border_color, False)

        if selected_index >= 0:
            self._draw_tab(painter, selected_index, selected_bg, border_color, True)

    def _draw_tab(self, painter, index, bg_color, border_color, selected):
        rect = self.tabRect(index)
        if rect.isNull():
            return

        r = rect.adjusted(1, 2, -1, 0)
        radius = 5

        path = QPainterPath()
        path.moveTo(r.left(), r.bottom() - radius)
        path.lineTo(r.left(), r.top() + radius)
        path.quadTo(r.left(), r.top(), r.left() + radius, r.top())
        path.lineTo(r.right() - radius, r.top())
        path.quadTo(r.right(), r.top(), r.right(), r.top() + radius)
        path.lineTo(r.right(), r.bottom() - radius)
        path.quadTo(r.right(), r.bottom(), r.right() - radius, r.bottom())
        path.lineTo(r.left() + radius, r.bottom())
        path.quadTo(r.left(), r.bottom(), r.left(), r.bottom() - radius)
        path.closeSubpath()

        painter.save()
        painter.fillPath(path, bg_color)

        pen = QPen(border_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)

        if selected:
            painter.drawLine(
                r.left() + radius,
                r.top(),
                r.right() - radius,
                r.top(),
            )

        option = QStyleOptionTab()
        self.initStyleOption(option, index)

        right_reserve = 32 if self.tabsClosable() else 10

        option.rect = r.adjusted(10, 0, -right_reserve, 0)

        self.style().drawControl(
            QStyle.ControlElement.CE_TabBarTabLabel,
            option,
            painter,
            self,
        )

        painter.restore()
