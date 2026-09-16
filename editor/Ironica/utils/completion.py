# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""
The main completion widget for Ironica.
"""

from __future__ import annotations

from editor import *
from editor.utils.resource_path import resource_path

COMPLETION_DEBOUNCE_MS: int = 40


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
    """Paints one completion row with icon/badge rendering."""

    ROW_HEIGHT = 30
    ICON_SIZE = 18
    LEFT_PADDING = 10
    ICON_GAP = 8
    RIGHT_PADDING = 10
    SIGNATURE_GAP = 18

    # Absolute icon directory resolution relative to this file
    _ICON_DIR = resource_path("assets/editor")

    _KIND_ICON_MAP = {
        "function": "function.png",
        "method": "function.png",
        "class": "class.png",
        "module": "module.png",
        "keyword": "keyword.png",
        "builtin": "keyword.png",
        "variable": "variable.png",
        "instance": "variable.png",
        "property": "property.png",
        "param": "parameter.png",
        "parameter": "parameter.png",
        "enum": "enum.png",
        "import": "module.png",
        "statement": "text.png",
        "text": "text.png",
        "path": "path.png",
        "symbol-text": "text.png",
        "snippet": "snippet.png",
    }

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self.color_selected = QColor("#2A2D32")
        self.color_hover = QColor("#2A2D32")
        self.color_normal = QColor("#D4D4D4")
        self.color_match = QColor("#4EB0CC")
        self.color_signature = QColor("#858585")
        self.color_icon = QColor("#4FC1FF")
        self.color_method = QColor("#C586C0")

    def retheme(self, bg: QColor, fg: QColor, sel: QColor) -> None:
        if bg.lightness() < 128:
            self.color_selected = bg.lighter(135)
            self.color_hover = bg.lighter(120)
            self.color_normal = fg
            self.color_signature = fg.darker(140)
            self.color_match = sel if sel.isValid() else QColor("#4EB0CC")
            self.color_icon = sel if sel.isValid() else QColor("#4FC1FF")
            self.color_method = fg.lighter(130)
        else:
            self.color_selected = bg.darker(110)
            self.color_hover = bg.darker(105)
            self.color_normal = fg
            self.color_signature = fg.darker(130)
            self.color_match = sel if sel.isValid() else QColor("#4EB0CC")
            self.color_icon = sel if sel.isValid() else QColor("#4FC1FF")
            self.color_method = fg.darker(120)

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
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(rect, self.color_hover)

        icon_rect = QRect(
            rect.left() + self.LEFT_PADDING,
            rect.top() + (rect.height() - self.ICON_SIZE) // 2,
            self.ICON_SIZE,
            self.ICON_SIZE,
        )

        icon = self._get_icon(item.icon_name)
        if icon is not None and not icon.isNull():
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)
        else:
            # Fallback: Render a clean colored letter badge if PNG is missing
            self._draw_fallback_badge(painter, icon_rect, item.icon_name)

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

    def _draw_fallback_badge(self, painter: QPainter, rect: QRect, kind: str) -> None:
        kind_lower = kind.lower()
        badge_char = kind[0].upper() if kind else "V"

        if "snippet" in kind_lower:
            bg_color = QColor("#D7BA7D")
            badge_char = "S"
        elif "func" in kind_lower or "method" in kind_lower:
            bg_color = QColor("#C586C0")
            badge_char = "f"
        elif "class" in kind_lower:
            bg_color = QColor("#4EC0E8")
            badge_char = "C"
        elif "module" in kind_lower or "import" in kind_lower:
            bg_color = QColor("#DCDCAA")
            badge_char = "M"
        elif "keyword" in kind_lower or "builtin" in kind_lower:
            bg_color = QColor("#569CD6")
            badge_char = "K"
        else:
            bg_color = QColor("#4FC1FF")
            badge_char = "v"

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(rect, 3, 3)

        font = painter.font()
        font.setPixelSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#1E1E1E"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, badge_char)

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
        if not name:
            return None
        filename = self._KIND_ICON_MAP.get(name.lower())
        if filename is None:
            return None
        full_path = os.path.join(self._ICON_DIR, filename)
        if not os.path.exists(full_path):
            return None
        return QIcon(full_path)


class CompletionHintBar(QFrame):
    """Bottom hint/action strip."""

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

        mono_font = QFont("Monospace")
        mono_font.setPointSize(11)
        mono_font.setWeight(QFont.Weight.DemiBold)

        for action, text, tooltip in button_specs:
            button = QToolButton(self)
            button.setObjectName(f"completionHintButton_{action}")
            button.setText(text)
            button.setToolTip(tooltip)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setFont(mono_font)
            button.setFixedSize(28, 28)

            pal = button.palette()
            pal.setColor(QPalette.ColorRole.ButtonText, QColor("#D4D4D4"))
            pal.setColor(QPalette.ColorRole.Window, QColor("transparent"))
            button.setPalette(pal)

            button.clicked.connect(
                lambda checked=False, name=action: self.action_triggered.emit(name)
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
                border: 1px solid transparent;
                border-radius: 4px;
                font-weight: 600;
                font-size: 13px;
                color: #D4D4D4;
                padding: 0;
            }
            QToolButton:hover {
                background: #3A3D42;
                border: 1px solid #555555;
            }""")

    def retheme(self, bg: QColor, fg: QColor, sel: QColor) -> None:
        if bg.lightness() < 128:
            border_color = bg.lighter(150).name()
            hover_bg = bg.lighter(130).name()
            hover_border = bg.lighter(170).name()
        else:
            border_color = bg.darker(115).name()
            hover_bg = bg.darker(108).name()
            hover_border = bg.darker(125).name()

        btn_color = fg.name()

        self.setStyleSheet(f"""
            QFrame#completionHintBar {{
                border-top: 1px solid {border_color};
            }}
            QLabel#completionHintLabel {{
                background: transparent;
                padding: 0;
                color: {btn_color};
            }}
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                font-weight: 600;
                font-size: 13px;
                color: {btn_color};
                padding: 0;
            }}
            QToolButton:hover {{
                background: {hover_bg};
                border: 1px solid {hover_border};
            }}""")

        for button in self.buttons:
            pal = button.palette()
            pal.setColor(QPalette.ColorRole.ButtonText, fg)
            button.setPalette(pal)

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

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
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
        self._item_fg = QColor("#D4D4D4")

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
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }""")

    def retheme(self, bg: QColor, fg: QColor, sel: QColor) -> None:
        delegate = self.list_view.itemDelegate()
        if isinstance(delegate, CompletionDelegate):
            delegate.retheme(bg, fg, sel)

        self._item_fg = QColor(fg)

        if bg.lightness() < 128:
            border_color = bg.lighter(155).name()
            sb_handle = bg.lighter(140).name()
        else:
            border_color = bg.darker(115).name()
            sb_handle = bg.darker(115).name()

        self.setStyleSheet(f"""
            QWidget#completionPopup {{
                background: transparent;
            }}
            QFrame#completionContainer {{
                border: 1px solid {border_color};
                border-radius: 7px;
            }}
            QListView#completionList {{
                border: none;
                outline: none;
                padding: 2px 0;
            }}
            QListView#completionList::item {{
                border: none;
                padding: 0;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 9px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {sb_handle};
                border-radius: 4px;
                min-height: 24px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}""")
        self.hint_bar.retheme(bg, fg, sel)

    def populate(self, items: List[CompletionItem]) -> bool:
        """Populate and resize."""
        self.model.clear()

        if not items:
            self.hide()
            return False

        fg = self._item_fg
        for item in items:
            qitem = QStandardItem()
            qitem.setData(item, Qt.ItemDataRole.UserRole)
            qitem.setForeground(fg)
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
            available_width, available_height = 1200, 800
        else:
            available = screen.availableGeometry()
            available_width, available_height = available.width(), available.height()

        width = min(
            max(450, int(content_width + 12)),
            max(450, int(available_width * 0.65)),
        )

        max_height = max(row_height + hint_height + 8, int(available_height * 0.60))
        max_list_rows = max(1, (max_height - hint_height - 6) // row_height)
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
    """Connects completion behavior to QsciScintilla with debouncing."""

    def __init__(self, editor: QsciScintilla) -> None:
        super().__init__(editor)

        self.editor = editor
        self.popup = CompletionPopup(editor.window())
        self.popup.item_selected.connect(self._insert_completion)

        self.editor.installEventFilter(self)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        try:
            self.editor.destroyed.connect(self.close)
        except Exception:
            pass

        # NOTE: Short debounce only gates the very first popup. While the
        # popup is open every keystroke re-filters cached items instantly;
        # the timer merely schedules a background refresh of the results.
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(COMPLETION_DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._request_completions)

        try:
            self.editor.textChanged.connect(self._on_text_changed)
        except Exception:
            pass

        self._current_prefix = ""
        self._current_ident = ""
        self._active = False
        self._committing = False
        self._last_cursor_pos = -1
        self._connected_manager = None
        self._cached_items: List[CompletionItem] = []
        self._cache_ident = ""
        self._requested_context = ("", "")

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
            QEvent.Type.MouseButtonPress,
        ):
            self._close()

        return False

    def _handle_editor_key(self, event: QEvent) -> bool:
        key_event = event
        key = key_event.key()
        modifiers = key_event.modifiers()

        if not self.popup.isVisible():
            return False

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

        if key == Qt.Key.Key_Escape:
            self._close()
            return True

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
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
            self._close()
            return False

        if self._is_completion_terminating_key(key_event):
            self._close()

        return False

    def _filter_application_event(self, event: QEvent) -> bool:
        if not self.popup.isVisible():
            return False

        event_type = event.type()

        if event_type in (
            QEvent.Type.WindowDeactivate,
            QEvent.Type.ApplicationDeactivate,
        ):
            self._close()
            return False

        if event_type == QEvent.Type.MouseButtonPress:
            mouse_event = event
            global_pos = mouse_event.globalPosition().toPoint()
            widget = QApplication.widgetAt(global_pos)

            if widget is None or (
                widget is not self.popup and not self.popup.isAncestorOf(widget)
            ):
                self._close()

        return False

    def _on_text_changed(self) -> None:
        if self._committing or getattr(self.editor, "_is_replacing", False):
            self._close()
            return

        pos = self.editor.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
        self._last_cursor_pos = pos

        line, col = self.editor.lineIndexFromPosition(pos)
        text_before_cursor = self.editor.text(line)[:col]

        # Snippet trigger: a trailing "/xxx" at the cursor.  A single "/" must
        # trigger immediately so the user can discover available snippets.
        snippet_match = re.search(r"/[A-Za-z0-9_]*$", text_before_cursor)
        if snippet_match:
            prefix = snippet_match.group(0)
            ident = ""
            self._current_prefix = prefix
            self._current_ident = ident

            if self.popup.isVisible() and self._cached_items and ident == self._cache_ident:
                self._refresh_from_cache()
            else:
                # Show snippets instantly for "/" prefix even before debounce fires
                # when no cached provider results exist.
                if prefix == "/":
                    # Populate synchronously so discovery is instant
                    snippet_items = self._get_snippet_completions()
                    if snippet_items:
                        self._cached_items = list(snippet_items)
                        self._cache_ident = ""
                        self.popup.populate(list(snippet_items))
                        self._show_popup(list(snippet_items))
                        return
            self._debounce_timer.start()
            return

        # FIX: Allow dot expressions (e.g., 'os.' or 'os.pa') to trigger completion
        match = re.search(r"([A-Za-z_]\w*)\.([A-Za-z_]\w*)?$", text_before_cursor)
        if not match:
            match = re.search(r"([A-Za-z_]\w*)$", text_before_cursor)

        if not match:
            self._current_prefix = ""
            self._close()
            return

        groups = match.groups()
        dot = "." in (match.group(0) or "")
        if dot:
            ident = groups[0] or ""
            prefix = groups[1] if len(groups) > 1 and groups[1] else ""
        else:
            ident = ""
            prefix = groups[0] or ""
        self._current_prefix = prefix or ""
        self._current_ident = ident

        # Require dot OR at least 2 characters to auto-trigger
        if not dot and len(self._current_prefix) < 2:
            self._close()
            return

        # Fast path: while the popup is already open, narrow the cached
        # results synchronously so the list tracks every keystroke with
        # zero perceived latency. The debounce only refreshes the cache.
        if self.popup.isVisible() and self._cached_items and ident == self._cache_ident:
            self._refresh_from_cache()

        # Restart single-shot timer (Debounce)
        self._debounce_timer.start()

    def _get_snippet_completions(self) -> List[CompletionItem]:
        """Return snippet CompletionItems matching the current prefix.

        Snippets are sourced from ``editor.snippet_map`` (trigger -> body)
        and, as fallback, from ``LanguageRegistry.get_snippets(lang)``.
        A prefix starting with ``/`` requires an exact ``/``-prefixed
        match; otherwise the leading ``/`` is ignored so typing ``Cl``
        also surfaces ``/Class``.
        """
        prefix = self._current_prefix or ""
        prefix_lower = prefix.lower()
        stripped_prefix = prefix.lstrip("/").lower()
        is_snippet_prefix = prefix.startswith("/")

        # Collect trigger -> body, preserving bodies from snippet_map
        triggers: dict[str, str] = {}
        snippet_map = getattr(self.editor, "snippet_map", {}) or {}
        for trig, body in snippet_map.items():
            triggers[trig] = body

        lang = getattr(self.editor, "current_lang", None)
        if lang:
            try:
                from editor.Ironica.language_engine import LanguageRegistry

                for trig in LanguageRegistry.get_snippets(lang):
                    if trig not in triggers:
                        triggers[trig] = trig
            except Exception:
                pass

        # If still empty, fall back to any snippet_map entries already collected
        if not triggers:
            return []

        result: List[CompletionItem] = []
        for trig, body in triggers.items():
            trig_lower = trig.lower()
            trig_stripped = trig.lstrip("/").lower()

            if is_snippet_prefix:
                if not trig_lower.startswith(prefix_lower):
                    continue
            else:
                if not prefix_lower:
                    continue
                if not trig_stripped.startswith(prefix_lower):
                    continue

            insert = body if body and body != trig else trig
            first_line = ""
            if isinstance(body, str) and body and body != trig:
                first_line = body.split("\n")[0].strip()
                if len(first_line) > 60:
                    first_line = first_line[:57] + "..."
            signature = first_line or "snippet"

            if is_snippet_prefix:
                matched = [(0, len(prefix))]
            else:
                # Highlight starts after leading "/" if present
                offset = 1 if trig.startswith("/") else 0
                matched = [(offset, len(prefix))]

            result.append(
                CompletionItem(
                    text=trig,
                    insert_text=insert,
                    icon_name="snippet",
                    signature=signature,
                    matched_ranges=matched,
                )
            )

        result.sort(key=lambda item: item.text.lower())
        return result

    def _refresh_from_cache(self) -> None:
        """Re-populate the popup from cached items for the current prefix.

        Returns without touching the popup when nothing matches, letting
        the pending background request decide the final state.  Snippet
        matches are merged synchronously so ``/``-triggered discovery
        feels instant.
        """
        # Snippet prefix: show snippet matches directly
        if self._current_prefix.startswith("/"):
            snippet_matches = self._get_snippet_completions()
            # Also filter cached items that are snippets (if previously cached)
            cached_matches = [
                item
                for item in self._cached_items
                if item.text.lower().startswith(self._current_prefix.lower())
            ]
            # Prefer synchronous snippet matches; they are always fresh
            combined = snippet_matches if snippet_matches else cached_matches
            if combined:
                self.popup.populate(combined)
            return

        matches = [
            item
            for item in self._cached_items
            if item.text.lower().startswith(self._current_prefix.lower())
        ]
        # Merge snippets that match this word prefix
        snippet_matches = self._get_snippet_completions()
        existing = {m.text for m in matches}
        for s in snippet_matches:
            if s.text not in existing:
                matches.append(s)

        if matches:
            self.popup.populate(matches)

    def _request_completions(self) -> None:
        self._requested_context = (self._current_ident, self._current_prefix)
        provider = getattr(self.editor, "current_provider", None)

        # Snippet-only prefix: bypass language provider and show snippets instantly
        if self._current_prefix.startswith("/"):
            snippet_items = self._get_snippet_completions()
            self._present_items(snippet_items)
            return

        if provider is None:
            items = self._get_document_tokens()
            # Merge snippet completions even without a provider
            snippet_items = self._get_snippet_completions()
            existing = {i.text for i in items}
            for s in snippet_items:
                if s.text not in existing:
                    items.append(s)
            if items:
                self._show_popup(items)
            else:
                self._close()
            return

        completion_manager = getattr(provider, "completion_manager", None)
        if completion_manager is not None:
            self._connect_to_manager(completion_manager)
            completion_manager.request(
                self.editor.text(),
                *self.editor.getCursorPosition(),
                getattr(provider, "file_path", None),
            )
            return

        if hasattr(provider, "get_completions"):
            try:
                raw_items = provider.get_completions(
                    self.editor.text(),
                    self.editor.getCursorPosition(),
                    self._current_prefix,
                )
                items = self._coerce_items(raw_items or [])
            except Exception:
                items = []
        else:
            items = []

        self._present_items(items)

    def _present_items(self, items: List[CompletionItem]) -> None:
        """Cache fresh results and display those matching the typed prefix.

        The cache powers the synchronous keystroke filter, so results are
        stored unfiltered while only prefix matches become visible. When
        a provider yields nothing the document-token fallback runs.
        Snippet completions from ``LanguageRegistry`` / ``snippet_map``
        are merged into the visible set so users discover snippet names.

        Args:
            items: Raw completion items returned by the active provider.
        """
        self._cached_items = list(items)
        self._cache_ident = self._requested_context[0]

        prefix_lower = self._current_prefix.lower()

        # Snippet-only prefix: items are already snippet-filtered
        if self._current_prefix.startswith("/"):
            visible = [
                item
                for item in self._cached_items
                if item.text.lower().startswith(prefix_lower)
            ]
            # Ensure fresh snippet filtering even if cache was empty
            if not visible:
                visible = self._get_snippet_completions()
            if visible:
                self._show_popup(visible)
            else:
                self._close()
            return

        visible = [
            item
            for item in self._cached_items
            if item.text.lower().startswith(prefix_lower)
        ]

        # Merge snippets that match this word prefix (without needing "/")
        snippet_items = self._get_snippet_completions()
        existing_texts = {v.text for v in visible}
        for s in snippet_items:
            if s.text not in existing_texts:
                visible.append(s)

        if not visible and not items and not snippet_items:
            visible = self._get_document_tokens()
            # Also include snippets in fallback if tokens found no prefix match
            for s in snippet_items:
                if s.text not in {v.text for v in visible}:
                    visible.append(s)

        if visible:
            self._show_popup(visible)
        else:
            self._close()

    def _connect_to_manager(self, manager) -> None:
        if self._connected_manager is manager:
            return

        if self._connected_manager is not None:
            try:
                self._connected_manager.completions_ready.disconnect(
                    self._on_completions_ready
                )
            except (TypeError, RuntimeError):
                pass

        self._connected_manager = manager
        try:
            manager.completions_ready.connect(self._on_completions_ready)
        except (TypeError, RuntimeError):
            pass

    @pyqtSlot(int, list)
    def _on_completions_ready(self, request_id: int, raw_items: list) -> None:
        self._present_items(self._coerce_items(raw_items or []))

    @staticmethod
    def _full_insert_text(text: str, candidate: str) -> str:
        """Pick a safe insertion string from a provider payload.

        Legacy payloads carry jedi's ``complete`` attribute, which is only
        the missing suffix of the word (typed ``imp`` -> ``ort``). Since
        insertion replaces the whole typed fragment, any insert shorter
        than the display text is treated as a suffix and discarded.

        Args:
            text: Full display text (the complete identifier).
            candidate: Provider-supplied insert text, possibly a suffix.

        Returns:
            The candidate when it fully covers the word, else *text*.
        """
        if len(candidate) >= max(1, len(text)) and candidate:
            return candidate
        return text

    @staticmethod
    def _coerce_items(raw_items: list) -> List[CompletionItem]:
        """Convert provider results or dictionaries into CompletionItems."""
        result: List[CompletionItem] = []
        for raw in raw_items:
            if isinstance(raw, CompletionItem):
                result.append(raw)
            elif isinstance(raw, dict):
                # FIX: Read dictionary keys sent across IPC bridge
                text = raw.get("text") or raw.get("name") or ""
                icon_name = raw.get("kind") or raw.get("icon_name") or ""
                signature = raw.get("signature") or ""
                insert_text = CompletionController._full_insert_text(
                    text,
                    raw.get("insert_text") or raw.get("complete") or "",
                )
                if text:
                    result.append(
                        CompletionItem(
                            text=text,
                            insert_text=insert_text,
                            icon_name=icon_name,
                            signature=signature,
                        )
                    )
            else:
                text = getattr(raw, "text", "") or getattr(raw, "name", "")
                if text:
                    result.append(
                        CompletionItem(
                            text=text,
                            insert_text=CompletionController._full_insert_text(
                                text, getattr(raw, "insert_text", "")
                            ),
                            icon_name=getattr(raw, "kind", "")
                            or getattr(raw, "icon_name", ""),
                            signature=getattr(raw, "signature", ""),
                        )
                    )
        return result

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

        return sorted(results, key=lambda item: item.text.lower())

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
                min(below.y(), available.bottom() - self.popup.height() - margin),
            )

        popup_x = max(
            available.left() + margin,
            min(below.x(), available.right() - self.popup.width() - margin),
        )

        self.popup.move(popup_x, popup_y)
        self.popup.show()
        self._active = True

    def _insert_completion(self, item: CompletionItem) -> None:
        """Replace the fragment before the cursor with the chosen item.

        Anchors are recomputed from the live document at commit time
        instead of positions captured when results arrived. Async answers
        routinely land after the user has kept typing, so stale anchors
        previously produced corrupted words (``imp`` + ``import`` ->
        ``impt``/``importt``). With live anchoring the inserted text is
        always the full identifier swapped over whatever is typed now.

        Snippet completions carry multi-line bodies; they are expanded with
        language-aware indentation so subsequent lines align with the
        original cursor indentation.

        Args:
            item: The completion entry selected in the popup.
        """
        if self._committing:
            return

        self._committing = True
        self._close()

        try:
            insert_text = item.insert_text or item.text
            line, col = self.editor.getCursorPosition()
            before_cursor = self.editor.text(line)[:col]

            # Detect snippet trigger including leading "/"
            snippet_match = None
            if item.icon_name == "snippet" or item.text.startswith("/"):
                snippet_match = re.search(r"/[A-Za-z0-9_]*$", before_cursor)

            if snippet_match:
                start_col = snippet_match.start()
            else:
                match = re.search(r"[A-Za-z_]\w*$", before_cursor)
                start_col = match.start() if match else col

            # Handle multi-line snippet bodies with indentation preservation
            is_snippet_body = (
                item.icon_name == "snippet" and "\n" in insert_text
            )
            if is_snippet_body:
                line_text = self.editor.text(line)
                indentation = line_text[: len(line_text) - len(line_text.lstrip())]
                lines = insert_text.split("\n")
                if len(lines) > 1:
                    insert_text = (
                        lines[0]
                        + "\n"
                        + "\n".join(indentation + l for l in lines[1:])
                    )

                self.editor.beginUndoAction()
                try:
                    self.editor.setSelection(line, start_col, line, col)
                    self.editor.replaceSelectedText(insert_text)
                    if len(lines) > 1:
                        end_line = line + len(lines) - 1
                        end_col = len(indentation) + len(lines[-1])
                        self.editor.setCursorPosition(end_line, end_col)
                    else:
                        self.editor.setCursorPosition(
                            line, start_col + len(lines[0])
                        )
                finally:
                    self.editor.endUndoAction()
                return

            self.editor.beginUndoAction()
            try:
                if start_col != col:
                    self.editor.setSelection(line, start_col, line, col)
                    self.editor.replaceSelectedText(insert_text)
                else:
                    self.editor.insertAt(insert_text, line, col)
                # For single-line snippet trigger without newlines, place cursor after
                # the inserted text; for multi-line non-snippet, naive placement is OK
                if "\n" in insert_text:
                    lines = insert_text.split("\n")
                    end_line = line + len(lines) - 1
                    end_col = len(lines[-1])
                    # Adjust for possible indentation prefix on first line removal
                    self.editor.setCursorPosition(end_line, end_col)
                else:
                    self.editor.setCursorPosition(line, start_col + len(insert_text))
            finally:
                self.editor.endUndoAction()
        finally:
            self._committing = False

    def close(self) -> None:
        self._close()
        self._cached_items = []
        self._cache_ident = ""
        try:
            self.editor.removeEventFilter(self)
        except Exception:
            pass
        try:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
        except Exception:
            pass
        if self._connected_manager is not None:
            try:
                self._connected_manager.completions_ready.disconnect(
                    self._on_completions_ready
                )
            except (TypeError, RuntimeError):
                pass
            self._connected_manager = None

    def retheme(self, bg: QColor, fg: QColor, sel: QColor) -> None:
        self.popup.retheme(bg, fg, sel)

    def _close(self) -> None:
        self._debounce_timer.stop()
        if self.popup.isVisible():
            self.popup.hide()
        self._active = False

    @staticmethod
    def _is_completion_terminating_key(key_event: QEvent) -> bool:
        text = key_event.text()
        if not text:
            return False

        # FIX: Removed '.' and '/' from terminating keys so '.' and '/' trigger completion
        # '/' must not terminate because snippets use "/Name" triggers.
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
            "'",
            '"',
            "`",
            "+",
            "-",
            "*",
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
