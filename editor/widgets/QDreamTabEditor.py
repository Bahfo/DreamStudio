from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QEvent, QTimer
from PyQt6.QtWidgets import (
    QTabBar,
    QTabWidget,
    QStyleOptionTab,
    QStyle,
    QGraphicsOpacityEffect,
)
from PyQt6.QtGui import (
    QPen,
    QColor,
    QPainter,
    QPalette,
    QPainterPath,
)


class DreamStudioIDETabBar(QTabBar):
    def __init__(self, _parent=None):
        super().__init__(_parent)
        self.setDrawBase(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setUsesScrollButtons(True)
        self._parent = _parent

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

        self._hover_index = -1
        self._is_syncing = False
        self._dirty_indices: set = set()
        self.currentChanged.connect(self._on_current_changed)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        index = self.tabAt(event.position().toPoint())
        if index != self._hover_index:
            self._hover_index = index
            self._sync_close_buttons(update_geometry=False)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hover_index = -1
        self._sync_close_buttons(update_geometry=False)

    def _sync_close_buttons(self, update_geometry=True):
        if getattr(self, "_is_syncing", False) or not self.tabsClosable():
            return

        self._is_syncing = True
        current_idx = self.currentIndex()

        for i in range(self.count()):
            button = self.tabButton(i, QTabBar.ButtonPosition.RightSide)
            if not button:
                continue

            is_visible = i == current_idx or i == self._hover_index

            effect = button.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(button)
                button.setGraphicsEffect(effect)

            effect.setOpacity(1.0 if is_visible else 0.0)
            button.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, not is_visible
            )

            if update_geometry:
                rect = self.tabRect(i)
                if not rect.isNull():
                    btn_w = 18
                    btn_h = 18
                    margin_right = 8
                    x = rect.right() - btn_w - margin_right
                    y = rect.center().y() - (btn_h // 2)
                    new_geo = QRect(x, y, btn_w, btn_h)
                    if button.geometry() != new_geo:
                        button.setGeometry(new_geo)
                    button.raise_()

        self._is_syncing = False
        win = self.window()
        if win is not None and hasattr(win, "update_editor_visibility"):
            win.update_editor_visibility()

    def _on_current_changed(self):
        QTimer.singleShot(0, self._sync_close_buttons)

    def tabLayoutChange(self):
        super().tabLayoutChange()
        self._on_current_changed()

    def tabInserted(self, index):
        super().tabInserted(index)
        self._sync_close_buttons()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self._sync_close_buttons()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
            QEvent.Type.PaletteChange,
        ):
            self._sync_close_buttons()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        selected_index = self.currentIndex()

        selected_bg = getattr(self, "selected_bg", QColor("#25324D"))
        hover_bg = getattr(self, "hover_bg", QColor("#2D2D2D"))
        inactive_bg = getattr(self, "inactive_bg", QColor("#1E1E1E"))
        border_color = getattr(self, "border_color", QColor("#35538F"))
        hover_border_color = getattr(self, "hover_border_color", QColor("#3C3F41"))
        inactive_border_color = getattr(
            self, "inactive_border_color", QColor("#1E1E1E")
        )

        for i in range(self.count()):
            if i == selected_index:
                continue

            option = QStyleOptionTab()
            self.initStyleOption(option, i)
            is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

            bg = hover_bg if is_hovered else inactive_bg
            border = hover_border_color if is_hovered else inactive_border_color

            self._draw_tab(painter, i, bg, border, False, option)

        if selected_index >= 0:
            option = QStyleOptionTab()
            self.initStyleOption(option, selected_index)
            self._draw_tab(
                painter, selected_index, selected_bg, border_color, True, option
            )

    def _draw_tab(self, painter, index, bg_color, border_color, selected, option):
        rect = self.tabRect(index)
        if rect.isNull():
            return

        r = rect.adjusted(1, 6, -1, -6)
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

        text_sel = getattr(self, "_text_selected", QColor("white"))
        text_inactive = getattr(self, "_text_inactive", QColor("#AFB1B3"))
        option.palette.setColor(
            QPalette.ColorRole.WindowText, text_sel if selected else text_inactive
        )

        right_reserve = 10
        left_margin = 10
        option.rect = r.adjusted(left_margin, 0, -right_reserve, 0)

        option.state &= ~QStyle.StateFlag.State_MouseOver
        option.state &= ~QStyle.StateFlag.State_HasFocus

        self.style().drawControl(
            QStyle.ControlElement.CE_TabBarTabLabel,
            option,
            painter,
            self,
        )

        painter.restore()

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        return QSize(size.width() + 25, size.height() + 12)

    def mark_dirty(self, index: int, is_dirty: bool) -> None:
        if is_dirty:
            self._dirty_indices.add(index)
        else:
            self._dirty_indices.discard(index)
        rect = self.tabRect(index)
        if not rect.isNull():
            self.update(rect)

    def retheme(self, t) -> None:
        self.selected_bg = QColor(t.color("tab.selected_bg"))
        self.hover_bg = QColor(t.color("tab.hover_bg"))
        self.inactive_bg = QColor(t.color("tab.inactive_bg"))
        self.border_color = QColor(t.color("tab.selected_border"))
        self.hover_border_color = QColor(t.color("tab.hover_border"))
        self.inactive_border_color = QColor(t.color("tab.inactive_border"))
        self._text_selected = QColor(t.color("tab.text_selected"))
        self._text_inactive = QColor(t.color("tab.text_inactive"))
        self._dirty_dot = QColor(t.color("tab.dirty_dot"))
        self._dirty_indices.clear()
        self.rebuild_dirty_indices()
        self.update()

    def rebuild_dirty_indices(self) -> None:
        self._dirty_indices.clear()
        for i in range(self._parent.count()):
            w = self._parent.widget(i)
            if w is not None and hasattr(w, "is_dirty"):
                try:
                    if w.is_dirty():
                        self._dirty_indices.add(i)
                except RuntimeError:
                    pass

    def on_double_click(self, index):
        if index == -1:
            self._parent.add_new_editor()


class QDreamTabEditor(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(DreamStudioIDETabBar(self))
        self.setTabsClosable(False)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
        """)
