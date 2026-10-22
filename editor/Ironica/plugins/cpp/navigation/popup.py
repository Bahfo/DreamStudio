"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Multi-match navigation popup for C++ GoTo functionality.
"""

from __future__ import annotations

from typing import List, Optional, Callable

from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtWidgets import (
    QStyle,
    QWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)
from PyQt6.QtGui import QStandardItem
from PyQt6.QtGui import QColor, QFontMetrics, QPainter, QCursor

from ..navigation.engine import NavigationResult
from editor.Ironica.utils.completion import CompletionPopup


class NavigationPopup(CompletionPopup):
    """Popup for showing multiple navigation targets."""

    target_selected = pyqtSignal(NavigationResult)
    cancelled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Go To")
        self._results: List[NavigationResult] = []
        self._on_select: Optional[Callable[[NavigationResult], None]] = None

    def set_results(
        self,
        results: List[NavigationResult],
        on_select: Optional[Callable[[NavigationResult], None]] = None,
    ) -> None:
        """Set the navigation results to display."""
        self._results = results
        self._on_select = on_select
        self.model.clear()

        for result in results:
            item = QStandardItem()
            item.setData(result, Qt.ItemDataRole.UserRole)
            display = self._format_result(result)
            item.setText(display)
            self.model.appendRow(item)

        if self.model.rowCount() > 0:
            self.list_view.setCurrentIndex(self.model.index(0, 0))

    def _format_result(self, result: NavigationResult) -> str:
        """Format a navigation result for display."""
        rel_path = result.file_path
        try:
            import os

            cwd = os.getcwd()
            if rel_path.startswith(cwd):
                rel_path = os.path.relpath(rel_path, cwd)
        except Exception:
            pass

        kind_icon = {
            "definition": "📍",
            "declaration": "📝",
            "implementation": "⚙️",
            "reference": "🔗",
        }.get(result.kind, "•")

        return f"{kind_icon} {rel_path}:{result.line}:{result.col}  —  {result.display_name}"

    def _on_clicked(self, index):
        """Handle single click."""
        item = self.model.itemFromIndex(index)
        if item:
            result = item.data(Qt.ItemDataRole.UserRole)
            if result and self._on_select:
                self._on_select(result)
            self.target_selected.emit(result)
            self.hide()

    def _on_double_clicked(self, index):
        """Handle double click."""
        self._on_clicked(index)

    def show_at_cursor(self, editor) -> None:
        """Show the popup near the cursor position."""
        try:
            line, col = editor.getCursorPosition()
            point = editor.mapToGlobal(editor.SCI_POINTXFROMPOSITION, 0)
            x = editor.SendScintilla(
                editor.SCI_POINTXFROMPOSITION, editor.positionFromLine(line) + col
            )
            y = editor.SendScintilla(
                editor.SCI_POINTYFROMPOSITION, editor.positionFromLine(line) + col
            )
            point = editor.mapToGlobal(
                QPoint(x, y + editor.SendScintilla(editor.SCI_TEXTHEIGHT, line))
            )
            self.move(point)
        except Exception:
            self.move(QCursor.pos())
        self.show()
        self.raise_()
        self.activateWindow()

    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() in (Qt.Key.Key_Escape,):
            self.cancelled.emit()
            self.hide()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            index = self.list_view.currentIndex()
            if index.isValid():
                self._on_clicked(index)
        else:
            super().keyPressEvent(event)


class NavigationResultDelegate(QStyledItemDelegate):
    """Custom delegate for navigation results."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg = QColor("#1E1E1E")
        self._fg = QColor("#D4D4D4")
        self._sel_bg = QColor("#094771")
        self._sel_fg = QColor("#FFFFFF")

    def retheme(self, bg: QColor, fg: QColor, sel: QColor) -> None:
        self._bg = bg
        self._fg = fg
        self._sel_bg = sel
        self._sel_fg = QColor("#FFFFFF") if sel.lightness() < 128 else QColor("#000000")

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """Paint the navigation result item."""
        result = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(result, NavigationResult):
            super().paint(painter, option, index)
            return

        painter.save()
        rect = option.rect
        selected = option.state & QStyle.StateFlag.State_Selected

        bg_color = self._sel_bg if selected else self._bg
        fg_color = self._sel_fg if selected else self._fg

        painter.fillRect(rect, bg_color)
        painter.setPen(fg_color)

        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        fm = QFontMetrics(font)

        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        painter.drawText(
            rect.adjusted(8, 2, -8, -2),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            text,
        )
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index):
        """Return size hint for items."""
        return super().sizeHint(option, index)
