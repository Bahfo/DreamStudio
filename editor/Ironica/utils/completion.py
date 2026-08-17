# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""
IntelliJ-style completion popup for a QScintilla editor.

The completion popup is intentionally implemented as a small stateful UI:
- the list and hint bar are part of the same popup window;
- popup geometry is calculated from content and available screen space;
- clicks/focus changes outside the popup close it;
- editor navigation and context changes invalidate the popup;
- Up/Down/PageUp/PageDown navigate without closing;
- Enter/Tab commit the current item and Escape cancels it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from PyQt6.QtCore import (
    pyqtSignal,
    QObject,
    QEvent,
    QPoint,
    QRect,
    QSize,
    Qt,
)
from PyQt6.QtGui import (
    QFontMetrics,
    QPainter,
    QColor,
    QIcon,
)
from PyQt6.QtWidgets import (
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QToolButton,
    QVBoxLayout,
    QSizePolicy,
    QListView,
    QFrame,
    QLabel,
    QStyle,
    QWidget,
)
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.Qsci import QsciScintilla


@dataclass
class CompletionItem:
    """One completion suggestion."""

    text: str
    insert_text: str = ""
    icon_name: str = ""
    signature: str = ""
    matched_ranges: List[Tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.insert_text:
            self.insert_text = self.text


class CompletionDelegate(QStyledItemDelegate):
    """Paints one completion row without depending on an external icon theme."""

    ROW_HEIGHT = 30
    ICON_SIZE = 18
    LEFT_PADDING = 10
    ICON_GAP = 8
    RIGHT_PADDING = 10
    SIGNATURE_GAP = 18

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self.color_selected = QColor("#2A2D32")
        self.color_normal = QColor("#D4D4D4")
        self.color_match = QColor("#4EB0CC")
        self.color_signature = QColor("#858585")
        self.color_icon = QColor("#4FC1FF")
        self.color_method = QColor("#C586C0")

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        item: Optional[CompletionItem] = index.data(Qt.ItemDataRole.UserRole)
        if item is None:
            return QSize(400, self.ROW_HEIGHT)

        fm = option.fontMetrics
        text_width = fm.horizontalAdvance(item.text)

        signature_width = 0
        if item.signature:
            signature_width = fm.horizontalAdvance(item.signature)

        width = (
            self.LEFT_PADDING
            + self.ICON_SIZE
            + self.ICON_GAP
            + text_width
            + (self.SIGNATURE_GAP + signature_width if signature_width else 0)
            + self.RIGHT_PADDING
        )

        return QSize(max(260, width), self.ROW_HEIGHT)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        item: Optional[CompletionItem] = index.data(Qt.ItemDataRole.UserRole)
        if item is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = option.rect

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, self.color_selected)
            painter.fillRect(
                rect.left(),
                rect.top(),
                3,
                rect.height(),
                self.color_match,
            )

        icon_rect = QRect(
            rect.left() + self.LEFT_PADDING,
            rect.top() + (rect.height() - self.ICON_SIZE) // 2,
            self.ICON_SIZE,
            self.ICON_SIZE,
        )

        icon = self._get_icon(item.icon_name)
        if icon is not None and not icon.isNull():
            icon.paint(
                painter,
                icon_rect,
                Qt.AlignmentFlag.AlignCenter,
            )
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(
                self.color_method
                if "method" in item.icon_name.lower()
                else self.color_icon
            )
            painter.drawEllipse(icon_rect.center(), 4, 4)

        fm = option.fontMetrics
        text_left = icon_rect.right() + self.ICON_GAP
        text_right = rect.right() - self.RIGHT_PADDING

        signature_width = 0
        if item.signature:
            signature_width = fm.horizontalAdvance(item.signature)
            signature_width = min(signature_width, max(0, rect.width() // 2))

        text_right -= signature_width
        if signature_width:
            text_right -= self.SIGNATURE_GAP

        text_rect = QRect(
            text_left,
            rect.top(),
            max(0, text_right - text_left),
            rect.height(),
        )

        if text_rect.width() > 0:
            self._draw_highlighted_text(
                painter,
                item.text,
                item.matched_ranges,
                text_rect,
                fm,
            )

        if item.signature and signature_width > 0:
            signature_rect = QRect(
                rect.right() - self.RIGHT_PADDING - signature_width,
                rect.top(),
                signature_width,
                rect.height(),
            )
            painter.setPen(self.color_signature)
            painter.drawText(
                signature_rect,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                fm.elidedText(
                    item.signature,
                    Qt.TextElideMode.ElideLeft,
                    signature_width,
                ),
            )

        painter.restore()

    def _draw_highlighted_text(
        self,
        painter: QPainter,
        text: str,
        ranges: List[Tuple[int, int]],
        rect: QRect,
        fm: QFontMetrics,
    ) -> None:
        x = rect.left()
        y = rect.top() + (rect.height() + fm.ascent() - fm.descent()) // 2

        for i, char in enumerate(text):
            matched = any(start <= i < start + length for start, length in ranges)
            painter.setPen(self.color_match if matched else self.color_normal)
            painter.drawText(x, y, char)
            x += fm.horizontalAdvance(char)

            if x >= rect.right():
                break

    def _get_icon(self, name: str) -> Optional[QIcon]:
        return None


class CompletionHintBar(QFrame):
    """
    Bottom hint/action strip.

    Four toolbuttons are provided deliberately as named actions so the IDE
    can replace their text/icons later without changing popup behavior.
    """

    action_triggered = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setObjectName("completionHintBar")
        self.setFixedHeight(38)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(6)

        self.hint_label = QLabel("Press Enter to insert the selected suggestion")
        self.hint_label.setObjectName("completionHintLabel")
        self.hint_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        layout.addWidget(self.hint_label, 1)

        self.buttons: List[QToolButton] = []

        button_specs = (
            ("accept", "↵", "Insert selected completion"),
            ("dot", "→.", "Insert selected completion and continue"),
            ("next_tip", "?", "Show next completion tip"),
            ("more", "⋮", "More completion actions"),
        )

        for action, text, tooltip in button_specs:
            button = QToolButton(self)
            button.setObjectName(f"completionHintButton_{action}")
            button.setText(text)
            button.setToolTip(tooltip)
            button.setAutoRaise(True)
            button.setFixedSize(24, 24)
            button.clicked.connect(
                lambda checked=False, name=action: (self.action_triggered.emit(name))
            )
            self.buttons.append(button)
            layout.addWidget(button)

        self.setStyleSheet("""
            QFrame#completionHintBar {
                border-top: 1px solid #3A3D42;
            }

            QLabel#completionHintLabel {
                background: transparent;
                padding: 0;
            }

            QToolButton {
                background: transparent;
                border-radius: 4px;
                font-weight: 500;
                font-size: 13px;
                border: none;
            }""")

    def set_hint(self, text: str) -> None:
        self.hint_label.setText(text)


class CompletionPopup(QWidget):
    """Frameless completion window containing the list and hint bar."""

    item_selected = pyqtSignal(CompletionItem)
    cancelled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint,
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating,
            True,
        )
        self.setObjectName("completionPopup")

        self._outer_layout = QVBoxLayout(self)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        self._outer_layout.setSpacing(0)

        self._container = QFrame(self)
        self._container.setObjectName("completionContainer")

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(1, 1, 1, 1)
        container_layout.setSpacing(0)

        self.list_view = QListView(self._container)
        self.list_view.setObjectName("completionList")
        self.list_view.setItemDelegate(CompletionDelegate(self.list_view))
        self.list_view.setUniformItemSizes(True)
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list_view.setFrameShape(QFrame.Shape.NoFrame)
        self.list_view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerItem)
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.model = QStandardItemModel(self)
        self.list_view.setModel(self.model)

        self.hint_bar = CompletionHintBar(self._container)

        container_layout.addWidget(self.list_view, 1)
        container_layout.addWidget(self.hint_bar, 0)
        self._outer_layout.addWidget(self._container)

        self.list_view.clicked.connect(self._on_clicked)
        self.list_view.doubleClicked.connect(self._on_double_clicked)
        self.hint_bar.action_triggered.connect(self._on_hint_action)

        self.setStyleSheet("""
            QWidget#completionPopup {
                background: transparent;
            }

            QFrame#completionContainer {
                border: 1px solid #0E0F10;
                border-radius: 7px;
            }

            QListView#completionList {
                border: none;
                outline: none;
                padding: 2px 0;
            }

            QListView#completionList::item {
                border: none;
                padding: 0;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 9px;
                margin: 2px;
            }

            QScrollBar::handle:vertical {
                border-radius: 4px;
                min-height: 24px;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
            """)

    def populate(self, items: List[CompletionItem]) -> bool:
        """Populate and resize. Returns False when there is nothing to show."""
        self.model.clear()

        if not items:
            self.hide()
            return False

        for item in items:
            qitem = QStandardItem()
            qitem.setData(item, Qt.ItemDataRole.UserRole)
            self.model.appendRow(qitem)

        self.list_view.setCurrentIndex(self.model.index(0, 0))

        self._resize_to_content(len(items))
        return True

    def _resize_to_content(self, count: int) -> None:
        delegate = self.list_view.itemDelegate()
        if not isinstance(delegate, CompletionDelegate):
            return

        rows = min(count, 10)
        row_height = delegate.ROW_HEIGHT
        hint_height = self.hint_bar.sizeHint().height()

        # Compute width from the actual content rather than using a fixed
        # 550px value. Long identifiers are allowed to determine the popup
        # width, but the result is capped to the current screen.
        fm = self.list_view.fontMetrics()
        content_width = 0

        for row in range(count):
            index = self.model.index(row, 0)
            item: Optional[CompletionItem] = index.data(Qt.ItemDataRole.UserRole)
            if item is None:
                continue

            text_width = fm.horizontalAdvance(item.text)
            signature_width = (
                fm.horizontalAdvance(item.signature) if item.signature else 0
            )

            candidate_width = (
                delegate.LEFT_PADDING
                + delegate.ICON_SIZE
                + delegate.ICON_GAP
                + text_width
                + (delegate.SIGNATURE_GAP + signature_width if signature_width else 0)
                + delegate.RIGHT_PADDING
            )
            content_width = max(content_width, candidate_width)

        screen = QApplication.screenAt(self.pos())
        if screen is None:
            screen = QApplication.primaryScreen()

        if screen is None:
            available_width = 1200
            available_height = 800
        else:
            available = screen.availableGeometry()
            available_width = available.width()
            available_height = available.height()

        width = min(
            max(420, int(content_width + 8)),
            max(420, int(available_width * 0.60)),
        )

        desired_height = rows * row_height + 4 + hint_height + 2

        # If the popup cannot fit, the list gets a scrollbar. The viewport
        # height is still an exact multiple of the row height, preventing the
        # last row from being clipped halfway through.
        max_height = max(
            row_height + hint_height + 8,
            int(available_height * 0.60),
        )
        max_list_rows = max(
            1,
            (max_height - hint_height - 6) // row_height,
        )
        visible_rows = min(rows, max_list_rows)

        height = visible_rows * row_height + hint_height + 6

        self.resize(width, height)

    def select_next(self) -> None:
        self._move_selection(1)

    def select_prev(self) -> None:
        self._move_selection(-1)

    def page_next(self) -> None:
        self._move_selection(
            max(1, self.list_view.viewport().height() // max(1, self._row_height()))
        )

    def page_prev(self) -> None:
        self._move_selection(
            -max(1, self.list_view.viewport().height() // max(1, self._row_height()))
        )

    def _move_selection(self, delta: int) -> None:
        count = self.model.rowCount()
        if count == 0:
            return

        current = self.list_view.currentIndex().row()
        if current < 0:
            current = 0

        new_row = max(0, min(count - 1, current + delta))
        self.list_view.setCurrentIndex(self.model.index(new_row, 0))
        self.list_view.scrollTo(
            self.list_view.currentIndex(),
            QAbstractItemView.ScrollHint.EnsureVisible,
        )

    def commit_current(self) -> None:
        index = self.list_view.currentIndex()
        if not index.isValid():
            return

        item: Optional[CompletionItem] = index.data(Qt.ItemDataRole.UserRole)
        if item is None:
            return

        self.item_selected.emit(item)
        self.hide()

    def cancel(self) -> None:
        self.hide()
        self.cancelled.emit()

    def _on_clicked(self, index) -> None:
        if index.isValid():
            self.commit_current()

    def _on_double_clicked(self, index) -> None:
        if index.isValid():
            self.commit_current()

    def _on_hint_action(self, action: str) -> None:
        if action in ("accept", "dot"):
            self.commit_current()
        elif action == "next_tip":
            self.hint_bar.set_hint(
                "Use ↑/↓ to navigate, Enter or Tab to insert, Esc to close"
            )
        elif action == "more":
            self.hint_bar.set_hint(
                "Completion actions are available from the editor menu"
            )

    def _row_height(self) -> int:
        delegate = self.list_view.itemDelegate()
        return delegate.ROW_HEIGHT if isinstance(delegate, CompletionDelegate) else 30


class CompletionController(QObject):
    """
    Connects completion behavior to QsciScintilla.

    The controller deliberately keeps the popup non-focusable. The editor
    remains the keyboard owner, while the controller intercepts completion
    navigation/commit/cancel keys.
    """

    def __init__(self, editor: QsciScintilla) -> None:
        super().__init__(editor)

        self.editor = editor
        self.popup = CompletionPopup(editor.window())
        self.popup.item_selected.connect(self._insert_completion)

        self.editor.installEventFilter(self)
        QApplication.instance().installEventFilter(self)

        try:
            self.editor.textChanged.connect(self._on_text_changed)
        except Exception:
            pass

        self._current_prefix = ""
        self._active = False
        self._committing = False
        self._last_cursor_pos = -1
        self._mouse_selection_guard = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self.editor:
            return self._filter_editor_event(event)

        if obj is QApplication.instance():
            return self._filter_application_event(event)

        return super().eventFilter(obj, event)

    def _filter_editor_event(self, event: QEvent) -> bool:
        event_type = event.type()

        if event_type == QEvent.Type.KeyPress:
            return self._handle_editor_key(event)

        if event_type in (
            QEvent.Type.FocusOut,
            QEvent.Type.Hide,
            QEvent.Type.Close,
        ):
            self._close()

        if event_type == QEvent.Type.MouseButtonPress:
            self._close()

        return False

    def _handle_editor_key(self, event: QEvent) -> bool:
        key_event = event
        key = key_event.key()
        modifiers = key_event.modifiers()

        if not self.popup.isVisible():
            return False

        # Completion list navigation.
        if key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.NoModifier:
            self.popup.select_next()
            return True

        if key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.NoModifier:
            self.popup.select_prev()
            return True

        if key == Qt.Key.Key_PageDown:
            self.popup.page_next()
            return True

        if key == Qt.Key.Key_PageUp:
            self.popup.page_prev()
            return True

        # Explicit cancellation.
        if key == Qt.Key.Key_Escape:
            self._close()
            return True

        # Commit completion.
        if key in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Tab,
        ):
            self.popup.commit_current()
            return True

        cursor_keys = {
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
            Qt.Key.Key_Home,
            Qt.Key.Key_End,
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
        }

        if key in cursor_keys:
            self._close()
            return False

        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            return False

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if key in (
                Qt.Key.Key_A,
                Qt.Key.Key_C,
                Qt.Key.Key_X,
                Qt.Key.Key_V,
                Qt.Key.Key_Z,
                Qt.Key.Key_Y,
                Qt.Key.Key_Left,
                Qt.Key.Key_Right,
                Qt.Key.Key_Home,
                Qt.Key.Key_End,
            ):
                self._close()
                return False

        if self._is_completion_terminating_key(key_event):
            self._close()

        return False

    def _filter_application_event(self, event: QEvent) -> bool:
        if not self.popup.isVisible():
            return False

        event_type = event.type()

        if event_type == QEvent.Type.WindowDeactivate:
            self._close()
            return False

        if event_type == QEvent.Type.ApplicationDeactivate:
            self._close()
            return False

        if event_type == QEvent.Type.MouseButtonPress:
            mouse_event = event
            global_pos = mouse_event.globalPosition().toPoint()
            widget = QApplication.widgetAt(global_pos)

            if widget is None:
                self._close()
                return False

            if self.popup is widget or self.popup.isAncestorOf(widget):
                return False

            self._close()
            return False

        if event_type == QEvent.Type.FocusOut:
            focus_widget = QApplication.focusWidget()
            if (
                focus_widget is not self.editor
                and focus_widget is not self.popup
                and not (
                    focus_widget is not None and self.popup.isAncestorOf(focus_widget)
                )
            ):
                self._close()

        return False

    def _on_text_changed(self) -> None:
        if self._committing:
            return

        if getattr(self.editor, "_is_replacing", False):
            self._close()
            return

        pos = self.editor.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)

        if pos != self._last_cursor_pos:
            self._last_cursor_pos = pos

        line, col = self.editor.lineIndexFromPosition(pos)
        text_before_cursor = self.editor.text(line)[:col]

        match = re.search(r"\b([A-Za-z_]\w*)$", text_before_cursor)

        if not match:
            self._current_prefix = ""
            self._close()
            return

        prefix = match.group(1)
        self._current_prefix = prefix

        if len(prefix) < 2:
            self._close()
            return

        self._request_completions()

    def _request_completions(self) -> None:
        items: List[CompletionItem] = []

        provider = getattr(self.editor, "current_provider", None)

        if provider and hasattr(provider, "get_completions"):
            try:
                items = (
                    provider.get_completions(
                        self.editor.text(),
                        self.editor.getCursorPosition(),
                        self._current_prefix,
                    )
                    or []
                )
            except Exception:
                items = []

        if not items:
            items = self._get_document_tokens()

        if items:
            self._show_popup(items)
        else:
            self._close()

    def _get_document_tokens(self) -> List[CompletionItem]:
        document_text = self.editor.text()
        words = set(re.findall(r"\b[a-zA-Z_]\w*\b", document_text))

        prefix_lower = self._current_prefix.lower()
        results: List[CompletionItem] = []

        for word in words:
            if word != self._current_prefix and word.lower().startswith(prefix_lower):
                results.append(
                    CompletionItem(
                        text=word,
                        icon_name="symbol-text",
                        signature="text",
                        matched_ranges=[(0, len(self._current_prefix))],
                    )
                )

        return sorted(
            results,
            key=lambda item: (
                item.text.lower(),
                item.text,
            ),
        )

    def _show_popup(self, items: List[CompletionItem]) -> None:
        if not self.popup.populate(items):
            self._close()
            return

        pos = self.editor.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)

        x = self.editor.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, pos)
        y = self.editor.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, pos)
        line_index = self.editor.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, pos)
        line_height = self.editor.SendScintilla(
            QsciScintilla.SCI_TEXTHEIGHT, line_index
        )

        x = max(0, x)

        below = self.editor.mapToGlobal(QPoint(x, y + line_height + 3))
        above = self.editor.mapToGlobal(QPoint(x, y - self.popup.height() - 3))

        screen = QApplication.screenAt(below)
        if screen is None:
            screen = QApplication.primaryScreen()

        if screen is None:
            self.popup.move(below)
            self.popup.show()
            self._active = True
            return

        available = screen.availableGeometry()
        margin = 8

        if below.y() + self.popup.height() <= available.bottom() - margin:
            popup_y = below.y()
        elif above.y() >= available.top() + margin:
            popup_y = above.y()
        else:
            popup_y = max(
                available.top() + margin,
                min(
                    below.y(),
                    available.bottom() - self.popup.height() - margin,
                ),
            )

        popup_x = max(
            available.left() + margin,
            min(
                below.x(),
                available.right() - self.popup.width() - margin,
            ),
        )

        self.popup.move(popup_x, popup_y)
        self.popup.show()
        self._active = True

    def _insert_completion(self, item: CompletionItem) -> None:
        if self._committing:
            return

        self._committing = True
        self._close()

        try:
            line, col = self.editor.getCursorPosition()
            start_col = max(0, col - len(self._current_prefix))

            self.editor.beginUndoAction()
            try:
                self.editor.setSelection(line, start_col, line, col)
                self.editor.replaceSelectedText(item.insert_text)
                self.editor.setCursorPosition(line, start_col + len(item.insert_text))
            finally:
                self.editor.endUndoAction()
        finally:
            self._committing = False

    def close(self) -> None:
        """Public cancellation hook for tab/workspace/editor changes."""
        self._close()

    def _close(self) -> None:
        if self.popup.isVisible():
            self.popup.hide()

        self._active = False

    @staticmethod
    def _is_completion_terminating_key(key_event: QEvent) -> bool:
        text = key_event.text()
        if not text:
            return False

        return text in {
            " ",
            "\t",
            "\n",
            "\r",
            "(",
            ")",
            "[",
            "]",
            "{",
            "}",
            ",",
            ":",
            ";",
            ".",
            "'",
            '"',
            "`",
            "+",
            "-",
            "*",
            "/",
            "\\",
            "=",
            "<",
            ">",
            "!",
            "&",
            "|",
            "#",
            "?",
        }
