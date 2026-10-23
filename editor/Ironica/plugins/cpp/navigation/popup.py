from __future__ import annotations

from typing import Callable, Optional, Sequence

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QFontMetrics, QPainter, QStandardItem
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem, QWidget

from ..navigation.engine import NavigationResult
from editor.Ironica.utils.completion import CompletionPopup


class NavigationPopup(CompletionPopup):
    target_selected = pyqtSignal(NavigationResult)
    cancelled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Go To")
        self._on_select: Optional[Callable[[NavigationResult], None]] = None
        self._delegate = NavigationResultDelegate(self.list_view)
        self.list_view.setItemDelegate(self._delegate)

    def set_results(
        self,
        results: Sequence[NavigationResult],
        on_select: Optional[Callable[[NavigationResult], None]] = None,
    ) -> None:
        self._on_select = on_select
        self.model.clear()

        for result in results:
            item = QStandardItem(self._format_result(result))
            item.setData(result, Qt.ItemDataRole.UserRole)
            self.model.appendRow(item)

        if self.model.rowCount():
            self.list_view.setCurrentIndex(self.model.index(0, 0))

    @staticmethod
    def _format_result(result: NavigationResult) -> str:
        labels = {
            "definition": "Definition",
            "declaration": "Declaration",
            "implementation": "Implementation",
            "reference": "Reference",
            "include": "Include",
        }
        label = labels.get(result.kind, result.kind.title())
        return (
            f"{label}  {result.file_path}:{result.line + 1}:{result.col + 1}"
            f"  —  {result.display_name}"
        )

    def _on_clicked(self, index) -> None:
        if not index.isValid():
            return
        item = self.model.itemFromIndex(index)
        result = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not isinstance(result, NavigationResult):
            return

        self.hide()
        if self._on_select is not None:
            self._on_select(result)
        self.target_selected.emit(result)

    def _on_double_clicked(self, index) -> None:
        self._on_clicked(index)

    def show_at_cursor(self, editor) -> None:
        try:
            line, column = editor.getCursorPosition()
            position = editor.positionFromLineIndex(line, column)
            x = editor.SendScintilla(editor.SCI_POINTXFROMPOSITION, 0, position)
            y = editor.SendScintilla(editor.SCI_POINTYFROMPOSITION, 0, position)
            height = editor.SendScintilla(editor.SCI_TEXTHEIGHT, line)
            self.move(editor.mapToGlobal(QPoint(int(x), int(y + height))))
        except (AttributeError, RuntimeError, TypeError, ValueError):
            self.move(QCursor.pos())

        self.show()
        self.raise_()
        self.activateWindow()
        self.list_view.setFocus(Qt.FocusReason.PopupFocusReason)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.hide()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_clicked(self.list_view.currentIndex())
            event.accept()
            return
        super().keyPressEvent(event)


class NavigationResultDelegate(QStyledItemDelegate):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._background = QColor("#1E1E1E")
        self._foreground = QColor("#D4D4D4")
        self._selected_background = QColor("#094771")
        self._selected_foreground = QColor("#FFFFFF")

    def retheme(self, background: QColor, foreground: QColor, selected: QColor) -> None:
        self._background = QColor(background)
        self._foreground = QColor(foreground)
        self._selected_background = QColor(selected)
        self._selected_foreground = (
            QColor("#FFFFFF") if selected.lightness() < 128 else QColor("#000000")
        )

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
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

    def sizeHint(self, option: QStyleOptionViewItem, index):
        hint = super().sizeHint(option, index)
        return hint.expandedTo(hint.__class__(hint.width(), 24))
