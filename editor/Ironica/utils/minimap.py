"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
High-Performance Virtual Minimap for DreamStudio.
"""

from __future__ import annotations

from editor import *
from editor.Ironica.utils.diagnostics_ruler import DiagnosticsRuler

logger = logging.getLogger(__name__)


class VirtualMinimap(QWidget):
    """Lightweight minimap that renders only the visible chunk of the source editor's text buffer using QPainter."""

    MAX_LINE_CHARS = 200

    def __init__(
        self,
        source: QWidget,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._source = source
        self.setObjectName("MiniMapHostWidget")

        self._char_width: float = 1.8
        self._line_height: float = 3.0
        self._padding: int = 2

        self._line_cache: dict[int, str] = {}
        self._line_width_cache: dict[int, float] = {}
        self._last_font_key: Optional[str] = None

        self._first_visible_source: int = 0
        self._visible_line_count: int = 0

        self._overlay_y: int = 0
        self._overlay_h: int = 0

        self._is_dragging: bool = False

        self._scroll_debounce = QTimer(self)
        self._scroll_debounce.setSingleShot(True)
        self._scroll_debounce.setInterval(16)
        self._scroll_debounce.timeout.connect(self.update)

        self._apply_theme()

        self.setFixedWidth(110)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def _apply_theme(
        self,
        palette: Optional[dict] = None,
    ) -> None:
        """Resolve the syntax-approximation bar colours from the theme palette."""
        from editor.Ironica.retheme import active_theme_name, theme_palette

        if palette is None:
            palette = theme_palette(active_theme_name())

        self._overlay_color = QColor(128, 128, 128, 60)
        self._line_default_color = QColor(160, 160, 160, 40)

        def token(key: str, default: str) -> QColor:
            colour = palette.get(key, default)
            c = QColor(colour)
            c.setAlpha(50)
            return c

        self._line_comment_color = token("COMMENT_COLOR", "#6A9955")
        self._line_string_color = token("STRING_COLOR", "#CE9178")
        self._line_class_color = token("CLASS_COLOR", "#4EC9B0")
        self._line_function_color = token("DEFINITION_COLOR", "#DCDCAA")
        self._line_import_color = token("IMPORT_COLOR", "#C586C0")
        self._line_number_color = token("NUMBER_COLOR", "#B5CEA8")


    def _font_key(self) -> str:
        """Return a hashable key for the current source editor font."""
        font = self._source.font()
        return f"{font.family()}-{font.pointSize()}-{font.pixelSize()}"

    def _ensure_metrics(self) -> None:
        """Recalculate line metrics if the source font has changed."""
        key = self._font_key()
        if key == self._last_font_key:
            return
        self._last_font_key = key

        font = QFont("JetBrains Mono")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPixelSize(max(1, int(self._line_height)))
        fm = QFontMetrics(font)
        self._char_width = fm.horizontalAdvance("M") * 0.18
        self._line_height = max(2.0, fm.height() * 0.25)

        self._line_width_cache.clear()


    def _source_line_count(self) -> int:
        """Return the total number of lines in the source editor."""
        try:
            return self._source.lines()
        except Exception:
            return 0

    def _source_line_text(self, line: int) -> str:
        """Return the text of source line *line*, cached."""
        if line in self._line_cache:
            return self._line_cache[line]
        try:
            text = self._source.text(line)
            if len(text) > self.MAX_LINE_CHARS:
                text = text[: self.MAX_LINE_CHARS]
            self._line_cache[line] = text
            return text
        except Exception:
            return ""

    def _invalidate_cache(self) -> None:
        """Clear the line text cache (called on text change)."""
        self._line_cache.clear()
        self._line_width_cache.clear()


    def _calculate_visible_range(self) -> None:
        """Determine which source lines are visible in the minimap viewport."""
        total = self._source_line_count()
        if total == 0:
            self._first_visible_source = 0
            self._visible_line_count = 0
            return

        viewport_h = self.height() - 2 * self._padding
        if viewport_h <= 0:
            self._first_visible_source = 0
            self._visible_line_count = 0
            return

        lines_per_viewport = max(1, int(viewport_h / max(1.0, self._line_height)))
        total_source_lines = total

        source_scrollbar = self._source.verticalScrollBar()
        if source_scrollbar is not None:
            sb_max = source_scrollbar.maximum()
            if sb_max > 0:
                scroll_ratio = source_scrollbar.value() / sb_max
                self._first_visible_source = int(
                    scroll_ratio * max(0, total_source_lines - lines_per_viewport)
                )
            else:
                self._first_visible_source = 0
        else:
            self._first_visible_source = 0

        self._first_visible_source = max(
            0, min(self._first_visible_source, total_source_lines - 1)
        )
        self._visible_line_count = min(lines_per_viewport, total_source_lines)


    def _update_overlay(self) -> None:
        """Calculate the position and height of the overlay rectangle."""
        try:
            source_first = self._source.SendScintilla(2152)
            source_visible = self._source.SendScintilla(2156)
        except Exception:
            return

        minimap_first = self._first_visible_source
        line_h = max(2.0, self._line_height)

        y = (source_first - minimap_first) * line_h + self._padding
        h = source_visible * line_h

        self._overlay_y = int(y)
        self._overlay_h = int(h)


    def paintEvent(self, event: QPaintEvent) -> None:
        """Render only the visible chunk of the source document."""
        self._ensure_metrics()
        self._calculate_visible_range()
        self._update_overlay()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        option = QStyleOption()
        option.initFrom(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, option, painter, self
        )

        total = self._source_line_count()
        if total == 0 or self._visible_line_count == 0:
            painter.end()
            return

        line_h = max(2.0, self._line_height)
        char_w = max(0.5, self._char_width)
        x_offset = 4
        max_w = self.width() - x_offset - 2

        for i in range(self._visible_line_count):
            src_line = self._first_visible_source + i
            if src_line >= total:
                break

            y = int(self._padding + i * line_h)
            text = self._source_line_text(src_line)

            if not text.strip():
                continue

            stripped = text.rstrip()
            pixel_w = min(len(stripped) * char_w, max_w)

            colour = self._line_default_color
            first_char = stripped.lstrip()[:1] if stripped else ""
            if first_char in ("#",):
                colour = self._line_comment_color
            elif first_char in ('"', "'", "f"):
                colour = self._line_string_color
            elif first_char.isupper():
                colour = self._line_class_color
            elif stripped.startswith(("def ", "async ")):
                colour = self._line_function_color
            elif stripped.startswith(("import ", "from ")):
                colour = self._line_import_color
            elif first_char.isdigit() or first_char == "-":
                colour = self._line_number_color

            painter.fillRect(x_offset, y, int(pixel_w), int(line_h), colour)

        painter.fillRect(
            0,
            self._overlay_y,
            self.width(),
            max(4, self._overlay_h),
            self._overlay_color,
        )

        painter.end()


    def _on_source_scroll(self) -> None:
        """Debounced handler for source editor scroll changes."""
        self._scroll_debounce.start()

    def _on_source_text_changed(self) -> None:
        """Invalidate cache and schedule repaint on text change."""
        self._invalidate_cache()
        self._scroll_debounce.start()


    def _scroll_source_to_y(self, y: int) -> None:
        """Translate a minimap Y coordinate to a source editor scroll."""
        total = self._source_line_count()
        if total == 0:
            return

        line_h = max(2.0, self._line_height)
        clicked_line_offset = max(0, int((y - self._padding) / line_h))
        target_line = self._first_visible_source + clicked_line_offset
        target_line = max(0, min(target_line, total - 1))

        try:
            visible_on_screen = self._source.SendScintilla(2156)
        except Exception:
            visible_on_screen = 20

        first_visible = max(0, target_line - visible_on_screen // 2)
        self._source.SendScintilla(2152, first_visible)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._scroll_source_to_y(int(event.position().y()))
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging:
            self._scroll_source_to_y(int(event.position().y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Forward scroll wheel events directly to the source editor."""
        self._source.wheelEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.update()


class MinimapOverlay(QWidget):
    """Transparent overlay that highlights the visible region of the source editor inside the minimap container."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def update_geometry(self, y_offset: int, height: int) -> None:
        """Update the position and height of the highlight box."""
        if self.parent():
            self.setGeometry(0, y_offset, self.parent().width(), height)


class MiniMapHostWidget(QWidget):
    """Wraps a ``CodeEditor`` and a ``VirtualMinimap`` side by side."""

    position_changed = pyqtSignal(int, int)
    dirty_state_changed = pyqtSignal(bool)

    def __init__(
        self,
        editor: QWidget,
        parent: Optional[QWidget] = None,
        minimap_width: int = 80,
    ):
        super().__init__(parent)

        self._editor = editor
        self._minimap_width = minimap_width
        self._minimap_visible = True

        if self._editor.parent() is not self:
            self._editor.setParent(self)

        self._editor.position_changed.connect(self.position_changed.emit)
        self._editor.dirty_state_changed.connect(self.dirty_state_changed.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._editor, 1)

        self._ruler = DiagnosticsRuler(self._editor, self)
        layout.addWidget(self._ruler, 0)

        self._minimap_container = QWidget(self)
        self._minimap_container.setObjectName("MinimapPanel")
        self._minimap_container.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground, True
        )
        minimap_layout = QVBoxLayout(self._minimap_container)
        minimap_layout.setContentsMargins(0, 0, 0, 0)
        minimap_layout.setSpacing(0)

        self._btn_up = QToolButton(self._minimap_container)
        self._btn_up.setArrowType(Qt.ArrowType.UpArrow)
        self._btn_up.setAutoRepeat(True)
        self._btn_up.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._btn_up.setStyleSheet(
            "QToolButton { border: none; background: transparent; padding: 4px; }"
            "QToolButton:hover { background: rgba(128, 128, 128, 0.2); }"
        )
        self._btn_up.clicked.connect(self._scroll_up)

        self._minimap = VirtualMinimap(editor, self._minimap_container)

        self._btn_down = QToolButton(self._minimap_container)
        self._btn_down.setArrowType(Qt.ArrowType.DownArrow)
        self._btn_down.setAutoRepeat(True)
        self._btn_down.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._btn_down.setStyleSheet(
            "QToolButton { border: none; background: transparent; padding: 4px; }"
            "QToolButton:hover { background: rgba(128, 128, 128, 0.2); }"
        )
        self._btn_down.clicked.connect(self._scroll_down)

        minimap_layout.addWidget(self._btn_up)
        minimap_layout.addWidget(self._minimap, 1)
        minimap_layout.addWidget(self._btn_down)

        self._minimap_container.setFixedWidth(self._minimap_width)
        layout.addWidget(self._minimap_container, 0)

        source_scrollbar = self._editor.verticalScrollBar()
        if source_scrollbar is not None:
            source_scrollbar.valueChanged.connect(self._minimap._on_source_scroll)

        self._editor.textChanged.connect(self._minimap._on_source_text_changed)
        self._editor.cursorPositionChanged.connect(self._minimap._on_source_scroll)

        ticks_signal = getattr(self._editor, "diagnostic_ticks_changed", None)
        if ticks_signal is not None:
            ticks_signal.connect(self._ruler.set_ticks)
        self._ruler.line_hovered.connect(self._on_ruler_line_hovered)

        self._minimap.update()

    def _on_ruler_line_hovered(self, line: int) -> None:
        """Forward a ruler hover to the editor as a highlight or a clear."""
        setter = getattr(self._editor, "set_hover_line", None)
        if setter is None:
            return
        if line < 0:
            clearer = getattr(self._editor, "clear_hover_line", None)
            if clearer is not None:
                clearer()
            return
        setter(line)

    @property
    def editor(self):
        """Return the underlying ``CodeEditor``."""
        return self._editor

    @property
    def ruler(self) -> DiagnosticsRuler:
        """Return the ``DiagnosticsRuler`` instance."""
        return self._ruler

    @property
    def minimap(self) -> VirtualMinimap:
        """Return the ``VirtualMinimap`` instance."""
        return self._minimap


    def _scroll_up(self) -> None:
        """Scroll the source editor up one step."""
        sb = self._editor.verticalScrollBar()
        if sb:
            sb.setValue(sb.value() - sb.singleStep())

    def _scroll_down(self) -> None:
        """Scroll the source editor down one step."""
        sb = self._editor.verticalScrollBar()
        if sb:
            sb.setValue(sb.value() + sb.singleStep())


    def set_minimap_visible(self, visible: bool) -> None:
        """Show or hide the minimap panel."""
        self._minimap_visible = visible
        self._minimap_container.setVisible(visible)
        self._minimap_container.setFixedWidth(self._minimap_width if visible else 0)
        if visible:
            self._minimap.update()

    def toggle_minimap(self) -> None:
        """Flip minimap visibility."""
        self.set_minimap_visible(not self._minimap_visible)


    def __getattr__(self, name: str):
        return getattr(self._editor, name)


def attach_minimap(
    editor, parent: Optional[QWidget] = None, minimap_width: int = 110
) -> MiniMapHostWidget:
    """Create and return a ``MiniMapHostWidget`` wrapping *editor*."""
    return MiniMapHostWidget(editor, parent=parent, minimap_width=minimap_width)


def ensure_inner(widget):
    """Return underlying CodeEditor for host or plain widget."""
    try:
        from editor.Ironica.utils.minimap import MiniMapHostWidget
    except Exception:
        MiniMapHostWidget = None
    if MiniMapHostWidget is not None and isinstance(widget, MiniMapHostWidget):
        return widget.editor
    for attr in ("editor", "code_editor", "text_edit"):
        inner = getattr(widget, attr, None)
        if inner is not None and hasattr(inner, "isModified"):
            return inner
    if hasattr(widget, "isModified"):
        return widget
    return None
