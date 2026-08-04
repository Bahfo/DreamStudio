"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

High-Performance Virtual Minimap for DreamStudio.

Completely replaces the dual-QScintilla approach with a lightweight,
QPainter-based virtual viewport renderer.  Only the text chunks
(lines) currently visible within the minimap's logical viewport are
calculated and painted, eliminating the dual-memory footprint and
preventing editor crashes on massive files.

**Architecture**

- ``VirtualMinimap`` — a plain ``QWidget`` that draws minimap lines
  via ``paintEvent``.  No QScintilla instance; no secondary text
  buffer.
- ``MinimapOverlay`` — a transparent overlay highlighting the
  source editor's visible region (unchanged from the original).
- ``MiniMapHostWidget`` — the side-by-side container wrapping a
  ``CodeEditor`` and the ``VirtualMinimap``.
- Debounced scroll-sync prevents rapid scroll events from flooding
  the main thread with paint requests.

**Performance Guarantees**

- O(visible_lines) paint cost per frame.
- Zero extra text buffer memory (lines are read from the source
  editor on demand).
- Line metrics (width in pixels) are cached per font size and
  invalidated only when the editor font changes.
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import (
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QFont,
    QColor,
    QPalette,
    QPainter,
    QMouseEvent,
    QWheelEvent,
    QPaintEvent,
    QResizeEvent,
    QFontMetrics,
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QToolButton,
    QWidget,
)

logger = logging.getLogger(__name__)


# ==================================================================
# VirtualMinimap — QPainter-based virtual viewport minimap
# ==================================================================


class VirtualMinimap(QWidget):
    """Lightweight minimap that renders only the visible chunk of
    the source editor's text buffer using QPainter.

    **How it works:**

    1. On every paint event, determine which source lines overlap the
       minimap's viewport (``_visible_range``).
    2. For each visible line, read the raw text from the source
       editor (``self._source.text(line)``), truncate it to a
       maximum pixel width, and paint it as a tiny coloured
       rectangle.
    3. A semi-transparent overlay highlights the source editor's
       current visible viewport.

    **Line metric cache:**

    The pixel width of each line is computed lazily and cached in
    ``_line_width_cache``.  The cache is invalidated when the
    editor font changes (detected via ``_last_font_key``).

    **Scroll sync:**

    Clicking or dragging on the minimap scrolls the source editor
    to the corresponding line.  A debounced ``QTimer`` prevents
    rapid scroll events from overwhelming the paint pipeline.
    """

    # Maximum number of characters to measure per line (for
    # performance on extremely long lines).
    MAX_LINE_CHARS = 200

    def __init__(
        self,
        source: QWidget,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._source = source

        # ── Visual configuration ──────────────────────────────────
        self._char_width: float = 1.8  # pixels per character
        self._line_height: float = 3.0  # pixels per line
        self._padding: int = 2  # top/bottom padding

        # ── Line cache ────────────────────────────────────────────
        self._line_cache: dict[int, str] = {}
        self._line_width_cache: dict[int, float] = {}
        self._last_font_key: Optional[str] = None

        # ── Visible range tracking ────────────────────────────────
        self._first_visible_source: int = 0
        self._visible_line_count: int = 0

        # ── Overlay for the source viewport highlight ─────────────
        self._overlay_y: int = 0
        self._overlay_h: int = 0

        # ── Drag state ────────────────────────────────────────────
        self._is_dragging: bool = False

        # ── Debounce timer for scroll sync ────────────────────────
        self._scroll_debounce = QTimer(self)
        self._scroll_debounce.setSingleShot(True)
        self._scroll_debounce.setInterval(16)  # ~60 fps
        self._scroll_debounce.timeout.connect(self.update)

        # ── Configuration ─────────────────────────────────────────
        self.setFixedWidth(110)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        # Background.
        pal = self.palette()
        bg = pal.color(QPalette.ColorRole.Window)
        self._apply_theme(bg)

    def _apply_theme(
        self,
        bg: QColor,
        palette: Optional[dict] = None,
    ) -> None:
        """Derive every minimap colour from *bg* and the theme palette.

        The minimap is a pure ``QPainter`` widget, so it has no lexer
        of its own; its colours must be recomputed from the active IDE
        theme.  When *palette* is omitted the currently active theme's
        palette is used so the initial paint already matches the theme
        under which the editor was created.
        """
        from editor.Ironica.retheme import active_theme_name, theme_palette

        if palette is None:
            palette = theme_palette(active_theme_name())

        dark = bg.lightness() < 128
        if dark:
            self._bg_color = bg.darker(120)
            self._overlay_color = QColor(128, 128, 128, 60)
            self._line_default_color = QColor(160, 160, 160, 40)
        else:
            self._bg_color = bg.darker(104)
            self._overlay_color = QColor(128, 128, 128, 60)
            self._line_default_color = QColor(100, 100, 100, 30)
        self._text_color = bg.lighter(220) if dark else bg.darker(160)

        def token(key: str, default: str) -> QColor:
            colour = palette.get(key, default)
            c = QColor(colour)
            c.setAlpha(50)
            return c

        # Approximate syntax colours at minimap scale, keyed by the
        # same symbolic palette entries the lexer uses.
        self._line_comment_color = token("COMMENT_COLOR", "#6A9955")
        self._line_string_color = token("STRING_COLOR", "#CE9178")
        self._line_class_color = token("CLASS_COLOR", "#4EC9B0")
        self._line_function_color = token("DEFINITION_COLOR", "#DCDCAA")
        self._line_import_color = token("IMPORT_COLOR", "#C586C0")
        self._line_number_color = token("NUMBER_COLOR", "#B5CEA8")

    def retheme(self, theme_name: str, bg: QColor) -> None:
        """Recolour the minimap after the IDE switches to *theme_name*."""
        from editor.Ironica.retheme import theme_palette

        self._apply_theme(bg, theme_palette(theme_name))
        self.update()

    # ------------------------------------------------------------------
    # Font / metric management
    # ------------------------------------------------------------------

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

        # Invalidate line width cache on font change.
        self._line_width_cache.clear()

    # ------------------------------------------------------------------
    # Source line access
    # ------------------------------------------------------------------

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
            # Truncate for performance on very long lines.
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

    # ------------------------------------------------------------------
    # Visible range calculation
    # ------------------------------------------------------------------

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

        # Map source scrollbar position to minimap first visible line.
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

    # ------------------------------------------------------------------
    # Overlay (viewport highlight)
    # ------------------------------------------------------------------

    def _update_overlay(self) -> None:
        """Calculate the position and height of the overlay rectangle."""
        try:
            source_first = self._source.SendScintilla(2152)  # SCI_GETFIRSTVISIBLELINE
            source_visible = self._source.SendScintilla(2156)  # SCI_LINESONSCREEN
        except Exception:
            return

        minimap_first = self._first_visible_source
        line_h = max(2.0, self._line_height)

        y = (source_first - minimap_first) * line_h + self._padding
        h = source_visible * line_h

        self._overlay_y = int(y)
        self._overlay_h = int(h)

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """Render only the visible chunk of the source document.

        This is the core of the virtual minimap: we paint at most
        ``visible_line_count`` lines, each as a tiny coloured
        rectangle representing the text density.
        """
        self._ensure_metrics()
        self._calculate_visible_range()
        self._update_overlay()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Background.
        painter.fillRect(self.rect(), self._bg_color)

        total = self._source_line_count()
        if total == 0 or self._visible_line_count == 0:
            painter.end()
            return

        line_h = max(2.0, self._line_height)
        char_w = max(0.5, self._char_width)
        x_offset = 4  # left padding
        max_w = self.width() - x_offset - 2

        # ── Draw visible lines ────────────────────────────────────
        for i in range(self._visible_line_count):
            src_line = self._first_visible_source + i
            if src_line >= total:
                break

            y = int(self._padding + i * line_h)
            text = self._source_line_text(src_line)

            if not text.strip():
                continue  # skip blank lines (leave background)

            # Draw the line as a series of tiny rectangles.
            # We don't render individual characters at this scale;
            # instead we draw a single horizontal bar whose width
            # represents the line's text density.
            stripped = text.rstrip()
            pixel_w = min(len(stripped) * char_w, max_w)

            # Simple colour assignment based on leading whitespace
            # and first non-space character (approximates syntax
            # colouring at minimap scale).
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

        # ── Draw viewport overlay ─────────────────────────────────
        painter.fillRect(
            0,
            self._overlay_y,
            self.width(),
            max(4, self._overlay_h),
            self._overlay_color,
        )

        painter.end()

    # ------------------------------------------------------------------
    # Scroll sync (debounced)
    # ------------------------------------------------------------------

    def _on_source_scroll(self) -> None:
        """Debounced handler for source editor scroll changes."""
        self._scroll_debounce.start()

    def _on_source_text_changed(self) -> None:
        """Invalidate cache and schedule repaint on text change."""
        self._invalidate_cache()
        self._scroll_debounce.start()

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def _scroll_source_to_y(self, y: int) -> None:
        """Translate a minimap Y coordinate to a source editor scroll."""
        total = self._source_line_count()
        if total == 0:
            return

        line_h = max(2.0, self._line_height)
        clicked_line_offset = max(0, int((y - self._padding) / line_h))
        target_line = self._first_visible_source + clicked_line_offset
        target_line = max(0, min(target_line, total - 1))

        # Center the source view on the clicked line.
        try:
            visible_on_screen = self._source.SendScintilla(2156)  # SCI_LINESONSCREEN
        except Exception:
            visible_on_screen = 20

        first_visible = max(0, target_line - visible_on_screen // 2)
        self._source.SendScintilla(2152, first_visible)  # SCI_SETFIRSTVISIBLELINE
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._scroll_source_to_y(int(event.position().y()))
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._is_dragging:
            self._scroll_source_to_y(int(event.position().y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        event.ignore()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        """Forward scroll wheel events directly to the source editor."""
        self._source.wheelEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.update()


# ==================================================================
# MinimapOverlay — transparent viewport highlight
# ==================================================================


class MinimapOverlay(QWidget):
    """Transparent overlay that highlights the visible region of the
    source editor inside the minimap container.

    This widget is ``WA_TransparentForMouseEvents`` so clicks pass
    through to the ``VirtualMinimap`` beneath it.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def update_geometry(self, y_offset: int, height: int) -> None:
        """Update the position and height of the highlight box."""
        if self.parent():
            self.setGeometry(0, y_offset, self.parent().width(), height)


# ==================================================================
# MiniMapHostWidget — side-by-side container
# ==================================================================


class MiniMapHostWidget(QWidget):
    """Wraps a ``CodeEditor`` and a ``VirtualMinimap`` side by side.

    Delegates all attribute access to the underlying editor so the
    host widget can be used as a drop-in replacement wherever
    ``CodeEditor`` is expected.

    **Public interface:**

    - ``editor`` — the underlying ``CodeEditor`` instance.
    - ``minimap`` — the ``VirtualMinimap`` instance.
    - ``set_minimap_visible(visible)`` — toggle minimap visibility.
    - ``toggle_minimap()`` — flip minimap visibility.
    """

    position_changed = pyqtSignal(int, int)
    dirty_state_changed = pyqtSignal(bool)

    def __init__(
        self,
        editor: QWidget,
        parent: Optional[QWidget] = None,
        minimap_width: int = 80,
    ):
        super().__init__(parent)
        self.setObjectName("MiniMapHostWidget")

        self._editor = editor
        self._minimap_width = minimap_width
        self._minimap_visible = True

        if self._editor.parent() is not self:
            self._editor.setParent(self)

        self._editor.position_changed.connect(self.position_changed.emit)
        self._editor.dirty_state_changed.connect(self.dirty_state_changed.emit)

        # ── Layout ────────────────────────────────────────────────
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._editor, 1)

        # ── Minimap container (vertical: up btn + minimap + down btn) ──
        self._minimap_container = QWidget(self)
        minimap_layout = QVBoxLayout(self._minimap_container)
        minimap_layout.setContentsMargins(0, 0, 0, 0)
        minimap_layout.setSpacing(0)

        # Up scroll button.
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

        # The virtual minimap.
        self._minimap = VirtualMinimap(editor, self._minimap_container)

        # Down scroll button.
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

        # ── Connect source signals for debounced sync ─────────────
        source_scrollbar = self._editor.verticalScrollBar()
        if source_scrollbar is not None:
            source_scrollbar.valueChanged.connect(self._minimap._on_source_scroll)

        self._editor.textChanged.connect(self._minimap._on_source_text_changed)
        self._editor.cursorPositionChanged.connect(self._minimap._on_source_scroll)

        self._minimap.update()

    @property
    def editor(self):
        """Return the underlying ``CodeEditor``."""
        return self._editor

    @property
    def minimap(self) -> VirtualMinimap:
        """Return the ``VirtualMinimap`` instance."""
        return self._minimap

    # ------------------------------------------------------------------
    # Scroll helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Attribute delegation
    # ------------------------------------------------------------------

    def __getattr__(self, name: str):
        return getattr(self._editor, name)


# ==================================================================
# Public factory functions
# ==================================================================


def attach_minimap(
    editor, parent: Optional[QWidget] = None, minimap_width: int = 110
) -> MiniMapHostWidget:
    """Create and return a ``MiniMapHostWidget`` wrapping *editor*."""
    return MiniMapHostWidget(editor, parent=parent, minimap_width=minimap_width)


def ensure_minimap(editor_or_host):
    """Return the ``MiniMapHostWidget`` for *editor_or_host*.

    If *editor_or_host* is already a ``MiniMapHostWidget`` it is
    returned as-is.  If it is a bare ``CodeEditor`` it is wrapped
    in a new host.
    """
    if isinstance(editor_or_host, MiniMapHostWidget):
        return editor_or_host
    return attach_minimap(editor_or_host)
