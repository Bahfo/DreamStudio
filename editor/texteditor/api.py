"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved

Public API for the DreamStudio text editor.

This module exposes a clean, minimal interface for all editor
operations.  The rest of the IDE should never manipulate the
editor widget directly.

``EditorAPI`` is a thin, stateless facade that wraps a ``CodeEditor``
instance and validates every operation before forwarding it.
"""

import logging
from typing import Optional

from PyQt6.Qsci import QsciScintilla

logger = logging.getLogger(__name__)


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
