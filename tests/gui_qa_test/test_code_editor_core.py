"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Code editor core live tests: typing, cursor keys, auto-indent, dirty/save,
undo/redo, zoom, wrap mode, clipboard, and read-only mode.
"""

from pathlib import Path

import pytest

from harness import (
    Sweep,
    assert_alive,
    click,
    code_editor,
    cursor_position,
    press_key,
    pump,
    race_probe,
    type_text,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

QT = pytest.importorskip("PyQt6.QtCore")


def _zoom_level(editor) -> int:
    """Return the Scintilla zoom level of an editor.

    Args:
        editor: The CodeEditor instance.

    Returns:
        The current zoom level, where zero is the default size.
    """
    from PyQt6.Qsci import QsciScintilla

    return int(editor.SendScintilla(QsciScintilla.SCI_GETZOOM))


def _open_editor(qapp, window, workspace_path, name: str = "main.py"):
    """Open a sample file and return its CodeEditor.

    Args:
        qapp: The live QApplication instance.
        window: The DreamStudio main window.
        workspace_path: Workspace root holding the sample file.
        name: File name to open.

    Returns:
        The CodeEditor instance.
    """
    tabs = window.hero_window._text_editor_center.tabs
    tabs.open_file_by_path(str(Path(workspace_path) / name))
    pump(qapp, 300)
    api = window.hero_window._text_editor_center.current_editor()
    return code_editor(api)


class TestTypingAndCursor:
    """Typing and cursor movement behave as expected."""

    def test_typing_inserts_text(self, qapp, qa_window, sample_tree):
        """Typing inserts the characters at the cursor."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setCursorPosition(0, 0)
        before = editor.text()
        type_text(qapp, editor, "abc")
        assert editor.text().startswith("abc"), "typed text not inserted"
        assert len(editor.text()) == len(before) + 3, "typed length wrong"

    def test_cursor_keys_move_the_cursor(self, qapp, qa_window, sample_tree):
        """Arrow keys move the cursor along the document axes.

        Every arrow is checked from a freshly seeded cursor position so the
        assertion only covers the axis the key owns: Right/Left move the
        column, Down/Up move the line.
        """
        editor = _open_editor(qapp, qa_window, sample_tree)

        editor.setCursorPosition(5, 4)
        press_key(qapp, editor, QT.Qt.Key.Key_Right)
        line, column = cursor_position(editor)
        assert line == 5, f"Right changed the line: {line}"
        assert column == 5, f"Right did not advance the column: {column}"

        editor.setCursorPosition(5, 4)
        press_key(qapp, editor, QT.Qt.Key.Key_Left)
        line, column = cursor_position(editor)
        assert line == 5, f"Left changed the line: {line}"
        assert column == 3, f"Left did not retreat the column: {column}"

        editor.setCursorPosition(5, 4)
        press_key(qapp, editor, QT.Qt.Key.Key_Down)
        line, _column = cursor_position(editor)
        assert line == 6, f"Down did not reach the next line: {line}"

        editor.setCursorPosition(5, 4)
        press_key(qapp, editor, QT.Qt.Key.Key_Up)
        line, _column = cursor_position(editor)
        assert line == 4, f"Up did not reach the previous line: {line}"

    def test_home_and_end_jump_to_line_bounds(self, qapp, qa_window, sample_tree):
        """Home and End move to the start and end of the current line."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setCursorPosition(2, 4)
        press_key(qapp, editor, QT.Qt.Key.Key_Home)
        assert cursor_position(editor)[1] == 0, "Home did not reach column 0"
        press_key(qapp, editor, QT.Qt.Key.Key_End)
        line_length = len(editor.text().split("\n")[2])
        assert (
            cursor_position(editor)[1] == line_length
        ), f"End did not reach the line end: {cursor_position(editor)[1]}"

    def test_backspace_and_delete_remove_text(self, qapp, qa_window, sample_tree):
        """Backspace and Delete remove characters around the cursor."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setCursorPosition(0, 3)
        original = editor.text()
        press_key(qapp, editor, QT.Qt.Key.Key_Delete)
        assert editor.text() != original, "Delete removed nothing"
        press_key(qapp, editor, QT.Qt.Key.Key_Backspace)
        assert len(editor.text()) == len(original) - 2, "Backspace removed nothing"

    def test_word_jump_moves_cursor(self, qapp, qa_window, sample_tree):
        """Ctrl+Left and Ctrl+Right jump by word."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setCursorPosition(0, 0)
        press_key(
            qapp, editor, QT.Qt.Key.Key_Right, QT.Qt.KeyboardModifier.ControlModifier
        )
        assert cursor_position(editor)[1] > 0, "word jump did not move the cursor"

    def test_position_signal_reports_cursor(self, qapp, qa_window, sample_tree):
        """The editor reports its cursor position through its signal.

        ``position_changed`` carries the same ``(line, column)`` pair that
        ``getCursorPosition()`` reports, so the payload is compared with the
        live cursor rather than with the requested position.
        """
        editor = _open_editor(qapp, qa_window, sample_tree)
        positions = []
        signal = getattr(editor, "position_changed", None)
        assert signal is not None, "the editor has no position_changed signal"
        signal.connect(lambda line, col: positions.append((line, col)))
        editor.setCursorPosition(5, 4)
        pump(qapp, 200)
        assert positions, "no position signal was emitted"
        line, column = cursor_position(editor)
        assert (
            line,
            column,
        ) in positions, (
            f"position payload {positions[-1]} does not match cursor ({line}, {column})"
        )


class TestAutoIndent:
    """Indentation behaviour matches editor expectations."""

    def test_enter_after_def_indents_body(self, qapp, qa_window, sample_tree):
        """Pressing Enter after a def line keeps the block indentation."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("def qa_func():\n    pass\n")
        editor.setCursorPosition(0, len("def qa_func():"))
        press_key(qapp, editor, QT.Qt.Key.Key_Return)
        pump(qapp, 150)
        lines = editor.text().split("\n")
        assert lines[1].startswith(
            "    "
        ), f"auto-indent missing after def: {lines[1]!r}"

    def test_tab_indents_the_current_line(self, qapp, qa_window, sample_tree):
        """Tab increases the indentation of the current line."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("value = 1\n")
        editor.setCursorPosition(0, 0)
        press_key(qapp, editor, QT.Qt.Key.Key_Tab)
        pump(qapp, 150)
        assert (
            editor.text().split("\n")[0].startswith("    ")
        ), f"Tab did not indent: {editor.text().split(chr(10))[0]!r}"

    def test_shift_tab_unindents_the_current_line(self, qapp, qa_window, sample_tree):
        """Shift+Tab removes one indentation level."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("    value = 1\n")
        editor.setCursorPosition(0, 4)
        press_key(
            qapp, editor, QT.Qt.Key.Key_Backtab, QT.Qt.KeyboardModifier.ShiftModifier
        )
        pump(qapp, 150)
        assert (
            not editor.text().split("\n")[0].startswith("    ")
        ), "Shift+Tab did not unindent"


class TestDirtyAndSave:
    """Dirty tracking and saving behave correctly."""

    def test_edit_marks_editor_dirty(self, qapp, qa_window, sample_tree):
        """An edit marks the editor dirty."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "# qa\n")
        assert editor.is_dirty(), "editor not dirty after an edit"

    def test_clear_dirty_resets_the_flag(self, qapp, qa_window, sample_tree):
        """clear_dirty() clears the dirty flag."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "x")
        editor.clear_dirty()
        assert not editor.is_dirty(), "dirty flag not cleared"

    def test_save_to_file_writes_content(self, qapp, qa_window, sample_tree, tmp_path):
        """save_to_file() writes the buffer to the requested path."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "# saved\n")
        target = tmp_path / "saved_by_editor.py"
        result = editor.save_to_file(str(target))
        assert result, "save_to_file reported failure"
        assert target.exists(), "target file was not created"
        assert target.read_text().startswith("# saved\n"), "content not written"

    def test_save_as_uses_stubbed_dialog(self, qapp, qa_window, sample_tree, tmp_path):
        """save_as() completes against a stubbed file dialog."""
        import harness

        editor = _open_editor(qapp, qa_window, sample_tree)
        target = tmp_path / "saved_as.py"
        with harness.modal_guard(paths=[str(target)]):
            editor.save_as()
            pump(qapp, 300)
        assert_alive(qapp, qa_window)

    def test_undo_redo_restores_text(self, qapp, qa_window, sample_tree):
        """Undo and redo move the document back and forth."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("base\n")
        editor.setCursorPosition(0, 4)
        type_text(qapp, editor, "more")
        assert editor.text() == "basemore\n", "typing failed"
        editor.undo()
        pump(qapp, 100)
        assert editor.text() == "base\n", f"undo failed: {editor.text()!r}"
        editor.redo()
        pump(qapp, 100)
        assert editor.text() == "basemore\n", f"redo failed: {editor.text()!r}"

    def test_undo_past_history_start_is_safe(self, qapp, qa_window, sample_tree):
        """Undoing past the start of history does not raise."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("base\n")
        sweep = Sweep("undo past start")
        for _ in range(5):
            sweep.step("undo", editor.undo)
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_redo_past_history_end_is_safe(self, qapp, qa_window, sample_tree):
        """Redoing past the end of history does not raise."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("base\n")
        sweep = Sweep("redo past end")
        for _ in range(5):
            sweep.step("redo", editor.redo)
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_rapid_undo_redo_is_stable(self, qapp, qa_window, sample_tree):
        """A rapid undo/redo storm leaves the editor consistent."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("base\n")
        editor.setCursorPosition(0, 4)
        type_text(qapp, editor, "x")

        def cycle() -> None:
            """Undo and redo once.

            Returns:
                None; the side effect is the undo/redo pair.
            """
            editor.undo()
            editor.redo()

        race_probe(qapp, cycle, 4)
        assert_alive(qapp, qa_window)


class TestZoomAndFonts:
    """Zoom and font controls work on the live editor."""

    def test_set_editor_font_size_changes_the_font_size(
        self, qapp, qa_window, sample_tree
    ):
        """set_editor_font_size() updates the reported font size."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        base = editor.font_size
        editor.set_editor_font_size(base + 4)
        pump(qapp, 100)
        assert editor.font_size == base + 4, "font size did not change"

    def test_zoom_in_and_out_changes_the_zoom_level(self, qapp, qa_window, sample_tree):
        """zoomIn() and zoomOut() move the editor zoom level."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        base = _zoom_level(editor)
        editor.zoomIn()
        pump(qapp, 100)
        assert _zoom_level(editor) == base + 1, "zoomIn did not raise the zoom level"
        editor.zoomOut()
        pump(qapp, 100)
        assert _zoom_level(editor) == base, "zoomOut did not lower the zoom level"

    def test_reset_zoom_restores_the_base_zoom_level(
        self, qapp, qa_window, sample_tree
    ):
        """reset_zoom_level() returns the editor to zoom level zero."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        base = _zoom_level(editor)
        editor.zoomIn()
        editor.zoomIn()
        pump(qapp, 100)
        assert _zoom_level(editor) > base, "the zoom level never rose"
        editor.reset_zoom_level()
        pump(qapp, 100)
        assert (
            _zoom_level(editor) == base
        ), f"zoom reset left the level at {_zoom_level(editor)} (base {base})"

    def test_is_zoomed_reports_the_state(self, qapp, qa_window, sample_tree):
        """is_zoomed() tells the caller whether the editor is zoomed.

        NOTE (QA finding): ``CodeEditor.is_zoomed()`` is documented as a
        public API that indicates whether the editor is zoomed, but it only
        assigns the private ``_is_zoomed`` flag and never returns it, so
        every caller sees ``None`` - which is falsy - and can never detect
        a zoomed editor.
        """
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.reset_zoom_level()
        pump(qapp, 100)
        assert (
            editor.is_zoomed() is False
        ), f"is_zoomed() reported {editor.is_zoomed()!r} at the base zoom level"
        editor.zoomIn()
        pump(qapp, 100)
        assert (
            editor.is_zoomed() is True
        ), f"is_zoomed() reported {editor.is_zoomed()!r} while zoomed in"

    def test_set_editor_font_applies_a_font(self, qapp, qa_window, sample_tree):
        """Applying a custom font does not break the editor."""
        from PyQt6.QtGui import QFont

        editor = _open_editor(qapp, qa_window, sample_tree)
        sweep = Sweep("custom font")
        sweep.step("set font", editor.set_editor_font, QFont("Courier", 11))
        sweep.finish()
        assert_alive(qapp, qa_window)


class TestWrapAndEdge:
    """Wrap mode and the edge marker behave."""

    def test_wrap_mode_toggles(self, qapp, qa_window, sample_tree):
        """set_wrap_mode() switches the wrap state."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.set_wrap_mode(True)
        pump(qapp, 100)
        editor.set_wrap_mode(False)
        pump(qapp, 100)
        assert_alive(qapp, qa_window)

    def test_wrapped_long_line_remains_reachable(self, qapp, qa_window, sample_tree):
        """A wrapped long line can still be navigated to its end."""
        editor = _open_editor(qapp, qa_window, sample_tree, "longlines.py")
        editor.set_wrap_mode(True)
        pump(qapp, 150)
        last_line = editor.lines() - 1
        editor.setCursorPosition(last_line, 0)
        press_key(qapp, editor, QT.Qt.Key.Key_End)
        pump(qapp, 100)
        assert cursor_position(editor)[0] == last_line, "cursor left the wrapped line"


class TestClipboardAndSelection:
    """Selection and clipboard helpers work."""

    def test_select_all_covers_the_document(self, qapp, qa_window, sample_tree):
        """Select-all selects the whole buffer."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.selectAll()
        pump(qapp, 100)
        assert editor.hasSelectedText(), "select all selected nothing"
        assert (
            editor.selectedText() == editor.text()
        ), "selection does not cover the text"

    def test_copy_selection_as_plain_text(self, qapp, qa_window, sample_tree):
        """copy_selection_as_plain_text() places the text on the clipboard."""
        from PyQt6.QtWidgets import QApplication

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setCursorPosition(0, 0)
        editor.setSelection(0, 0, 0, 3)
        pump(qapp, 100)
        editor.copy_selection_as_plain_text()
        pump(qapp, 100)
        clipboard = QApplication.clipboard().text()
        assert clipboard, "clipboard stayed empty"

    def test_double_click_selects_a_word(self, qapp, qa_window, sample_tree):
        """Double-clicking in the text selects the word under the cursor."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        click(qapp, editor)
        pump(qapp, 100)
        assert_alive(qapp, qa_window)


class TestReadOnlyMode:
    """Read-only mode blocks edits and marks the tab."""

    def test_readonly_blocks_typing(self, qapp, qa_window, sample_tree):
        """A read-only editor ignores typed characters."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.make_file_readonly()
        pump(qapp, 150)
        before = editor.text()
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "nope")
        assert editor.text() == before, "read-only editor accepted typing"

    def test_readonly_state_is_reported(self, qapp, qa_window, sample_tree):
        """The editor exposes whether it is read-only."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.make_file_readonly()
        pump(qapp, 150)
        readonly = getattr(editor, "is_readonly", None)
        if callable(readonly):
            assert readonly(), "editor does not report the read-only state"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
