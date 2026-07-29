"""
(C) COPYRIGHT 2026 - EXcellent TechStacks, All Rights Reserved.

Ironica Code Editor - Lightweight static text editor for DreamStudio.
This code is protected under the GPLv3 License.
"""

# Written By Bahaa Nofal - 26/May/2026

import logging
import pathlib
import stat
import re

from typing import Optional, Any

from PyQt6.QtGui import (
    QKeyEvent,
    QPalette,
    QPainter,
    QPixmap,
    QColor,
    QImage,
    QBrush,
    QFont,
    QPen,
)
from PyQt6.QtCore import Qt, QEvent, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication, QColorDialog
from PyQt6.Qsci import QsciScintilla

from editor.Ironica.language_engine import LanguageRegistry
from editor.Ironica.regex import IronicaLexer
from editor.Ironica.utils.documentation_flayout import DocumentationFlyout
from editor.Ironica.utils.hover_controller import HoverController
from editor.Ironica.utils.debug_frame import StackInfoFrame

logger = logging.getLogger(__name__)


class CodeEditor(QsciScintilla):
    """
    Base class code editor for complex language support for DreamStudio.

    Builds on top of QScintilla. The ``CodeEditor`` class supports a multi-
    plugin system for languages support via its modern engine built on top
    of Ironica Lexers.

    **Ownership Model:**

    The editor owns the following state exclusively:

    - Text content (via QScintilla buffer)
    - Cursor position and selection
    - Modified (dirty) flag (via ``isModified()``)
    - Lexer and language configuration
    - Read-only state (via ``setReadOnly()``)
    - ``current_file_path`` — the canonical path of the file on disk
    - ``current_lang`` — the resolved language identifier
    - ``current_provider`` — the language intelligence provider

    The tab manager (``DreamTabbedEditor``) owns:

    - Tab title, position, and ordering
    - The ``opened_files`` deduplication map
    - Per-tab UI indicators (dirty dot, read-only lock)
    """

    position_changed = pyqtSignal(int, int)
    dirty_state_changed = pyqtSignal(bool)

    _INDENTATION_SPACING = 4

    MARGIN_BREAKPOINT = 1
    MARKER_BREAKPOINT = 1
    COLOR_MARGIN = 2
    MARKER_HOVER = 3
    MARKER_EXEC_LINE = 4

    COLOR_BREAKPOINT = QColor("#E53935")
    COLOR_HOVER = QColor(229, 57, 53, 100)
    COLOR_EXEC_LINE = QColor("#FFD54F")
    CIRCLE_RADIUS = 4

    # Works for three types: Hex, RGB, and RGBA
    COLOR_REGEX = re.compile(
        r"(#(?:[0-9a-fA-F]{3,4}){1,2}\b|"
        r"rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*(?:0?\.\d+|\d+(?:\.\d+)?)\s*)?\))"
    )
    COLOR_MARKER_START = 10
    COLOR_MARKER_END = 24

    def __init__(self, _parent=None, language=None, file_path=None):
        """
        Initialise the editor widget.

        Args:
            _parent: Parent widget (typically the tab editor).
            language: Optional language identifier string. When ``None``,
                no syntax highlighting or provider is attached.
            file_path: Optional file path to load immediately. If provided,
                ``load_from_file`` is called during construction.
        """
        super().__init__(_parent)

        self.setObjectName("CodeEditor")
        self._lexer = None
        self._parent = _parent
        self.current_file_path = None
        self._font_size = 10
        self._is_dirty = False
        self._diagnostic_indicators = {}
        self._next_diag_slot = 8  # Slots 8-15 allocated for diagnostics to avoid
        # semantic overlaps

        # For breakpoints hover:
        self._hovered_breakpoint_line = None

        ###############################################
        # Breakpoint Helpers
        ###############################################
        self._debug_stack_widget = None
        self._paused_line = -1

        self.verticalScrollBar().valueChanged.connect(self._update_debug_stack_position)
        self.horizontalScrollBar().valueChanged.connect(
            self._update_debug_stack_position
        )

        self.textChanged.connect(self._on_text_changed)

        ###############################################
        # Color Wheel and Indicators
        ###############################################
        self._color_marker_cache = {}
        self._next_color_marker_id = self.COLOR_MARKER_START

        self.textChanged.connect(self.update_visible_color_indicators)
        self.verticalScrollBar().valueChanged.connect(
            self.update_visible_color_indicators
        )

        # Language state — single source of truth.
        self.current_lang: Optional[str] = None
        self.current_provider: Optional[Any] = None

        self._font = QFont()
        self._font.setFamilies(["firacode", "Consolas", "Courier New", "monospace"])
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        self._font.setPointSize(10)
        self.setFont(self._font)
        try:
            self.setUtf8(True)
        except Exception:
            pass

        self.setMouseTracking(True)
        self._setup_indentation()
        self._setup_auto_indent()
        self._setup_margins()
        self._setup_folding()
        self._setup_caret()
        self._setup_edge()
        self._setup_wrap()

        # Hover flyout state (DocumentationFlyout + HoverController).
        self._hover_flyout: Optional[DocumentationFlyout] = None
        self._hover_controller: Optional[HoverController] = None
        self._last_mouse_pos = None

        # Import highlighting indicators (debounced).
        self._import_highlight_timer = QTimer(self)
        self._import_highlight_timer.setSingleShot(True)
        self._import_highlight_timer.setInterval(300)
        self._import_highlight_timer.timeout.connect(self._apply_semantic_indicators)

        # Fold recomputation (debounced).
        self._fold_recompute_timer = QTimer(self)
        self._fold_recompute_timer.setSingleShot(True)
        self._fold_recompute_timer.setInterval(500)
        self._fold_recompute_timer.timeout.connect(self._recompute_folds)

        self.cursorPositionChanged.connect(self._emit_position)

        self.marginClicked.connect(self._on_margin_clicked)

        # Apply language if provided.
        if language:
            self.setLanguage(language)

        # Load file if provided.
        if file_path:
            self.load_from_file(file_path)

    # ------------------------------------------------------------------
    # Dirty state
    # ------------------------------------------------------------------

    def _on_text_changed(self) -> None:
        if not self._is_dirty:
            self._is_dirty = True
            self.dirty_state_changed.emit(True)
        if self.current_lang == "python":
            self._import_highlight_timer.start()
            self._schedule_fold_recompute()

    def _schedule_fold_recompute(self) -> None:
        """Debounce fold recomputation on text change."""
        self._fold_recompute_timer.start()

    def _recompute_folds(self) -> None:
        """Recompute fold regions for the current language and push
        them to the FoldManager."""
        if not self.current_lang or not self._fold_manager:
            return

        try:
            if self.current_lang == "python":
                from editor.Ironica.plugins.python.folding import (
                    compute_folds_for_editor,
                )

                compute_folds_for_editor(self)
        except Exception as exc:
            logger.debug("Fold recomputation failed: %s", exc)

    # ------------------------------------------------------------------
    # Hover flyout engine
    # ------------------------------------------------------------------

    def _setup_hover_engine(self) -> None:
        """Create and attach the DocumentationFlyout + HoverController."""
        if not self.current_provider:
            return
        if not hasattr(self.current_provider, "get_hover_display"):
            return

        self._hover_flyout = DocumentationFlyout(parent=self)
        self._hover_controller = HoverController(
            editor=self, flyout=self._hover_flyout, provider=self.current_provider
        )
        self._hover_flyout.jump_to_source_requested.connect(
            lambda: self.execute_goto_definition(
                self._hover_controller._target_line,
                self._hover_controller._target_col,
            )
        )

    def _teardown_hover_engine(self) -> None:
        """Destroy the current hover flyout and controller."""
        if self._hover_controller:
            self._hover_controller = None
        if self._hover_flyout:
            self._hover_flyout.hide()
            self._hover_flyout = None

    def _dismiss_hover_flyout(self) -> None:
        """Dismiss the flyout unless pinned or mouse is inside."""
        if self._hover_flyout and self._hover_flyout.isVisible():
            self._hover_flyout.dismiss(force=False)

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _setup_indentation(self) -> None:
        """Configure indentation, tab width, and backspace behaviour."""
        self.setAutoIndent(True)
        self.setBackspaceUnindents(True)
        self.setTabIndents(True)
        self.setIndentationWidth(self._INDENTATION_SPACING)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(self._INDENTATION_SPACING)
        self.SendScintilla(QsciScintilla.SCI_SETINDENTATIONGUIDES, 3)

    def _theme_colors(self):
        """Derive palette colours for margins, caret, and folding."""
        pal = self.palette()
        bg = pal.color(QPalette.ColorRole.Window)
        text = pal.color(QPalette.ColorRole.WindowText)
        mid = bg.lighter(130) if bg.lightness() < 128 else bg.darker(115)
        border = bg.lighter(150) if bg.lightness() < 128 else bg.darker(130)
        return bg, text, mid, border

    def setup_symbol_margin(
        self, margin: int, *marker_ids: int, width: int = 18
    ) -> None:
        self.setMarginType(margin, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginSensitivity(margin, True)
        self.setMarginWidth(margin, width)

        mask = 0
        for m in marker_ids:
            mask |= 1 << m
        self.setMarginMarkerMask(margin, mask)

    def _setup_margins(self) -> None:
        """Configure line numbers, breakpoints, and colorwheel margins."""
        bg, text, _, _ = self._theme_colors()
        self.setPaper(bg)
        self.setColor(text)

        # Line Numbers
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "000000")
        self.setMarginLineNumbers(0, True)
        self.setMarginsBackgroundColor(bg)
        self.setMarginsForegroundColor(text)
        self._apply_indent_guide_color(text)

        # Breakpoints Margin
        self.markerDefine(
            self._create_circle_image(18, self.CIRCLE_RADIUS, self.COLOR_BREAKPOINT),
            self.MARKER_BREAKPOINT,
        )
        self.markerDefine(
            self._create_circle_image(18, self.CIRCLE_RADIUS, self.COLOR_HOVER),
            self.MARKER_HOVER,
        )
        self.markerDefine(
            QsciScintilla.MarkerSymbol.FullRectangle,
            self.MARKER_EXEC_LINE,
        )
        self.setMarkerForegroundColor(self.COLOR_EXEC_LINE, self.MARKER_EXEC_LINE)
        self.setMarkerBackgroundColor(self.COLOR_EXEC_LINE, self.MARKER_EXEC_LINE)

        self.setup_symbol_margin(
            self.MARGIN_BREAKPOINT,
            self.MARKER_BREAKPOINT,
            self.MARKER_HOVER,
            self.MARKER_EXEC_LINE,
        )

        # Colorwheel Margin
        color_marker_ids = list(
            range(self.COLOR_MARKER_START, self.COLOR_MARKER_END + 1)
        )
        self.setup_symbol_margin(self.COLOR_MARGIN, *color_marker_ids)

        # Left padding offset
        self.SendScintilla(QsciScintilla.SCI_SETMARGINLEFT, 0, 10)

    def _apply_indent_guide_color(self, text_color) -> None:
        """Set indentation guide line to a smooth, light neutral gray."""
        from PyQt6.QtGui import QColor

        guide = QColor(160, 160, 160)
        guide.setAlpha(30)
        self.setIndentationGuidesForegroundColor(guide)

    def _setup_caret(self) -> None:
        """Configure caret appearance."""
        bg, text, mid, _ = self._theme_colors()
        self.setCaretForegroundColor(text)
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(mid)
        self.setCaretWidth(2)

    def _setup_folding(self) -> None:
        """Configure code folding markers and attach a FoldManager once."""
        if not hasattr(self, "_fold_manager") or self._fold_manager is None:
            from editor.Ironica.utils.folding import FoldManager

            self._fold_manager = FoldManager(self)

    def _setup_edge(self) -> None:
        """Configure the long-line edge marker."""
        _, _, mid, _ = self._theme_colors()
        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
        self.setEdgeColumn(80)
        self.setEdgeColor(mid)

    def _setup_wrap(self) -> None:
        """Configure word-wrap mode."""
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def _setup_auto_indent(self) -> None:
        """Configure brace matching."""
        self.setBraceMatching(QsciScintilla.BraceMatch.StrictBraceMatch)

    # ------------------------------------------------------------------
    # Position / signals
    # ------------------------------------------------------------------

    def _emit_position(self, line: int, col: int) -> None:
        """Forward cursor position changes to the ``position_changed`` signal."""
        self.position_changed.emit(line, col)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_debug_stack_position()

    def wheelEvent(self, event) -> None:
        """Dismiss all popups when the editor scrolls."""
        self._dismiss_all_popups()
        super().wheelEvent(event)

    def changeEvent(self, event) -> None:
        if event.type() in (
            QEvent.Type.StyleChange,
            QEvent.Type.PaletteChange,
        ):
            if getattr(self, "_in_change_event", False):
                return
            self._in_change_event = True
            try:
                self._setup_margins()
                self._setup_caret()
                self._setup_folding()
                self._setup_edge()
            finally:
                self._in_change_event = False
        elif event.type() == QEvent.Type.WindowStateChange:
            self._dismiss_all_popups()
        super().changeEvent(event)

    def focusOutEvent(self, event) -> None:
        """Dismiss hover flyout when the editor loses focus."""
        self._dismiss_hover_flyout()
        super().focusOutEvent(event)

    # ------------------------------------------------------------------
    # Font management
    # ------------------------------------------------------------------

    @property
    def font_size(self) -> int:
        """Current font point size."""
        return self._font_size

    @font_size.setter
    def font_size(self, size: int) -> None:
        self._font_size = int(size)
        self._font.setPointSize(self._font_size)
        self.setFont(self._font)
        self.setMarginsFont(self._font)
        if self._lexer and hasattr(self._lexer, "setFont"):
            self._lexer.setFont(self._font, -1)

    def set_editor_font(self, font) -> None:
        """
        Set the editor font family or QFont instance.

        Args:
            font: A ``QFont`` instance or a font family name string.
        """
        if isinstance(font, QFont):
            self._font = QFont(font)
        else:
            self._font = QFont()
            self._font.setFamilies([str(font), "Consolas", "Courier New", "monospace"])
            self._font.setStyleHint(QFont.StyleHint.Monospace)

        self._font.setPointSize(self.font_size)
        self.setFont(self._font)
        self.setMarginsFont(self._font)

        if self._lexer and hasattr(self._lexer, "setFont"):
            self._lexer.setFont(self._font, -1)

    def set_editor_font_size(self, font_size: int) -> None:
        """Set the editor font point size."""
        self.font_size = int(font_size)

    def set_wrap_mode(self, enabled: bool = False) -> None:
        """Enable or disable word wrapping."""
        self.setWrapMode(
            QsciScintilla.WrapMode.WrapNone
            if not enabled
            else QsciScintilla.WrapMode.WrapWord
        )
        if not enabled:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    # ------------------------------------------------------------------
    # Keyboard events
    # ------------------------------------------------------------------

    def keyPressEvent(self, e: QKeyEvent) -> None:
        """Intercept key events for goto definition and enhanced enter/return behaviour."""
        if e.key() == Qt.Key.Key_F12:
            self.execute_goto_definition()
            e.accept()
            return

        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            line, index = self.getCursorPosition()
            current_line_text = self.text(line)

            base_indent = ""
            for ch in current_line_text:
                if ch in (" ", "\t"):
                    base_indent += ch
                else:
                    break

            if current_line_text.rstrip().endswith((":", "{", "(")):
                indent = base_indent + (" " * self._INDENTATION_SPACING)
            else:
                indent = base_indent

            self.beginUndoAction()
            self.insert("\n" + indent)
            self.endUndoAction()
            self.setCursorPosition(line + 1, len(indent))
            return

        super().keyPressEvent(e)

    # ------------------------------------------------------------------
    # Mouse events / hover
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, e):
        """Track cursor movement for breakpoint margin hover."""
        super().mouseMoveEvent(e)
        self._last_mouse_pos = e.position().toPoint()

        # Breakpoint Margin Hover Preview
        w0 = self.SendScintilla(QsciScintilla.SCI_GETMARGINWIDTHN, 0)
        w1 = self.SendScintilla(QsciScintilla.SCI_GETMARGINWIDTHN, 1)

        margin_start = w0
        margin_end = w0 + w1

        x = self._last_mouse_pos.x()
        y = self._last_mouse_pos.y()

        if margin_start <= x < margin_end:
            pos = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMPOINT, x, y)
            if pos != -1:
                line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, pos)
                self._update_hover_breakpoint(line)
            else:
                self._clear_hover_breakpoint()
        else:
            self._clear_hover_breakpoint()

    def leaveEvent(self, event):
        """Mouse left the editor — clear margin hover."""
        self._clear_hover_breakpoint()
        super().leaveEvent(event)

    def mousePressEvent(self, e: QKeyEvent) -> None:
        """Intercept Ctrl+Click for go-to-definition navigation."""
        if (
            e.button() == Qt.MouseButton.LeftButton
            and e.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            px = int(e.position().x())
            py = int(e.position().y())
            position = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMPOINT, px, py)
            if position != -1:
                line, col = self.lineIndexFromPosition(position)
                self.setCursorPosition(line, col)
                self.execute_goto_definition()
                e.accept()
                return

        super().mousePressEvent(e)

    def _dismiss_all_popups(self) -> None:
        """Dismiss every open sub-menu (hover flyout)."""
        self._dismiss_hover_flyout()

    # ------------------------------------------------------------------
    # Debugger and Breakpoints
    # ------------------------------------------------------------------

    @staticmethod
    def _create_circle_image(size: int, radius: int, color: QColor) -> QImage:
        """Draws a centered anti-aliased circle on a transparent QImage."""
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))

        center = size // 2
        painter.drawEllipse(center - radius, center - radius, radius * 2, radius * 2)
        painter.end()
        return image

    def _update_hover_breakpoint(self, line: int) -> None:
        """Render semi-transparent hover circle if line has no active breakpoint."""
        if line < 0 or line >= self.lines():
            self._clear_hover_breakpoint()
            return

        if self._hovered_breakpoint_line == line:
            return

        self._clear_hover_breakpoint()

        mask = self.markersAtLine(line)
        if not (mask & (1 << self.MARKER_BREAKPOINT)):
            self.markerAdd(line, self.MARKER_HOVER)
            self._hovered_breakpoint_line = line

    def _clear_hover_breakpoint(self) -> None:
        """Remove active hover preview circle."""
        if self._hovered_breakpoint_line is not None:
            self.markerDelete(self._hovered_breakpoint_line, self.MARKER_HOVER)
            self._hovered_breakpoint_line = None

    def _on_margin_clicked(
        self, margin: int, line: int, modifiers: Qt.KeyboardModifier
    ) -> None:
        """Handles click actions for breakpoints and colorpicker margins."""

        # BREAKPOINTS
        if margin == self.MARGIN_BREAKPOINT:
            mask = self.markersAtLine(line)
            if mask & (1 << self.MARKER_BREAKPOINT):
                self.markerDelete(line, self.MARKER_BREAKPOINT)
                self.markerAdd(line, self.MARKER_HOVER)
                self._hovered_breakpoint_line = line
            else:
                self.markerDelete(line, self.MARKER_HOVER)
                self.markerAdd(line, self.MARKER_BREAKPOINT)
                self._hovered_breakpoint_line = None

        # COLORWHEEL
        elif margin == self.COLOR_MARGIN:
            info = self._get_color_by_line(line)
            if not info:
                return

            current_color, old_str, start_col, end_col = info

            options = QColorDialog.ColorDialogOption.ShowAlphaChannel
            new_color = QColorDialog.getColor(
                current_color, self, "Select Color", options
            )

            if new_color.isValid() and new_color != current_color:
                self._apply_color_to_line(line, old_str, new_color, start_col, end_col)

    def get_breakpoint_lines(self) -> set[int]:
        """
        Scans the document and returns a set of 1-based line numbers where
        breakpoint markers currently exist.
        """
        breakpoint_lines = set()

        mask = 1 << self.MARKER_BREAKPOINT
        current_line = 0
        total_lines = self.lines()

        while current_line < total_lines:
            found_line = self.markerFindNext(current_line, mask)
            if found_line == -1:
                break

            breakpoint_lines.add(found_line + 1)

            current_line = found_line + 1

        return breakpoint_lines

    def set_execution_line_highlight(self, line: int) -> None:
        """Highlight the given 1-based line as the current execution point.

        Removes any previous execution highlight before applying the new
        one so that only a single line is highlighted at any time.

        Args:
            line: 1-based line number to highlight.
        """
        self.clear_all_execution_highlights()
        line_idx = line - 1
        if 0 <= line_idx < self.lines():
            self.markerAdd(line_idx, self.MARKER_EXEC_LINE)
            self.ensureLineVisible(line_idx)

    def clear_all_execution_highlights(self) -> None:
        """Remove every execution-line highlight marker from the document."""
        self.markerDeleteAll(self.MARKER_EXEC_LINE)

    def show_debug_stack_frame(
        self, line: int, info_text: str = "Stack Info Placeholder"
    ):
        """Displays a red-bordered frame widget directly below the given
        1-based line number.
        Pushes lower lines down to make space.
        """
        # Clear the annotation at the previous paused line so that the
        # editor layout doesn't accumulate orphaned gaps when stepping.
        if self._paused_line != -1 and self._paused_line != line:
            old_idx = self._paused_line - 1
            if 0 <= old_idx < self.lines():
                self.clearAnnotations(old_idx)

        self._paused_line = line
        line_idx = line - 1  # Convert to 0-based for QScintilla

        if self._debug_stack_widget is None:
            self._debug_stack_widget = StackInfoFrame(self)

        self._debug_stack_widget.content_label.setText(info_text)
        self.annotate(line_idx, "\n\n", 0)

        self._debug_stack_widget.show()
        self._update_debug_stack_position()

    def hide_debug_stack_frame(self):
        """
        Removes the debug stack frame and collapses reserved space back
        together.
        """
        if self._paused_line != -1:
            line_idx = self._paused_line - 1
            # Clear annotation gap
            self.clearAnnotations(line_idx)
            self._paused_line = -1

        if self._debug_stack_widget:
            self._debug_stack_widget.hide()

    def _update_debug_stack_position(self):
        """
        Calculates exact viewport coordinates and moves/resizes frame
        on viewport scroll or resize.
        """
        if self._paused_line < 1 or self._debug_stack_widget is None:
            return

        line_idx = self._paused_line - 1

        char_pos = self.positionFromLineIndex(line_idx, 0)
        line_y = self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, char_pos)
        line_height = self.SendScintilla(QsciScintilla.SCI_TEXTHEIGHT, line_idx)

        margin_offset = sum(
            self.marginWidth(i) for i in range(5) if self.marginWidth(i) > 0
        )

        frame_x = margin_offset + 10
        frame_y = line_y + line_height + 2
        frame_width = max(300, self.viewport().width() - frame_x - 35)
        frame_height = 55

        if frame_y < 0 or frame_y > self.viewport().height():
            self._debug_stack_widget.hide()
        else:
            self._debug_stack_widget.show()
            self._debug_stack_widget.setGeometry(
                frame_x, frame_y, frame_width, frame_height
            )

    # ------------------------------------------------------------------
    # ColorWheel
    # ------------------------------------------------------------------

    def _get_color_by_line(self, line_number: int) -> tuple[Any, str, int, int] | None:
        """
        Scans a specific line and extracts the indicated color from it by
        using a set of compiled regular expressions (COLOR_REGEX)
        """
        line_text = self.text(line_number)
        match = self.COLOR_REGEX.search(line_text)
        if not match:
            return None

        color_str = match.group(0)
        color = self._parse_color(color_str)

        if color and color.isValid():
            return (color, color_str, match.start(), match.end())

        return None

    def _parse_color(self, color_str: str) -> QColor | None:
        """
        Parses Hex, RGB, or RGBA string colors into QColor instances.
        """
        color_str = color_str.strip()

        if color_str.startswith("#"):  # HEX
            hex_body = color_str[1:]
            if len(hex_body) in (3, 4):
                expanded = "".join(c * 2 for c in hex_body)
                # This case is for shortened hex colors, e.g.: #333
                color_str = f"#{expanded}"

            color = QColor(color_str)
            return color if color.isValid() else None

        if color_str.startswith("rgb"):  # RGB / RGBA
            nums = re.findall(r"[\d\.]+", color_str)
            if len(nums) in (3, 4):
                r, g, b = map(int, nums[:3])
                a = int(float(nums[3]) * 255) if len(nums) == 4 else 255
                return QColor(r, g, b, a)

        return None

    def _create_color_swatch(self, color: QColor, size: int = 14) -> QPixmap:
        """Draws a clean, rounded square color preview with a border."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if color.alpha() < 255:
            painter.fillRect(0, 0, size, size, QColor(220, 220, 220))
            painter.fillRect(0, 0, size // 2, size // 2, QColor(255, 255, 255))
            painter.fillRect(
                size // 2, size // 2, size // 2, size // 2, QColor(255, 255, 255)
            )

        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor(120, 120, 120, 200), 1))
        painter.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
        painter.end()

        return pixmap

    def _get_or_create_color_marker(self, color: QColor) -> int:
        """Returns an existing marker ID for this color, or defines a new one."""
        rgba = color.rgba()
        if rgba in self._color_marker_cache:
            return self._color_marker_cache[rgba]

        marker_id = self._next_color_marker_id
        self._next_color_marker_id += 1
        if self._next_color_marker_id > self.COLOR_MARKER_END:
            self._next_color_marker_id = self.COLOR_MARKER_START

        for cached_rgba, m_id in list(self._color_marker_cache.items()):
            if m_id == marker_id:
                del self._color_marker_cache[cached_rgba]
                break

        swatch = self._create_color_swatch(color)
        self.markerDefine(swatch, marker_id)

        self._color_marker_cache[rgba] = marker_id
        return marker_id

    def update_line_color_indicator(self, line_number: int) -> None:
        """Checks a line for a color string and updates its margin marker."""
        info = self._get_color_by_line(line_number)

        for m_id in range(self.COLOR_MARKER_START, self.COLOR_MARKER_END + 1):
            self.markerDelete(line_number, m_id)

        if info:
            color, _, _, _ = info
            marker_id = self._get_or_create_color_marker(color)
            self.markerAdd(line_number, marker_id)

    def update_visible_color_indicators(self) -> None:
        """Scans and updates color markers only for lines currently visible in the editor."""
        first_line = self.firstVisibleLine()
        visible_count = self.SendScintilla(QsciScintilla.SCI_LINESONSCREEN)

        if visible_count <= 0:
            last_line = self.lines()
        else:
            last_line = min(self.lines(), first_line + visible_count + 1)

        for line in range(first_line, last_line):
            self.update_line_color_indicator(line)

    def _apply_color_to_line(
        self, line: int, old_str: str, new_color: QColor, start_col: int, end_col: int
    ) -> None:
        """Replaces the color string in the editor while preserving undo history."""
        new_str = self._format_color_string(old_str, new_color)

        self.beginUndoAction()
        self.setSelection(line, start_col, line, end_col)
        self.replaceSelectedText(new_str)
        self.endUndoAction()

    def _format_color_string(self, old_str: str, new_color: QColor) -> str:
        """
        Formats new_color to match the format (Hex/RGB/RGBA) and case of
        old_str.
        """
        r, g, b, a = (
            new_color.red(),
            new_color.green(),
            new_color.blue(),
            new_color.alpha(),
        )

        # RGB/RGBA
        if old_str.strip().startswith("rgb"):
            if "rgba" in old_str or a < 255:
                alpha_str = f"{a / 255.0:.2f}".rstrip("0").rstrip(".")
                return f"rgba({r}, {g}, {b}, {alpha_str})"
            return f"rgb({r}, {g}, {b})"

        is_uppercase = any(c.isupper() for c in old_str)

        # HEX RGB/RGBA/RRGGBB/RRGGBBAA
        if a < 255:
            hex_str = f"#{r:02x}{g:02x}{b:02x}{a:02x}"
        else:
            hex_str = f"#{r:02x}{g:02x}{b:02x}"

        return hex_str.upper() if is_uppercase else hex_str

    # ------------------------------------------------------------------
    # Go-to definition
    # ------------------------------------------------------------------

    def execute_goto_definition(self, line: int = None, col: int = None) -> None:
        """Resolve the symbol under the cursor and navigate to its definition.

        When *line* and *col* are ``None`` (the default), the current
        cursor position is used.  Callers that know the exact position
        — e.g. the documentation flyout — can pass explicit coordinates.

        Falls back gracefully if no provider is active or the symbol
        cannot be resolved.  All provider errors are caught so that a
        plugin failure never crashes the editor.
        """
        if not self.current_provider:
            return

        try:
            if line is None or col is None:
                line, col = self.getCursorPosition()
            target = self.current_provider.get_definition_location(
                self.text(), line, col
            )

            if not target:
                return

            file_path, target_line, target_col = target

            # Guard: empty or None file path — nothing to navigate to.
            if not file_path:
                return

            # Guard: already at the definition (same file + same line).
            current_path = getattr(self, "current_file_path", "") or ""
            if file_path == current_path and target_line == line:
                return

            tab_widget = self._parent
            if tab_widget and hasattr(tab_widget, "open_file_at_line"):
                tab_widget.open_file_at_line(file_path, target_line)

                current_editor = tab_widget.currentWidget()
                if current_editor and hasattr(current_editor, "setCursorPosition"):
                    current_editor.setCursorPosition(target_line, target_col)
        except Exception as exc:
            logger.debug("Go-to-definition failed: %s", exc)

    # ------------------------------------------------------------------
    # Language / lexer
    # ------------------------------------------------------------------

    def setLanguage(self, lang: str) -> None:
        """Assign a language to the editor and isolate native folding features."""
        self._teardown_hover_engine()

        if not lang:
            self._lexer = None
            self.setLexer(None)
            self.current_lang = None
            self.current_provider = None
            return

        self.current_lang = lang
        self.current_provider = LanguageRegistry.get_provider(lang)
        config = LanguageRegistry.get_config(lang)

        if config:
            self._lexer = self._create_lexer(lang, config)
            self.setLexer(self._lexer)

            if hasattr(self._lexer, "setFont"):
                self._lexer.setFont(self._font, -1)
            self._apply_semantic_indicators()
            self._recompute_folds()
        else:
            self._lexer = None
            self.setLexer(None)

        self._setup_hover_engine()

    def _create_lexer(self, lang: str, config: dict):
        """Create an ``IronicaLexer`` for *lang*.

        ``IronicaLexer`` is a combined lexer that handles keyword
        highlighting, bracket pair colorization with depth tracking,
        numeric literals, and operators — all with colours read from
        the language JSON config.
        """
        return IronicaLexer(self, config)

    # ------------------------------------------------------------------
    # Semantic indicators (imports, special keywords)
    # ------------------------------------------------------------------

    @staticmethod
    def _scintilla_rgb(hex_color: str) -> int:
        """Convert a ``#RRGGBB`` CSS colour to Scintilla's ``0x00BBGGRR``."""
        from PyQt6.QtGui import QColor

        c = QColor(hex_color)
        return ((c.blue() & 0xFF) << 16) | ((c.green() & 0xFF) << 8) | (c.red() & 0xFF)

    # Slot indices used for Scintilla indicators (up to 8 reserved).
    _IND_PROVIDER_BASE = 0

    def _apply_semantic_indicators(self) -> None:
        """Apply Scintilla indicators driven by the language provider.

        Calls ``current_provider.get_semantic_highlights(text)`` if
        available.  The provider returns semantic-only
        ``(start, length, "#RRGGBB")`` tuples which are painted as
        ``INDIC_TEXTFORE`` overlays.  Up to 8 concurrent indicator slots
        are used (colour-keyed); excess shares the last slot.

        Always clears all indicator slots before reapplying so that
        stale overlays from a previous buffer state are never left
        behind.
        """
        from PyQt6.QtGui import QColor

        if not self.current_provider:
            return

        text = self.text()
        if not text:
            return

        length = len(text)

        # ── always clear all indicator slots first ────────────────
        for ind in range(8):
            self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, ind)
            self.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, 0, length)

        # Ask the provider for semantic highlight ranges.
        provider_fn = getattr(self.current_provider, "get_semantic_highlights", None)
        if provider_fn is None:
            return
        try:
            highlights = provider_fn(text)
        except Exception:
            return

        if not highlights:
            return

        # ── group by colour → one indicator slot per colour ──────
        _SLOTS = 8
        colour_to_slot: dict = {}
        next_slot = 0

        for start, token_len, colour_hex in highlights:
            if start < 0 or token_len <= 0 or start + token_len > length:
                continue

            slot = colour_to_slot.get(colour_hex)
            if slot is None:
                slot = next_slot % _SLOTS
                colour_to_slot[colour_hex] = slot
                next_slot += 1
                self.SendScintilla(
                    QsciScintilla.SCI_INDICSETSTYLE, slot, QsciScintilla.INDIC_TEXTFORE
                )
                self.SendScintilla(
                    QsciScintilla.SCI_INDICSETFORE,
                    slot,
                    self._scintilla_rgb(colour_hex),
                )

            self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, slot)
            self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE, start, token_len)

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def load_from_file(self, file_path: str) -> None:
        """Load file contents into the editor.

        Attempts UTF-8 decoding first, then falls back to the system
        default encoding. Sets the editor to read-only when the file on
        disk lacks write permissions.

        Args:
            file_path: Absolute path to the file to load.

        Raises:
            FileNotFoundError: If the file does not exist.
            PermissionError: If the file cannot be read.
            UnicodeDecodeError: If the file cannot be decoded (after
                fallback attempt).
        """
        path_obj = pathlib.Path(file_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Try UTF-8 first, then fall back to system default.
        content = None
        for encoding in ("utf-8", "utf-8-sig", None):
            try:
                kwargs = {"encoding": encoding} if encoding else {}
                with open(file_path, "r", **kwargs) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            # Final fallback: read as bytes, replace errors.
            with open(file_path, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")

        self.current_file_path = file_path

        # Invalidate the semantic provider cache before setText so the
        # debounced refresh always computes fresh results for the new
        # buffer content.
        if self.current_provider and hasattr(self.current_provider, "invalidate_cache"):
            try:
                self.current_provider.invalidate_cache()
            except Exception:
                pass

        self.setText(content)
        self.setModified(False)
        self._is_dirty = False
        self.dirty_state_changed.emit(False)
        self._dismiss_hover_flyout()
        self._recompute_folds()

        # Check read-only permissions.
        try:
            if not (path_obj.stat().st_mode & stat.S_IWUSR):
                self.setReadOnly(True)
        except OSError as exc:
            logger.warning(
                "Could not check file permissions for %s: %s", file_path, exc
            )

    def clear_dirty(self) -> None:
        """Reset the editor's modified (dirty) flag."""
        self.setModified(False)
        if self._is_dirty:
            self._is_dirty = False
            self.dirty_state_changed.emit(False)

    def is_dirty(self) -> bool:
        """Return ``True`` if the editor buffer has been modified."""
        return self._is_dirty

    def save(self) -> bool:
        """Save the current buffer to ``current_file_path``.

        If no file path is set, delegates to ``save_as()``.

        Returns:
            ``True`` on success, ``False`` on failure or cancellation.
        """
        if self.current_file_path:
            return self.save_to_file(self.current_file_path)
        return self.save_as()

    def save_as(self) -> bool:
        """Prompt the user for a path and save the buffer.

        Returns:
            ``True`` on success, ``False`` on failure or cancellation.
        """
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            self.current_file_path or "",
            "All Files (*)",
        )
        if not file_path:
            return False
        return self.save_to_file(file_path)

    def save_to_file(self, file_path: str) -> bool:
        """Write the editor buffer to *file_path*.

        Args:
            file_path: Destination path (overwritten if it exists).

        Returns:
            ``True`` on success, ``False`` on any I/O error.
        """
        try:
            content = self.text()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.current_file_path = file_path
            self.setModified(False)
            if self._is_dirty:
                self._is_dirty = False
                self.dirty_state_changed.emit(False)
            return True
        except OSError as exc:
            logger.error("Save failed for %s: %s", file_path, exc)
            return False

    # ------------------------------------------------------------------
    # Clipboard helpers
    # ------------------------------------------------------------------

    def copy_selection_as_plain_text(self) -> None:
        """Copy the current selection to the system clipboard as plain text."""
        selected_text = self.selectedText()
        if selected_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(selected_text)

    # ------------------------------------------------------------------
    # Read-only management
    # ------------------------------------------------------------------

    def make_file_readonly(self) -> None:
        """Toggle the file's read-only permission on disk and in the editor."""
        if not self.current_file_path:
            from editor.widgets.QExitDialog import ConfirmDialog

            dialog = ConfirmDialog(
                parent=self,
                title="No File Path",
                message="This file isn't provided with a path. Save it first.",
                confirm_text="OK",
                cancel_text="CANCEL",
                destructive=False,
            )
            dialog.exec()
            return

        try:
            file_path = pathlib.Path(self.current_file_path)
            current_mode = file_path.stat().st_mode

            if current_mode & stat.S_IWUSR:
                new_mode = current_mode & ~stat.S_IWUSR
                self.setReadOnly(True)
                self._update_readonly_tab_indicator(True)
            else:
                new_mode = current_mode | stat.S_IWUSR | stat.S_IXUSR
                self.setReadOnly(False)
                self._update_readonly_tab_indicator(False)

            file_path.chmod(new_mode)
        except OSError as exc:
            logger.error("Could not change file permissions: %s", exc)
            from editor.widgets.QExitDialog import ConfirmDialog

            dialog = ConfirmDialog(
                parent=self,
                title="Read-Only Error",
                message=f"Could not change file permissions: {exc}",
                confirm_text="OK",
                cancel_text="CANCEL",
                destructive=False,
            )
            dialog.exec()

    def _update_readonly_tab_indicator(self, is_readonly: bool) -> None:
        """Notify the tab bar to show or hide the read-only lock icon."""
        tab_widget = self._parent
        if tab_widget is None:
            return
        tab_bar = tab_widget.tabBar()
        for i in range(tab_widget.count()):
            if tab_widget.widget(i) is self:
                tab_bar.mark_readonly(i, is_readonly)
                break

    # ------------------------------------------------------------------
    # Code formatting
    # ------------------------------------------------------------------

    def format_current_file(self) -> None:
        """Pass the buffer through the current provider's formatter.

        All provider errors are caught so that a plugin failure
        never crashes the editor.
        """
        if not self.current_provider:
            return

        try:
            raw_text = self.text()
            formatted_text = self.current_provider.format_source(raw_text)

            if formatted_text and formatted_text != raw_text:
                line, col = self.getCursorPosition()
                first_visible = self.SendScintilla(
                    QsciScintilla.SCI_GETFIRSTVISIBLELINE
                )

                self.beginUndoAction()
                self.setText(formatted_text)
                self.endUndoAction()

                total_lines = self.lines()
                clamped_line = max(0, min(line, total_lines - 1))
                self.setCursorPosition(clamped_line, col)
                self.SendScintilla(QsciScintilla.SCI_SETFIRSTVISIBLELINE, first_visible)
        except Exception as exc:
            logger.debug("Format query failed: %s", exc)

    # ------------------------------------------------------------------
    # Diagnostic Underlining
    # ------------------------------------------------------------------

    def add_diagnostic_underline(
        self, line: int, start_col: int, end_col: int, color_hex: str = "#FF0000"
    ) -> None:
        """
        Applies a precise squiggly error underline to the selected text block bounds.
        Splits coordinates to strictly target valid non-whitespace text strings,
        avoiding spaces. Calculates character indices to UTF-8 byte mapping to avoid offset
        drift with special characters.
        """
        if line < 0 or line >= self.lines():
            return

        line_text = self.text(line)
        start_col = max(0, min(start_col, len(line_text)))
        end_col = max(start_col, min(end_col, len(line_text)))

        # Dynamic indicator registration for colors
        if color_hex not in self._diagnostic_indicators:
            slot = self._next_diag_slot
            self._diagnostic_indicators[color_hex] = slot

            # Rotate slot keys within the 8-15 allocation block
            self._next_diag_slot = 8 + ((self._next_diag_slot - 7) % 8)

            # Configure indicator format parameters (1 = INDIC_SQUIGGLE)
            self.SendScintilla(QsciScintilla.SCI_INDICSETSTYLE, slot, 1)
            self.SendScintilla(
                QsciScintilla.SCI_INDICSETFORE, slot, self._scintilla_rgb(color_hex)
            )
        else:
            slot = self._diagnostic_indicators[color_hex]

        target_substring = line_text[start_col:end_col]
        line_start_byte = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMLINE, line)
        if line_start_byte == -1:
            return

        for match in re.finditer(r"[^\s]+", target_substring):
            match_start_char = start_col + match.start()
            match_end_char = start_col + match.end()

            byte_start = line_start_byte + len(
                line_text[:match_start_char].encode("utf-8")
            )
            byte_len = len(line_text[match_start_char:match_end_char].encode("utf-8"))

            self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, slot)
            self.SendScintilla(
                QsciScintilla.SCI_INDICATORFILLRANGE, byte_start, byte_len
            )

    def clear_diagnostic_underlines(self) -> None:
        """
        Instantly wipe out all diagnostic squiggle decorations across the
        entire buffer.
        """
        doc_length = self.SendScintilla(QsciScintilla.SCI_GETLENGTH)
        if doc_length <= 0:
            return

        for slot in range(8, 16):
            self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, slot)
            self.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, 0, doc_length)

    # ------------------------------------------------------------------
    # Ghost Text System (End-of-Line and Inline Annotations)
    # ------------------------------------------------------------------

    def set_ghost_text(self, line: int, text: str, color_hex: str = "#8a8a8a") -> None:
        """
        Renders light gray overlay annotation text directly beneath or after a
        target line. Perfect for structural descriptions like "(+5 more imports)" or
        custom inline messages.
        """
        if line < 0 or line >= self.lines():
            return

        style_id = 140
        self.SendScintilla(
            QsciScintilla.SCI_STYLESETFORE, style_id, self._scintilla_rgb(color_hex)
        )

        if hasattr(self._font, "family"):
            self.SendScintilla(
                QsciScintilla.SCI_STYLESETFONT,
                style_id,
                self._font.family().encode("utf-8"),
            )
        self.SendScintilla(
            QsciScintilla.SCI_STYLESETSIZE, style_id, self._font.pointSize()
        )

        self.SendScintilla(2540, line, text.encode("utf-8"))
        self.SendScintilla(2542, line, style_id)

        self.SendScintilla(2544, 1)

    def clear_ghost_text(self, line: int) -> None:
        """Clear custom ghost text rendered on a specific line index."""
        if line < 0 or line >= self.lines():
            return
        self.SendScintilla(2540, line, b"")

    def clear_all_ghost_text(self) -> None:
        """Clear every active ghost text annotation throughout the entire document buffer."""
        # SCI_ANNOTATIONCLEARALL = 2546
        self.SendScintilla(2546)
