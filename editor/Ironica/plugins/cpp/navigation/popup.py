from __future__ import annotations

from typing import Callable, Optional, Sequence

from PyQt6.QtCore import QEvent, QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QFontMetrics, QPainter, QStandardItem
from PyQt6.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from ..navigation.engine import NavigationResult
from editor.Ironica.utils.completion import CompletionPopup


class NavigationPopup(CompletionPopup):
    """Non-activating popup listing multiple navigation targets.

    The editor keeps keyboard focus while this popup is visible.  Activating a
    ``Qt.ToolTip`` window desynchronises Qt's focus bookkeeping from the window
    manager on X11, which hides the editor caret and stops keyboard input.
    Navigation keys are forwarded from the editor through an event filter.

    Attributes:
        _editor: Editor that owns the caret and the keyboard focus.
        _on_select: Callback invoked when a result is chosen.
        _restore_focus: Whether the next hide should refocus the editor.
        _filters_installed: Whether the editor/application filters are active.
    """

    target_selected = pyqtSignal(NavigationResult)
    cancelled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Go To")
        self._on_select: Optional[Callable[[NavigationResult], None]] = None
        self._editor: Optional[QWidget] = None
        self._restore_focus = False
        self._filters_installed = False
        self._delegate = NavigationResultDelegate(self.list_view)
        self.list_view.setItemDelegate(self._delegate)
        self.hint_bar.hide()

    def set_results(
        self,
        results: Sequence[NavigationResult],
        on_select: Optional[Callable[[NavigationResult], None]] = None,
    ) -> None:
        """Replace the popup contents with *results*.

        Args:
            results: Navigation targets to display.
            on_select: Callback invoked with the chosen target.
        """
        self._on_select = on_select
        self.model.clear()

        for result in results:
            item = QStandardItem(self._format_result(result))
            item.setData(result, Qt.ItemDataRole.UserRole)
            self.model.appendRow(item)

        if self.model.rowCount():
            self.list_view.setCurrentIndex(self.model.index(0, 0))
        self._resize_to_content()

    @staticmethod
    def _format_result(result: NavigationResult) -> str:
        """Return the single-line label for *result*."""
        labels = {
            "definition": "Definition",
            "declaration": "Declaration",
            "implementation": "Implementation",
            "reference": "Reference",
            "include": "Include",
        }
        label = labels.get(result.kind, result.kind.title())
        location = f"{result.file_path}:{result.line + 1}:{result.col + 1}"
        if result.display_name:
            return f"{label}  {location}  —  {result.display_name}"
        return f"{label}  {location}"

    def _resize_to_content(self) -> None:
        """Resize the popup so all visible rows fit without clipping."""
        count = self.model.rowCount()
        if count <= 0:
            return

        rows = min(count, 10)
        row_height = NavigationResultDelegate.ROW_HEIGHT
        metrics = self.list_view.fontMetrics()

        content_width = 0
        for row in range(count):
            item = self.model.item(row, 0)
            if item is not None:
                content_width = max(
                    content_width, metrics.horizontalAdvance(item.text())
                )

        screen = QApplication.screenAt(self.mapToGlobal(QPoint(0, 0)))
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            available = QRect(0, 0, 1200, 800)
        else:
            available = screen.availableGeometry()

        width = min(
            max(450, content_width + 40),
            max(450, int(available.width() * 0.65)),
        )
        if count > rows:
            width += 12
        height = rows * row_height + 8
        self.resize(width, height)

    def _on_clicked(self, index) -> None:
        """Commit the result at *index* and dismiss the popup."""
        if not self.isVisible() or not index.isValid():
            return
        item = self.model.itemFromIndex(index)
        result = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not isinstance(result, NavigationResult):
            return

        self._dismiss(restore_focus=True)
        if self._on_select is not None:
            self._on_select(result)
        self.target_selected.emit(result)

    def _on_double_clicked(self, index) -> None:
        self._on_clicked(index)

    def _commit_current(self) -> None:
        """Commit the highlighted result, or dismiss when nothing is selected."""
        index = self.list_view.currentIndex()
        if index.isValid():
            self._on_clicked(index)
        else:
            self._dismiss(restore_focus=True)

    def show_at_cursor(self, editor) -> None:
        """Show the popup near *editor*'s caret without taking focus.

        Args:
            editor: Editor whose caret anchors the popup and keeps focus.
        """
        self._editor = editor
        try:
            line, column = editor.getCursorPosition()
            position = editor.positionFromLineIndex(line, column)
            x = editor.SendScintilla(editor.SCI_POINTXFROMPOSITION, 0, position)
            y = editor.SendScintilla(editor.SCI_POINTYFROMPOSITION, 0, position)
            height = editor.SendScintilla(editor.SCI_TEXTHEIGHT, line)
            self.move(editor.mapToGlobal(QPoint(int(x), int(y + height))))
        except (AttributeError, RuntimeError, TypeError, ValueError):
            self.move(QCursor.pos())

        self._install_filters()
        self.show()
        self.raise_()

    def _install_filters(self) -> None:
        """Observe editor keys and application-wide dismissal events."""
        if self._filters_installed:
            return
        if self._editor is not None:
            self._editor.installEventFilter(self)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self._filters_installed = True

    def _remove_filters(self) -> None:
        """Detach the event filters installed by :meth:`_install_filters`."""
        if not self._filters_installed:
            return
        if self._editor is not None:
            try:
                self._editor.removeEventFilter(self)
            except RuntimeError:
                pass
        app = QApplication.instance()
        if app is not None:
            try:
                app.removeEventFilter(self)
            except RuntimeError:
                pass
        self._filters_installed = False

    def _dismiss(self, restore_focus: bool) -> None:
        """Hide the popup and optionally return focus to the editor."""
        if not self.isVisible():
            return
        self._restore_focus = restore_focus
        self.hide()

    def _focus_editor(self) -> None:
        """Give keyboard focus back to the editor and its top-level window."""
        editor = self._editor
        if editor is None:
            return
        try:
            window = editor.window()
            if window is not QApplication.activeWindow():
                window.activateWindow()
            editor.setFocus(Qt.FocusReason.OtherFocusReason)
        except (AttributeError, RuntimeError):
            pass

    def _dismiss_if_outside(self, event) -> None:
        """Dismiss when a mouse press lands outside the popup."""
        try:
            position = event.globalPosition().toPoint()
        except AttributeError:
            position = event.globalPos()
        widget = QApplication.widgetAt(position)
        if widget is None or (widget is not self and not self.isAncestorOf(widget)):
            self._dismiss(restore_focus=False)

    def _handle_editor_key(self, event) -> bool:
        """Forward navigation keys from the focused editor to the popup."""
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self._dismiss(restore_focus=True)
            return True

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._commit_current()
            return True

        if modifiers == Qt.KeyboardModifier.NoModifier:
            if key == Qt.Key.Key_Down:
                self.select_next()
                return True
            if key == Qt.Key.Key_Up:
                self.select_prev()
                return True
            if key == Qt.Key.Key_PageDown:
                self.page_next()
                return True
            if key == Qt.Key.Key_PageUp:
                self.page_prev()
                return True
            if key == Qt.Key.Key_Home:
                self.list_view.setCurrentIndex(self.model.index(0, 0))
                return True
            if key == Qt.Key.Key_End:
                last = max(0, self.model.rowCount() - 1)
                self.list_view.setCurrentIndex(self.model.index(last, 0))
                return True

        if key in (
            Qt.Key.Key_Shift,
            Qt.Key.Key_Control,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Meta,
        ):
            return False

        self._dismiss(restore_focus=False)
        return False

    def eventFilter(self, obj, event) -> bool:
        """Route editor keys and close the popup on outside interaction."""
        event_type = event.type()
        if obj is self._editor:
            if event_type == QEvent.Type.KeyPress:
                return self._handle_editor_key(event)
            if event_type in (
                QEvent.Type.FocusOut,
                QEvent.Type.Hide,
                QEvent.Type.Close,
            ):
                self._dismiss(restore_focus=False)
            return False

        if event_type == QEvent.Type.MouseButtonPress:
            self._dismiss_if_outside(event)
        elif event_type in (
            QEvent.Type.WindowDeactivate,
            QEvent.Type.ApplicationDeactivate,
        ):
            self._dismiss(restore_focus=False)
        return super().eventFilter(obj, event)

    def hideEvent(self, event) -> None:
        """Remove filters and restore focus after the popup is hidden."""
        self._remove_filters()
        restore_focus = self._restore_focus
        self._restore_focus = False
        super().hideEvent(event)
        if restore_focus:
            self._focus_editor()

    def keyPressEvent(self, event) -> None:
        """Handle keys when the popup itself happens to receive focus."""
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self._dismiss(restore_focus=True)
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._commit_current()
            event.accept()
            return
        super().keyPressEvent(event)


class NavigationResultDelegate(QStyledItemDelegate):
    """Paints navigation results without relying on the completion delegate."""

    ROW_HEIGHT = 24

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._background = QColor("#1E1E1E")
        self._foreground = QColor("#D4D4D4")
        self._selected_background = QColor("#094771")
        self._selected_foreground = QColor("#FFFFFF")

    def retheme(self, background: QColor, foreground: QColor, selected: QColor) -> None:
        """Update the palette used by :meth:`paint`."""
        self._background = QColor(background)
        self._foreground = QColor(foreground)
        self._selected_background = QColor(selected)
        self._selected_foreground = (
            QColor("#FFFFFF") if selected.lightness() < 128 else QColor("#000000")
        )

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        """Draw one navigation result row."""
        result = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(result, NavigationResult):
            super().paint(painter, option, index)
            return

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.save()
        try:
            painter.fillRect(
                option.rect, self._selected_background if selected else self._background
            )
            painter.setPen(self._selected_foreground if selected else self._foreground)
            font = painter.font()
            font.setPointSize(9)
            painter.setFont(font)
            metrics = QFontMetrics(font)
            text = index.data(Qt.ItemDataRole.DisplayRole) or ""
            text_rect = option.rect.adjusted(8, 2, -8, -2)
            text = metrics.elidedText(
                text, Qt.TextElideMode.ElideMiddle, text_rect.width()
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text,
            )
        finally:
            painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        """Return the fixed row height used by the popup."""
        hint = super().sizeHint(option, index)
        hint.setHeight(max(hint.height(), self.ROW_HEIGHT))
        return hint
