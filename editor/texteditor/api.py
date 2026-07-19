"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved

Public API for the DreamStudio text editor.

This module exposes a clean, minimal interface for all editor
operations.  The rest of the IDE should never manipulate the
editor widget directly.

``EditorAPI`` is a thin, stateless facade that wraps a ``CodeEditor``
instance and validates every operation before forwarding it.

``FoldManager`` provides an abstract, language-agnostic folding
interface that directly controls QScintilla's internal margin and
folding UI, mirroring the clean aesthetics of JetBrains IDEs.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QWidget
from PyQt6.Qsci import QsciScintilla

logger = logging.getLogger(__name__)


# ==================================================================
# FoldManager — abstract, language-agnostic folding controller
# ==================================================================


@dataclass
class FoldRegion:
    """A single collapsible code region.

    Attributes:
        start_line: First line of the foldable block (0-indexed).
        end_line:   Last line of the foldable block (0-indexed, inclusive).
        label:      Optional placeholder text shown when collapsed
                    (e.g. ``"..."`` or ``"# 5 hidden lines"``).
        kind:       Category tag for the region (``"import"``,
                    ``"class"``, ``"function"``, ``"block"``, etc.).
        folded:     Whether the region is currently collapsed.
    """
    start_line: int
    end_line: int
    label: str = "..."
    kind: str = "block"
    folded: bool = False


class _FoldMarginMarker(QWidget):
    """Custom-painted fold marker replacing QScintilla's default
    ugly box-style markers.

    Renders a clean JetBrains-style ``+`` / ``−`` indicator inside
    a rounded rectangle with smooth antialiased lines.
    """

    def __init__(self, expanded: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self._expanded = expanded
        self.setFixedSize(16, 16)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background circle.
        bg = QColor(100, 100, 100, 60)
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.PenStyle.NoPen)
        r = self.rect().adjusted(1, 1, -1, -1)
        painter.drawEllipse(r)

        # + / − sign.
        painter.setPen(QPen(QColor(200, 200, 200), 1.5))
        cx, cy = r.center().x(), r.center().y()
        half = 3
        painter.drawLine(cx - half, cy, cx + half, cy)
        if self._expanded:
            painter.drawLine(cx, cy - half, cx, cy + half)

        painter.end()


class FoldManager:
    """Language-agnostic fold region manager for a ``QsciScintilla``
    editor.

    ``FoldManager`` owns:

    - A dedicated QScintilla margin (Margin 2 by default) for fold
      markers.
    - The list of ``FoldRegion`` objects registered by language
      plugins.
    - Custom ``_FoldMarginMarker`` painting for clean visual
      indicators.

    Language plugins call :meth:`register_fold_region` (or
    :meth:`set_fold_regions` for bulk updates) to tell the manager
    where collapsible blocks exist.  The manager translates these
    into QScintilla fold levels on the appropriate margin.

    **Lifecycle:**

    1. Created once per ``CodeEditor`` (typically by ``EditorAPI``).
    2. Language plugin calls ``set_fold_regions(...)`` after loading
       or editing a file.
    3. User clicks a fold marker → QScintilla toggles fold level →
       manager synchronises its ``FoldRegion.folded`` state.

    **Margin layout (JetBrains standard)::**

        [Margin 0: Line Numbers] [Margin 1: Folding] [Margin 2: Text]
    """

    # Default fold margin index (between line numbers and text).
    FOLD_MARGIN = 1
    # Width of the fold marker gutter in pixels.
    FOLD_MARGIN_WIDTH = 16
    # Mask: only the fold margin accepts mouse clicks.
    FOLD_MARGIN_MASK = 0b100  # bit 2 = margin index 2 in Scintilla terms

    def __init__(self, editor: QsciScintilla) -> None:
        if editor is None:
            raise ValueError("FoldManager requires a non-None editor")
        self._editor = editor
        self._regions: List[FoldRegion] = []
        self._setup_margin()

    # ------------------------------------------------------------------
    # Margin configuration
    # ------------------------------------------------------------------

    def _setup_margin(self) -> None:
        """Configure the dedicated fold margin with clean markers."""
        e = self._editor

        # Use Margin 1 for folding (Margin 0 = line numbers).
        e.setMarginType(self.FOLD_MARGIN, QsciScintilla.MarginType.SymbolMargin)
        e.setMarginWidth(self.FOLD_MARGIN, self.FOLD_MARGIN_WIDTH)
        e.setMarginSensitivity(self.FOLD_MARGIN, True)
        e.setMarginMarkerMask(self.FOLD_MARGIN, QsciScintilla.SC_MASK_FOLDERS)

        # Clean fold marker colours.
        pal = e.palette()
        bg = pal.color(pal.ColorRole.Window)
        mid = bg.lighter(130) if bg.lightness() < 128 else bg.darker(115)

        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDER)
        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDEROPEN)
        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDEREND)
        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL)
        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDERTAIL)
        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDERSUB)

        # Folder closed / open / end-of-folder symbols.
        e.markerDefine(QsciScintilla.MarkerSymbol.BoxedPlus, QsciScintilla.SC_MARKNUM_FOLDER)
        e.markerDefine(QsciScintilla.MarkerSymbol.BoxedMinus, QsciScintilla.SC_MARKNUM_FOLDEROPEN)
        e.markerDefine(QsciScintilla.MarkerSymbol.BoxedPlus, QsciScintilla.SC_MARKNUM_FOLDEREND)
        e.markerDefine(QsciScintilla.MarkerSymbol.BoxedMinus, QsciScintilla.SC_MARKNUM_FOLDEROPENMID)
        e.markerDefine(QsciScintilla.MarkerSymbol.VerticalLine, QsciScintilla.SC_MARKNUM_FOLDERSUB)
        e.markerDefine(QsciScintilla.MarkerSymbol.VerticalLine, QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL)
        e.markerDefine(QsciScintilla.MarkerSymbol.BottomLeftCorner, QsciScintilla.SC_MARKNUM_FOLDERTAIL)

        # Fold margin colours matching the editor background.
        e.setFoldMarginColors(mid, mid)

        # Enable the built-in fold interface so QScintilla tracks
        # fold headers automatically when we set fold levels.
        e.setFolding(QsciScintilla.FoldStyle.PlainFoldStyle)

    # ------------------------------------------------------------------
    # Public API — region registration
    # ------------------------------------------------------------------

    def register_fold_region(
        self,
        start_line: int,
        end_line: int,
        label: str = "...",
        kind: str = "block",
    ) -> FoldRegion:
        """Register a single collapsible code region.

        Args:
            start_line: First line of the block (0-indexed).
            end_line:   Last line of the block (0-indexed, inclusive).
            label:      Placeholder text when collapsed.
            kind:       Category tag (``"import"``, ``"class"``,
                        ``"function"``, ``"block"``).

        Returns:
            The newly created ``FoldRegion``.
        """
        region = FoldRegion(
            start_line=start_line,
            end_line=end_line,
            label=label,
            kind=kind,
        )
        self._regions.append(region)
        return region

    def set_fold_regions(self, regions: List[FoldRegion]) -> None:
        """Bulk-replace all fold regions and re-apply fold levels.

        Language plugins should call this once after parsing the
        buffer (e.g. on file load or after a debounced edit).

        Args:
            regions: Complete list of ``FoldRegion`` objects.
        """
        self._regions = list(regions)
        self._apply_fold_levels()

    def clear_fold_regions(self) -> None:
        """Remove all fold regions and reset the margin."""
        self._regions.clear()
        self._apply_fold_levels()

    def get_fold_regions(self) -> List[FoldRegion]:
        """Return the current list of fold regions (read-only copy)."""
        return list(self._regions)

    def get_region_at_line(self, line: int) -> Optional[FoldRegion]:
        """Return the ``FoldRegion`` that starts on *line*, or ``None``."""
        for r in self._regions:
            if r.start_line == line:
                return r
        return None

    # ------------------------------------------------------------------
    # Fold level application
    # ------------------------------------------------------------------

    def _apply_fold_levels(self) -> None:
        """Translate the ``_regions`` list into QScintilla fold levels.

        Each line in a foldable block gets ``SC_FOLDLEVELHEADERFLAG``
        on its start line and ``SC_FOLDLEVELWHITEFLAG`` or
        ``SC_FOLDLEVELBOXHEADERFLAG`` as appropriate.

        This method is the bridge between the abstract ``FoldRegion``
        model and QScintilla's C++ fold tree.
        """
        e = self._editor
        total_lines = e.lines()
        if total_lines == 0:
            return

        e.SendScintilla(QsciScintilla.SCI_SETFOLDFLAGS, 0)

        # Reset all lines to base fold level.
        for ln in range(total_lines):
            e.SendScintilla(
                QsciScintilla.SCI_SETFOLDLEVEL, ln, 0
            )

        for region in self._regions:
            s = max(0, region.start_line)
            end = min(total_lines - 1, region.end_line)

            if s >= total_lines or end < s:
                continue

            # Mark the header line (start of foldable block).
            header_level = 0 | QsciScintilla.SC_FOLDLEVELHEADERFLAG
            e.SendScintilla(QsciScintilla.SCI_SETFOLDLEVEL, s, header_level)

            # Mark inner lines with increased indent level.
            for ln in range(s + 1, end + 1):
                e.SendScintilla(
                    QsciScintilla.SCI_SETFOLDLEVEL, ln, 1
                )

            # Mark the line after the block returns to base level.
            if end + 1 < total_lines:
                e.SendScintilla(
                    QsciScintilla.SCI_SETFOLDLEVEL, end + 1, 0
                )

    # ------------------------------------------------------------------
    # Collapse / expand helpers
    # ------------------------------------------------------------------

    def collapse_region(self, region: FoldRegion) -> None:
        """Collapse a specific fold region by sending a fold toggle."""
        if region.folded:
            return
        self._editor.SendScintilla(
            QsciScintilla.SCI_TOGGLEFOLD, region.start_line
        )
        region.folded = True

    def expand_region(self, region: FoldRegion) -> None:
        """Expand a previously collapsed fold region."""
        if not region.folded:
            return
        self._editor.SendScintilla(
            QsciScintilla.SCI_TOGGLEFOLD, region.start_line
        )
        region.folded = False

    def collapse_all(self) -> None:
        """Collapse all registered fold regions."""
        for region in self._regions:
            self.collapse_region(region)

    def expand_all(self) -> None:
        """Expand all registered fold regions."""
        for region in self._regions:
            self.expand_region(region)

    def collapse_kind(self, kind: str) -> None:
        """Collapse all regions matching *kind* (e.g. ``"import"``)."""
        for region in self._regions:
            if region.kind == kind:
                self.collapse_region(region)

    def expand_kind(self, kind: str) -> None:
        """Expand all regions matching *kind*."""
        for region in self._regions:
            if region.kind == kind:
                self.expand_region(region)


class EditorAPI:
    """Facade that wraps a ``CodeEditor`` instance and exposes every
    editor operation through clean Python methods.

    The rest of the IDE depends **only** on this public interface.

    Lifetime: one ``EditorAPI`` instance per open editor.  The wrapper
    is lightweight and carries no state beyond the ``_editor`` reference.
    """

    def __init__(self, editor: QsciScintilla) -> None:
        if editor is None:
            raise ValueError("EditorAPI requires a non-None editor instance")
        self._editor = editor

    @property
    def editor(self) -> QsciScintilla:
        """Return the underlying ``QsciScintilla`` widget (escape hatch)."""
        return self._editor

    # ------------------------------------------------------------------
    # Clipboard
    # ------------------------------------------------------------------

    def cut(self) -> None:
        """Cut the current selection to the clipboard."""
        if self._editor.hasSelectedText():
            self._editor.cut()

    def copy(self) -> None:
        """Copy the current selection to the clipboard."""
        if self._editor.hasSelectedText():
            self._editor.copy()

    def paste(self) -> None:
        """Paste from the clipboard at the current cursor position."""
        self._editor.paste()

    def delete(self) -> None:
        """Delete the current selection."""
        if self._editor.hasSelectedText():
            self._editor.removeSelectedText()

    def duplicate_line(self) -> None:
        """Duplicate the line containing the cursor."""
        line, _ = self._editor.getCursorPosition()
        text = self._editor.text(line)
        self._editor.insertAt(f"\n{text}", line + 1, 0)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select_all(self) -> None:
        """Select all text in the editor."""
        self._editor.selectAll()

    def select_line(self) -> None:
        """Select the entire line at the cursor."""
        line = self._editor.getCursorPosition()[0]
        line_text = self._editor.text(line)
        self._editor.setSelection(line, 0, line, len(line_text))

    def expand_selection(self) -> None:
        """Expand the selection to the surrounding word boundaries."""
        line, col = self._editor.getCursorPosition()
        line_text = self._editor.text(line)
        start = line_text.rfind(" ", 0, col) + 1
        end = line_text.find(" ", col)
        if end == -1:
            end = len(line_text)
        self._editor.setSelection(line, start, line, end)

    # ------------------------------------------------------------------
    # Cursor movement
    # ------------------------------------------------------------------

    def move_up(self) -> None:
        """Move the cursor one line up, preserving column."""
        line, col = self._editor.getCursorPosition()
        if line > 0:
            self._editor.setCursorPosition(line - 1, col)

    def move_down(self) -> None:
        """Move the cursor one line down, preserving column."""
        line, col = self._editor.getCursorPosition()
        if line < self._editor.lines() - 1:
            self._editor.setCursorPosition(line + 1, col)

    def move_left(self) -> None:
        """Move the cursor one character left, wrapping to the previous line."""
        line, col = self._editor.getCursorPosition()
        if col > 0:
            self._editor.setCursorPosition(line, col - 1)
        elif line > 0:
            prev_text = self._editor.text(line - 1).rstrip("\r\n")
            self._editor.setCursorPosition(line - 1, len(prev_text))

    def move_right(self) -> None:
        """Move the cursor one character right, wrapping to the next line."""
        line, col = self._editor.getCursorPosition()
        line_text = self._editor.text(line)
        if col < len(line_text):
            self._editor.setCursorPosition(line, col + 1)
        elif line < self._editor.lines() - 1:
            self._editor.setCursorPosition(line + 1, 0)

    def goto_line(self, line: int) -> None:
        """Jump to *line* (0-indexed), clamped to valid range.

        Args:
            line: Target line number (0-indexed).
        """
        if not isinstance(line, int):
            logger.warning("goto_line: expected int, got %s", type(line).__name__)
            return
        clamped = max(0, min(line, self._editor.lines() - 1))
        self._editor.setCursorPosition(clamped, 0)
        self._editor.ensureLineVisible(clamped)

    def goto_position(self, line: int, col: int) -> None:
        """Jump to *line*/*col* (both 0-indexed), clamped to valid range.

        Args:
            line: Target line number (0-indexed).
            col: Target column number (0-indexed).
        """
        if not isinstance(line, int) or not isinstance(col, int):
            logger.warning(
                "goto_position: expected (int, int), got (%s, %s)",
                type(line).__name__,
                type(col).__name__,
            )
            return
        clamped_line = max(0, min(line, self._editor.lines() - 1))
        line_text = self._editor.text(clamped_line)
        clamped_col = max(0, min(col, len(line_text)))
        self._editor.setCursorPosition(clamped_line, clamped_col)
        self._editor.ensureLineVisible(clamped_line)

    # ------------------------------------------------------------------
    # Editing
    # ------------------------------------------------------------------

    def undo(self) -> None:
        """Undo the last editing action, if available."""
        if self._editor.isUndoAvailable():
            self._editor.undo()

    def redo(self) -> None:
        """Redo the last undone action, if available."""
        if self._editor.isRedoAvailable():
            self._editor.redo()

    def indent(self) -> None:
        """Indent the selection or insert a tab of spaces."""
        if self._editor.hasSelectedText():
            self._editor.SendScintilla(QsciScintilla.SCI_TAB)
        else:
            line, col = self._editor.getCursorPosition()
            self._editor.insert("    ")
            self._editor.setCursorPosition(line, col + 4)

    def unindent(self) -> None:
        """Unindent the current selection."""
        if self._editor.hasSelectedText():
            self._editor.SendScintilla(QsciScintilla.SCI_BACKTAB)

    def comment(self) -> None:
        """Comment out every selected line with a ``#`` prefix."""
        if not self._editor.hasSelectedText():
            return
        self._editor.beginUndoAction()
        line_from, _, line_to, _ = self._editor.getSelection()
        for i in range(line_from, line_to + 1):
            self._editor.insertAt("# ", i, 0)
        self._editor.endUndoAction()

    def uncomment(self) -> None:
        """Remove a leading ``# `` from every selected line."""
        if not self._editor.hasSelectedText():
            return
        self._editor.beginUndoAction()
        line_from, _, line_to, _ = self._editor.getSelection()
        for i in range(line_from, line_to + 1):
            text = self._editor.text(i)
            if text.lstrip().startswith("# "):
                indent = len(text) - len(text.lstrip())
                self._editor.setSelection(i, indent, i, indent + 2)
                self._editor.removeSelectedText()
        self._editor.endUndoAction()

    def uppercase(self) -> None:
        """Convert the selection to upper case."""
        if self._editor.hasSelectedText():
            text = self._editor.selectedText()
            self._editor.replaceSelectedText(text.upper())

    def lowercase(self) -> None:
        """Convert the selection to lower case."""
        if self._editor.hasSelectedText():
            text = self._editor.selectedText()
            self._editor.replaceSelectedText(text.lower())

    # ------------------------------------------------------------------
    # File
    # ------------------------------------------------------------------

    def load_file(self, file_path: str) -> None:
        """Load a file into the editor.

        Args:
            file_path: Absolute path to the file.

        Raises:
            ``FileNotFoundError``, ``PermissionError``, or
            ``UnicodeDecodeError`` on failure.
        """
        if not file_path or not isinstance(file_path, str):
            raise ValueError("load_file requires a non-empty file path string")
        self._editor.load_from_file(file_path)

    def save(self) -> bool:
        """Save the editor buffer to its current file path.

        Returns:
            ``True`` on success, ``False`` on failure or cancellation.
        """
        return self._editor.save()

    def save_as(self) -> bool:
        """Prompt for a new path and save the editor buffer.

        Returns:
            ``True`` on success, ``False`` on failure or cancellation.
        """
        return self._editor.save_as()

    def reload(self) -> None:
        """Re-read the file from disk, discarding unsaved changes.

        Raises:
            Same exceptions as ``load_from_file``.
        """
        if self._editor.current_file_path:
            self._editor.load_from_file(self._editor.current_file_path)

    # ------------------------------------------------------------------
    # Search & Replace
    # ------------------------------------------------------------------

    def find(self, text: str) -> bool:
        """Find the first occurrence of *text* from the current position.

        Args:
            text: The string to search for.

        Returns:
            ``True`` if a match was found.
        """
        if not text:
            return False
        return self._editor.findFirst(text, False, False, False, False)

    def replace(self, find_text: str, replace_text: str) -> bool:
        """Find and replace the first occurrence of *find_text*.

        Args:
            find_text: The string to search for.
            replace_text: The replacement string.

        Returns:
            ``True`` if a match was found and replaced.
        """
        if not find_text:
            return False
        found = self._editor.findFirst(find_text, False, False, False, False)
        if found:
            self._editor.replace(replace_text)
            return True
        return False

    def replace_all(self, find_text: str, replace_text: str) -> int:
        """Replace every occurrence of *find_text* with *replace_text*.

        Guards against infinite loops when the replacement text contains
        the search text by tracking cursor advancement.

        Args:
            find_text: The string to search for.
            replace_text: The replacement string.

        Returns:
            The number of replacements made.
        """
        if not find_text:
            return 0
        if find_text == replace_text:
            return 0

        count = 0
        safety_limit = max(self._editor.lines() * 2000, 50000)
        self._editor.setCursorPosition(0, 0)

        while count < safety_limit:
            if not self._editor.findFirst(find_text, False, False, False, False):
                break
            # Read the match position before replacing so we can detect
            # stalls where the cursor does not advance.
            match_pos = self._editor.SendScintilla(
                QsciScintilla.SCI_GETCURRENTPOS
            )
            self._editor.replace(replace_text)
            count += 1
            after_pos = self._editor.SendScintilla(
                QsciScintilla.SCI_GETCURRENTPOS
            )
            if after_pos <= match_pos:
                # Cursor did not advance — force it forward one character
                # to break a potential infinite loop.
                self._editor.SendScintilla(QsciScintilla.SCI_CHARRIGHT)

        if count >= safety_limit:
            logger.warning(
                "replace_all: safety limit (%d) reached for find_text=%r",
                safety_limit,
                find_text,
            )
        return count

    def show_find_widget(self) -> None:
        """Placeholder for future find-widget integration."""
        pass

    # ------------------------------------------------------------------
    # View
    # ------------------------------------------------------------------

    def zoom_in(self) -> None:
        """Increase the editor zoom level."""
        self._editor.zoomIn()

    def zoom_out(self) -> None:
        """Decrease the editor zoom level."""
        self._editor.zoomOut()

    def reset_zoom(self) -> None:
        """Reset the editor zoom to the default level."""
        self._editor.zoomTo(0)

    # ------------------------------------------------------------------
    # Text access
    # ------------------------------------------------------------------

    def get_text(self) -> str:
        """Return the full text buffer as a string."""
        return self._editor.text()

    def set_text(self, text: str) -> None:
        """Replace the entire text buffer.

        Args:
            text: The new text content.
        """
        self._editor.setText(text)

    def append_text(self, text: str) -> None:
        """Append *text* to the end of the buffer."""
        self._editor.append(text)

    def insert_text(self, text: str) -> None:
        """Insert *text* at the current cursor position."""
        line, col = self._editor.getCursorPosition()
        self._editor.insertAt(text, line, col)

    def clear(self) -> None:
        """Clear the entire text buffer."""
        self._editor.clear()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def is_dirty(self) -> bool:
        """Return ``True`` if the buffer has been modified since last save."""
        return self._editor.isModified()

    def set_dirty(self, dirty: bool) -> None:
        """Manually set the dirty (modified) flag.

        Args:
            dirty: ``True`` to mark the editor as modified.
        """
        self._editor.setModified(dirty)

    def file_path(self) -> Optional[str]:
        """Return the canonical file path, or ``None`` for untitled buffers."""
        return getattr(self._editor, "current_file_path", None)

    def set_file_path(self, path: str) -> None:
        """Update the canonical file path.

        Args:
            path: New file path string.
        """
        self._editor.current_file_path = path

    # ------------------------------------------------------------------
    # Editor Properties (read-only introspection)
    # ------------------------------------------------------------------

    def eol_mode(self) -> int:
        """Return the end-of-line mode constant."""
        return self._editor.eolMode()

    def indentation_width(self) -> int:
        """Return the indentation width in spaces."""
        return self._editor.indentationWidth()

    def uses_tabs(self) -> bool:
        """Return ``True`` when tabs are used for indentation."""
        return self._editor.indentationsUseTabs()

    def lines(self) -> int:
        """Return the total number of lines in the buffer."""
        return self._editor.lines()

    # ------------------------------------------------------------------
    # Code Tools
    # ------------------------------------------------------------------

    def format_code(self) -> None:
        """Delegate formatting to the active language provider."""
        if hasattr(self._editor, "format_current_file"):
            self._editor.format_current_file()

    # ------------------------------------------------------------------
    # Folding
    # ------------------------------------------------------------------

    def fold_region(
        self,
        start_line: int,
        end_line: int,
        label: str = "...",
        kind: str = "block",
    ) -> Optional[FoldRegion]:
        """Register a single fold region on this editor.

        Delegates to :meth:`FoldManager.register_fold_region`.
        Returns the created ``FoldRegion``, or ``None`` if the
        editor has no ``FoldManager`` attached.
        """
        fm = getattr(self._editor, "_fold_manager", None)
        if fm is None:
            logger.debug("fold_region: no FoldManager on editor")
            return None
        return fm.register_fold_region(start_line, end_line, label, kind)

    def apply_folds(self, regions: List[FoldRegion]) -> None:
        """Bulk-apply fold regions and update the margin.

        Language plugins call this after parsing the buffer.
        """
        fm = getattr(self._editor, "_fold_manager", None)
        if fm is not None:
            fm.set_fold_regions(regions)

    def collapse_all(self) -> None:
        """Collapse every registered fold region."""
        fm = getattr(self._editor, "_fold_manager", None)
        if fm is not None:
            fm.collapse_all()

    def expand_all(self) -> None:
        """Expand every registered fold region."""
        fm = getattr(self._editor, "_fold_manager", None)
        if fm is not None:
            fm.expand_all()

    def collapse_imports(self) -> None:
        """Collapse all ``"import"`` kind fold regions."""
        fm = getattr(self._editor, "_fold_manager", None)
        if fm is not None:
            fm.collapse_kind("import")

    def collapse_classes(self) -> None:
        """Collapse all ``"class"`` kind fold regions."""
        fm = getattr(self._editor, "_fold_manager", None)
        if fm is not None:
            fm.collapse_kind("class")

    def collapse_functions(self) -> None:
        """Collapse all ``"function"`` kind fold regions."""
        fm = getattr(self._editor, "_fold_manager", None)
        if fm is not None:
            fm.collapse_kind("function")
