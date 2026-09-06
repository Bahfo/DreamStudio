from editor import *


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
        self._readonly_indices: set = set()

        self._selected_bg = QColor("#1E1E1E")
        self._hover_bg = QColor("#3E3E42")
        self._inactive_bg = QColor("#252526")
        self._border_color = QColor("#1E1E1E")
        self._hover_border_color = QColor("#3E3E42")
        self._inactive_border_color = QColor("#252526")
        self._border_buttom = QColor("#005190")

        self._text_selected = QColor("#FFFFFF")
        self._text_inactive = QColor("#969696")
        self._dirty_dot = QColor("#EAB308")
        self._readonly_color = QColor("#888888")

        self.currentChanged.connect(self._on_current_changed)

    # -- Q_PROPERTY: background colors -----------------------------------

    def get_selected_bg(self):
        return self._selected_bg

    def set_selected_bg(self, color):
        self._selected_bg = QColor(color)
        self.update()

    selected_bg = pyqtProperty(QColor, get_selected_bg, set_selected_bg)

    def get_hover_bg(self):
        return self._hover_bg

    def set_hover_bg(self, color):
        self._hover_bg = QColor(color)
        self.update()

    hover_bg = pyqtProperty(QColor, get_hover_bg, set_hover_bg)

    def get_inactive_bg(self):
        return self._inactive_bg

    def set_inactive_bg(self, color):
        self._inactive_bg = QColor(color)
        self.update()

    inactive_bg = pyqtProperty(QColor, get_inactive_bg, set_inactive_bg)

    def get_border_color(self):
        return self._border_color

    def set_border_color(self, color):
        self._border_color = QColor(color)
        self.update()

    border_color = pyqtProperty(QColor, get_border_color, set_border_color)

    def get_hover_border_color(self):
        return self._hover_border_color

    def set_hover_border_color(self, color):
        self._hover_border_color = QColor(color)
        self.update()

    hover_border_color = pyqtProperty(
        QColor, get_hover_border_color, set_hover_border_color
    )

    def get_inactive_border_color(self):
        return self._inactive_border_color

    def set_inactive_border_color(self, color):
        self._inactive_border_color = QColor(color)
        self.update()

    inactive_border_color = pyqtProperty(
        QColor, get_inactive_border_color, set_inactive_border_color
    )

    def get_text_selected(self):
        return self._text_selected

    def set_text_selected(self, color):
        self._text_selected = QColor(color)
        self.update()

    text_selected = pyqtProperty(QColor, get_text_selected, set_text_selected)

    def get_text_inactive(self):
        return self._text_inactive

    def set_text_inactive(self, color):
        self._text_inactive = QColor(color)
        self.update()

    text_inactive = pyqtProperty(QColor, get_text_inactive, set_text_inactive)

    def get_dirty_dot(self):
        return self._dirty_dot

    def set_dirty_dot(self, color):
        self._dirty_dot = QColor(color)
        self.update()

    dirty_dot = pyqtProperty(QColor, get_dirty_dot, set_dirty_dot)

    def get_readonly_color(self):
        return self._readonly_color

    def set_readonly_color(self, color):
        self._readonly_color = QColor(color)
        self.update()

    readonly_color = pyqtProperty(QColor, get_readonly_color, set_readonly_color)

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
                    btn_w = 14
                    btn_h = 14
                    margin_right = 6
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
        self.rebuild_dirty_indices()
        self.rebuild_readonly_indices()

    def tabInserted(self, index):
        super().tabInserted(index)
        self._sync_close_buttons()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self._sync_close_buttons()
        self.rebuild_readonly_indices()

    def changeEvent(self, event):
        if getattr(self, "_in_change_event", False):
            return
        self._in_change_event = True
        try:
            super().changeEvent(event)
            if event.type() in (
                QEvent.Type.FontChange,
                QEvent.Type.StyleChange,
                QEvent.Type.PaletteChange,
            ):
                self._sync_close_buttons()
        finally:
            self._in_change_event = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the solid unified tab bar background row first
        painter.fillRect(self.rect(), self.inactive_bg)

        selected_index = self.currentIndex()

        for i in range(self.count()):
            if i == selected_index:
                continue

            option = QStyleOptionTab()
            self.initStyleOption(option, i)
            is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

            bg = self.hover_bg if is_hovered else self.inactive_bg
            border = (
                self.hover_border_color if is_hovered else self.inactive_border_color
            )

            self._draw_tab(painter, i, bg, border, False, option)

        if selected_index >= 0:
            option = QStyleOptionTab()
            self.initStyleOption(option, selected_index)
            self._draw_tab(
                painter,
                selected_index,
                self.selected_bg,
                self.border_color,
                True,
                option,
            )

    def _draw_tab(self, painter, index, bg_color, border_color, selected, option):
        rect = self.tabRect(index)
        if rect.isNull():
            return

        painter.save()

        painter.fillRect(rect, bg_color)

        pen = QPen(border_color)
        pen.setWidth(2)
        painter.setPen(pen)

        if selected:
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        else:
            painter.setPen(QPen(self.inactive_bg.lighter(110)))
            painter.drawLine(
                rect.right(), rect.top() + 4, rect.right(), rect.bottom() - 4
            )

        text_offset = 0
        if index in self._dirty_indices:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._dirty_dot)
            painter.drawEllipse(QPoint(rect.left() + 10, rect.center().y()), 3, 3)
            painter.restore()
            text_offset += 12

        if index in self._readonly_indices:
            painter.save()
            pen = QPen(self._readonly_color)
            pen.setWidthF(1.5)
            painter.setPen(pen)
            lock_x = rect.left() + 8 + text_offset
            lock_y = rect.center().y() - 3
            painter.drawRect(lock_x, lock_y, 7, 6)
            painter.drawArc(lock_x + 1, lock_y - 3, 5, 6, 0 * 16, 180 * 16)
            painter.restore()
            text_offset += 14

        option.palette.setColor(
            QPalette.ColorRole.WindowText,
            self._text_selected if selected else self._text_inactive,
        )

        right_reserve = 20 if self.tabsClosable() else 12
        left_margin = 12 + text_offset
        option.rect = rect.adjusted(left_margin, 0, -right_reserve, 0)

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
        return QSize(size.width() + 10, 32)

    def mark_dirty(self, index: int, is_dirty: bool) -> None:
        if is_dirty:
            self._dirty_indices.add(index)
        else:
            self._dirty_indices.discard(index)
        rect = self.tabRect(index)
        if not rect.isNull():
            self.update(rect)

    def mark_readonly(self, index: int, is_readonly: bool) -> None:
        if is_readonly:
            self._readonly_indices.add(index)
        else:
            self._readonly_indices.discard(index)
        rect = self.tabRect(index)
        if not rect.isNull():
            self.update(rect)

    def rebuild_dirty_indices(self) -> None:
        self._dirty_indices.clear()
        parent = self._parent if self._parent is not None else self.parent()
        if parent is None or not hasattr(parent, "count") or not hasattr(parent, "widget"):
            return
        for i in range(parent.count()):
            w = parent.widget(i)
            if w is not None and hasattr(w, "is_dirty"):
                try:
                    if w.is_dirty():
                        self._dirty_indices.add(i)
                except RuntimeError:
                    pass

    def rebuild_readonly_indices(self) -> None:
        self._readonly_indices.clear()
        parent = self._parent if self._parent is not None else self.parent()
        if parent is None or not hasattr(parent, "count") or not hasattr(parent, "widget"):
            return
        for i in range(parent.count()):
            w = parent.widget(i)
            if w is not None and hasattr(w, "isReadOnly"):
                try:
                    if w.isReadOnly():
                        self._readonly_indices.add(i)
                except RuntimeError:
                    pass


class QDreamTabEditor(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(DreamStudioIDETabBar(self))
        self.setTabsClosable(False)
        self.setMovable(True)
        self.setDocumentMode(True)

        self.setTabPosition(QTabWidget.TabPosition.North)
