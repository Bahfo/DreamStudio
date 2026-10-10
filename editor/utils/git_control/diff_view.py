"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Side-by-side diff view for changed files in source control.
"""

import difflib
import os
from typing import Any, List, Optional, Tuple

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLabel, QSplitter, QVBoxLayout, QWidget

DEL_MARKER = 8
ADD_MARKER = 9
MAX_HIGHLIGHT_LINES = 5000

DEL_DARK = "#5a1d1d"
ADD_DARK = "#1d4d2b"
DEL_LIGHT = "#f2c4c4"
ADD_LIGHT = "#c4e6c4"


def resolve_language(path: str) -> Optional[str]:
    """Return the editor language identifier for a file path.

    Args:
        path: Repository-relative file path.

    Returns:
        Language identifier, or ``None`` when the extension is unknown.
    """
    ext = os.path.splitext(path)[1].lower()
    if not ext:
        return None
    try:
        from editor.Ironica.language_engine import LanguageRegistry

        return LanguageRegistry.get_language_by_extension(ext)
    except Exception:
        return None


def compute_blocks(
    old: str, new: str
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """Compute changed-line ranges for a file pair.

    Args:
        old: HEAD content.
        new: Working-tree content.

    Returns:
        ``(left_blocks, right_blocks)`` as 0-based ``(start, end)`` ranges.
    """
    matcher = difflib.SequenceMatcher(
        a=old.splitlines(), b=new.splitlines(), autojunk=False
    )
    left_blocks: List[Tuple[int, int]] = []
    right_blocks: List[Tuple[int, int]] = []
    total = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            left_blocks.append((i1, i2))
            total += i2 - i1
        if tag in ("insert", "replace"):
            right_blocks.append((j1, j2))
            total += j2 - j1
        if total > MAX_HIGHLIGHT_LINES:
            break
    return left_blocks, right_blocks


def _theme_is_dark(theme_name: Optional[str] = None) -> bool:
    """Return whether a theme is a dark theme.

    Args:
        theme_name: Theme to inspect, or ``None`` for the active theme.

    Returns:
        ``True`` for dark themes, ``False`` for light ones.
    """
    try:
        from editor.Ironica.retheme import active_theme_name, editor_colors

        name = theme_name or active_theme_name()
        return editor_colors(name)["bg"].lightness() < 128
    except Exception:
        return True


def _marker_color(theme_name: Optional[str], dark: str, light: str) -> QColor:
    """Pick the dark or light marker color for a theme.

    Args:
        theme_name: Theme deciding the variant.
        dark: Color used on dark themes.
        light: Color used on light themes.

    Returns:
        Theme-appropriate ``QColor``.
    """
    return QColor(dark if _theme_is_dark(theme_name) else light)


def _paint_blocks(
    editor: Any,
    blocks: List[Tuple[int, int]],
    marker: int,
    dark: str,
    light: str,
    theme_name: Optional[str] = None,
) -> None:
    """Paint full-line background markers over line ranges.

    Args:
        editor: Target diff pane.
        blocks: 0-based ``(start, end)`` line ranges.
        marker: Scintilla marker number to use.
        dark: Marker color on dark themes.
        light: Marker color on light themes.
        theme_name: Theme deciding the variant.
    """
    editor.markerDefine(QsciScintilla.MarkerSymbol.Background, marker)
    editor.setMarkerBackgroundColor(_marker_color(theme_name, dark, light), marker)
    for start, end in blocks:
        for line in range(start, end):
            try:
                editor.markerAdd(line, marker)
            except Exception:
                pass


def _recolor_markers(
    editor: Any, marker: int, dark: str, light: str, theme_name: str
) -> None:
    """Refresh a marker's color for a theme.

    Args:
        editor: Target diff pane.
        marker: Scintilla marker number to recolor.
        dark: Marker color on dark themes.
        light: Marker color on light themes.
        theme_name: Theme deciding the variant.
    """
    editor.markerDefine(QsciScintilla.MarkerSymbol.Background, marker)
    editor.setMarkerBackgroundColor(_marker_color(theme_name, dark, light), marker)


class DiffView(QWidget):
    """Side-by-side read-only diff tab with themed panes.

    Attributes:
        left: HEAD content pane.
        right: Working-tree content pane.
        left_blocks: Changed-line ranges in the left pane.
        right_blocks: Changed-line ranges in the right pane.
    """

    is_diff_view = True

    def __init__(
        self,
        path: str,
        old: str,
        new: str,
        language: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Build header labels, themed panes, highlights, and scroll sync.

        Args:
            path: Repository-relative file path (used for the headers).
            old: HEAD content.
            new: Working-tree content (empty when deleted).
            language: Editor language identifier for highlighting.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.path = path
        self.left_blocks, self.right_blocks = compute_blocks(old, new)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_box, self.left = self._build_pane("HEAD", old, language)
        if new:
            right_box, self.right = self._build_pane("Working Tree", new, language)
        else:
            right_box, self.right = self._build_pane(
                "Working Tree (deleted)", "", language
            )
        splitter.addWidget(left_box)
        splitter.addWidget(right_box)
        layout.addWidget(splitter)
        self._paint(getattr(self.left, "_theme_name", None))
        self._sync_scroll()

    @staticmethod
    def _build_pane(
        header: str, content: str, language: Optional[str]
    ) -> Tuple[QWidget, Any]:
        """Build one labeled read-only pane.

        Args:
            header: Label shown above the editor.
            content: File content to display.
            language: Editor language identifier for highlighting.

        Returns:
            ``(container, editor)`` tuple.
        """
        from editor.Ironica.code_editor import CodeEditor

        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(QLabel(header))
        editor = CodeEditor(box, language=language)
        editor.setText(content)
        editor.setReadOnly(True)
        try:
            editor.setCaretWidth(0)
        except Exception:
            pass
        try:
            editor.setModified(False)
            editor.clear_save_indicators()
        except Exception:
            pass
        layout.addWidget(editor, 1)
        return box, editor

    def _paint(self, theme_name: Optional[str] = None) -> None:
        """Paint change markers on both panes.

        Args:
            theme_name: Theme deciding the marker colors.
        """
        try:
            _paint_blocks(
                self.left, self.left_blocks, DEL_MARKER, DEL_DARK, DEL_LIGHT,
                theme_name,
            )
        except Exception:
            pass
        try:
            _paint_blocks(
                self.right, self.right_blocks, ADD_MARKER, ADD_DARK, ADD_LIGHT,
                theme_name,
            )
        except Exception:
            pass

    def _sync_scroll(self) -> None:
        """Scroll both panes together, vertically and horizontally."""
        state = {"on": False}

        def _forward(dst, value: int) -> None:
            if state["on"]:
                return
            state["on"] = True
            try:
                if dst.value() != value:
                    dst.setValue(value)
            finally:
                state["on"] = False

        lv, rv = self.left.verticalScrollBar(), self.right.verticalScrollBar()
        lh, rh = self.left.horizontalScrollBar(), self.right.horizontalScrollBar()
        lv.valueChanged.connect(lambda v: _forward(rv, v))
        rv.valueChanged.connect(lambda v: _forward(lv, v))
        lh.valueChanged.connect(lambda v: _forward(rh, v))
        rh.valueChanged.connect(lambda v: _forward(rh, lh, v))

    def retheme(self, theme_name: str) -> None:
        """Re-apply a theme to both panes and their change markers.

        Args:
            theme_name: Theme to apply (e.g. ``"dark"``).
        """
        for editor in (self.left, self.right):
            try:
                editor.retheme(theme_name)
            except Exception:
                pass
        try:
            _recolor_markers(self.left, DEL_MARKER, DEL_DARK, DEL_LIGHT, theme_name)
        except Exception:
            pass
        try:
            _recolor_markers(self.right, ADD_MARKER, ADD_DARK, ADD_LIGHT, theme_name)
        except Exception:
            pass


def match_diff_fonts(view: DiffView, tab_editor: Any) -> None:
    """Copy the active editor font family and size onto diff panes.

    Args:
        view: Diff view whose panes receive the font.
        tab_editor: Central tab widget hosting the current editor.
    """
    try:
        cur = tab_editor.currentWidget()
        ref = getattr(cur, "editor", None) or cur
        family = getattr(getattr(ref, "_font", None), "family", None)
        size = getattr(ref, "font_size", None)
        for pane in (view.left, view.right):
            try:
                if callable(family):
                    pane.set_editor_font(family())
                if isinstance(size, int):
                    pane.font_size = size
            except Exception:
                pass
    except Exception:
        return


def build_diff_tab(tab_editor: Any, path: str, old: str, new: str) -> Optional[QWidget]:
    """Open a themed side-by-side diff tab for a file pair.

    Args:
        tab_editor: Central tab widget receiving the new tab.
        path: Repository-relative file path (used for title and language).
        old: HEAD content.
        new: Working-tree content.

    Returns:
        The new tab widget.
    """
    view = DiffView(path, old, new, resolve_language(path))
    match_diff_fonts(view, tab_editor)
    name = os.path.basename(path)
    title = f"Diff: {name} (deleted)" if not new else f"Diff: {name}"
    index = tab_editor.addTab(view, title)
    tab_editor.setCurrentIndex(index)
    try:
        tab_editor.setFocus()
    except Exception:
        pass
    return view
