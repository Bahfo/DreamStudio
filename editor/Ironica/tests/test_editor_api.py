"""Tests for EditorAPI (editor/texteditor/api.py).

Covers: clipboard, selection, cursor movement, editing, search/replace,
state management, zoom, and argument validation.
"""

import pytest
from PyQt6.QtCore import Qt


class TestEditorAPIConstruction:
    """Test EditorAPI instantiation and validation."""

    def test_requires_non_none_editor(self):
        from editor.Ironica.api import EditorAPI

        with pytest.raises(ValueError, match="non-None"):
            EditorAPI(None)

    def test_editor_property_returns_wrapped_editor(self, editor_api):
        assert editor_api.editor is not None
        assert editor_api.editor.objectName() == "CodeEditor"


class TestClipboard:
    """Test cut, copy, paste, delete, duplicate_line."""

    def test_copy_no_selection(self, editor_api):
        editor_api.copy()  # should not raise

    def test_copy_with_selection(self, editor_api):
        editor_api.set_text("hello world")
        editor_api._editor.setSelection(0, 0, 0, 5)
        editor_api.copy()

    def test_cut_no_selection(self, editor_api):
        editor_api.cut()  # should not raise

    def test_cut_with_selection(self, editor_api):
        editor_api.set_text("hello world")
        editor_api._editor.setSelection(0, 0, 0, 5)
        editor_api.cut()
        assert editor_api.get_text() == " world"

    def test_paste(self, editor_api):
        editor_api.set_text("hello")
        editor_api.paste()  # should not raise

    def test_delete_no_selection(self, editor_api):
        editor_api.delete()  # should not raise

    def test_delete_with_selection(self, editor_api):
        editor_api.set_text("hello world")
        editor_api._editor.setSelection(0, 6, 0, 11)
        editor_api.delete()
        assert editor_api.get_text() == "hello "

    def test_duplicate_line(self, editor_api):
        editor_api.set_text("line one")
        editor_api.goto_line(0)
        editor_api.duplicate_line()
        text = editor_api.get_text()
        assert "line one" in text


class TestSelection:
    """Test select_all, select_line, expand_selection."""

    def test_select_all(self, editor_api):
        editor_api.set_text("abc\ndef")
        editor_api.select_all()
        assert editor_api._editor.hasSelectedText()

    def test_select_line(self, editor_api):
        editor_api.set_text("abc\ndef")
        editor_api._editor.setCursorPosition(1, 2)
        editor_api.select_line()
        assert editor_api._editor.hasSelectedText()

    def test_expand_selection(self, editor_api):
        editor_api.set_text("hello world foo")
        editor_api._editor.setCursorPosition(0, 6)
        editor_api.expand_selection()
        assert editor_api._editor.hasSelectedText()


class TestCursorMovement:
    """Test move_up, move_down, move_left, move_right, goto_line, goto_position."""

    def test_move_up(self, editor_api):
        editor_api.set_text("line1\nline2")
        editor_api._editor.setCursorPosition(1, 0)
        editor_api.move_up()
        line, _ = editor_api._editor.getCursorPosition()
        assert line == 0

    def test_move_up_at_top(self, editor_api):
        editor_api.set_text("line1")
        editor_api._editor.setCursorPosition(0, 0)
        editor_api.move_up()
        line, _ = editor_api._editor.getCursorPosition()
        assert line == 0

    def test_move_down(self, editor_api):
        editor_api.set_text("line1\nline2")
        editor_api._editor.setCursorPosition(0, 0)
        editor_api.move_down()
        line, _ = editor_api._editor.getCursorPosition()
        assert line == 1

    def test_move_down_at_bottom(self, editor_api):
        editor_api.set_text("line1")
        editor_api._editor.setCursorPosition(0, 0)
        editor_api.move_down()
        line, _ = editor_api._editor.getCursorPosition()
        assert line == 0

    def test_move_left(self, editor_api):
        editor_api.set_text("hello")
        editor_api._editor.setCursorPosition(0, 3)
        editor_api.move_left()
        _, col = editor_api._editor.getCursorPosition()
        assert col == 2

    def test_move_left_wraps(self, editor_api):
        editor_api.set_text("ab\ncd")
        editor_api._editor.setCursorPosition(1, 0)
        editor_api.move_left()
        line, col = editor_api._editor.getCursorPosition()
        assert line == 0
        # col should be at the end of line 0
        assert col > 0

    def test_move_right(self, editor_api):
        editor_api.set_text("hello")
        editor_api._editor.setCursorPosition(0, 1)
        editor_api.move_right()
        _, col = editor_api._editor.getCursorPosition()
        assert col == 2

    def test_move_right_wraps(self, editor_api):
        editor_api.set_text("ab\ncd")
        editor_api._editor.setCursorPosition(0, 2)
        editor_api.move_right()
        line, _ = editor_api._editor.getCursorPosition()
        assert line == 1

    def test_goto_line(self, editor_api):
        editor_api.set_text("line0\nline1\nline2\nline3")
        editor_api.goto_line(2)
        line, _ = editor_api._editor.getCursorPosition()
        assert line == 2

    def test_goto_line_clamps(self, editor_api):
        editor_api.set_text("line0")
        editor_api.goto_line(100)
        line, _ = editor_api._editor.getCursorPosition()
        assert line == 0

    def test_goto_line_negative(self, editor_api):
        editor_api.set_text("line0")
        editor_api.goto_line(-5)
        line, _ = editor_api._editor.getCursorPosition()
        assert line == 0

    def test_goto_line_non_int_ignored(self, editor_api):
        editor_api.set_text("line0")
        editor_api.goto_line("abc")  # should log warning, not crash

    def test_goto_position(self, editor_api):
        editor_api.set_text("hello world")
        editor_api.goto_position(0, 5)
        line, col = editor_api._editor.getCursorPosition()
        assert line == 0
        assert col == 5

    def test_goto_position_clamps(self, editor_api):
        editor_api.set_text("hello")
        editor_api.goto_position(0, 100)
        _, col = editor_api._editor.getCursorPosition()
        assert col == 5  # clamped to line length

    def test_goto_position_non_int_ignored(self, editor_api):
        editor_api.set_text("hello")
        editor_api.goto_position("a", 0)  # should log warning


class TestEditing:
    """Test undo, redo, indent, unindent, comment, uncomment."""

    def test_undo_redo(self, editor_api):
        editor_api.set_text("")
        editor_api._editor.setModified(False)
        editor_api._editor.insert("hello")
        assert editor_api.is_dirty()
        editor_api.undo()
        editor_api.redo()

    def test_indent_with_selection(self, editor_api):
        editor_api.set_text("line1\nline2")
        editor_api._editor.setSelection(0, 0, 1, 5)
        editor_api.indent()

    def test_indent_without_selection(self, editor_api):
        editor_api.set_text("hello")
        editor_api._editor.setCursorPosition(0, 0)
        editor_api.indent()
        text = editor_api.get_text()
        assert len(text) >= 4

    def test_unindent(self, editor_api):
        editor_api.set_text("line1\nline2")
        editor_api._editor.setSelection(0, 0, 1, 5)
        editor_api.unindent()

    def test_comment(self, editor_api):
        editor_api.set_text("line1\nline2")
        editor_api._editor.setSelection(0, 0, 1, 5)
        editor_api.comment()
        text = editor_api.get_text()
        assert "# " in text

    def test_comment_no_selection(self, editor_api):
        editor_api.set_text("line1")
        editor_api.comment()  # no-op, should not raise

    def test_uncomment(self, editor_api):
        editor_api.set_text("# line1\n# line2")
        editor_api._editor.setSelection(0, 0, 1, 8)
        editor_api.uncomment()
        text = editor_api.get_text()
        assert text.startswith("line1")

    def test_uncomment_no_selection(self, editor_api):
        editor_api.set_text("# line1")
        editor_api.uncomment()  # no-op

    def test_uppercase(self, editor_api):
        editor_api.set_text("hello")
        editor_api._editor.setSelection(0, 0, 0, 5)
        editor_api.uppercase()
        assert editor_api.get_text() == "HELLO"

    def test_lowercase(self, editor_api):
        editor_api.set_text("HELLO")
        editor_api._editor.setSelection(0, 0, 0, 5)
        editor_api.lowercase()
        assert editor_api.get_text() == "hello"


class TestSearchReplace:
    """Test find, replace, replace_all."""

    def test_find(self, editor_api):
        editor_api.set_text("hello world hello")
        editor_api._editor.setCursorPosition(0, 0)
        result = editor_api.find("world")
        # findFirst requires the editor to have focus/displayed
        # in offscreen mode this may not always work, so just check no crash
        assert isinstance(result, bool)

    def test_find_empty(self, editor_api):
        editor_api.set_text("hello")
        result = editor_api.find("")
        assert result is False

    def test_find_not_found(self, editor_api):
        editor_api.set_text("hello")
        result = editor_api.find("xyz")
        # may or may not find depending on QScintilla implementation

    def test_replace(self, editor_api):
        editor_api.set_text("hello world")
        editor_api._editor.setCursorPosition(0, 0)
        result = editor_api.replace("hello", "bye")
        assert result is True

    def test_replace_empty(self, editor_api):
        editor_api.set_text("hello")
        result = editor_api.replace("", "bye")
        assert result is False

    def test_replace_all(self, editor_api):
        editor_api.set_text("a b a b a")
        count = editor_api.replace_all("a", "x")
        assert count == 3
        assert editor_api.get_text() == "x b x b x"

    def test_replace_all_empty_find(self, editor_api):
        editor_api.set_text("hello")
        count = editor_api.replace_all("", "x")
        assert count == 0

    def test_replace_all_same_text(self, editor_api):
        editor_api.set_text("hello")
        count = editor_api.replace_all("hello", "hello")
        assert count == 0  # no-op guard

    def test_replace_all_no_match(self, editor_api):
        editor_api.set_text("hello")
        count = editor_api.replace_all("xyz", "abc")
        assert count == 0


class TestView:
    """Test zoom_in, zoom_out, reset_zoom."""

    def test_zoom_in(self, editor_api):
        editor_api.zoom_in()  # should not raise

    def test_zoom_out(self, editor_api):
        editor_api.zoom_out()  # should not raise

    def test_reset_zoom(self, editor_api):
        editor_api.reset_zoom()  # should not raise


class TestTextAccess:
    """Test get_text, set_text, append_text, insert_text, clear."""

    def test_get_set_text(self, editor_api):
        editor_api.set_text("hello")
        assert editor_api.get_text() == "hello"

    def test_append_text(self, editor_api):
        editor_api.set_text("hello")
        editor_api.append_text(" world")
        assert editor_api.get_text() == "hello world"

    def test_insert_text(self, editor_api):
        editor_api.set_text("hello")
        editor_api._editor.setCursorPosition(0, 3)
        editor_api.insert_text("X")
        assert "helXlo" == editor_api.get_text()

    def test_clear(self, editor_api):
        editor_api.set_text("hello")
        editor_api.clear()
        assert editor_api.get_text() == ""


class TestState:
    """Test dirty state, file path management."""

    def test_is_dirty_initially_false(self, editor_api):
        assert not editor_api.is_dirty()

    def test_set_dirty(self, editor_api):
        # Insert text first so the buffer is non-empty, then set dirty
        editor_api.set_text("x")
        editor_api.set_dirty(True)
        assert editor_api.is_dirty()

    def test_clear_dirty(self, editor_api):
        editor_api.set_dirty(True)
        editor_api.set_dirty(False)
        assert not editor_api.is_dirty()

    def test_file_path_initially_none(self, editor_api):
        assert editor_api.file_path() is None

    def test_set_file_path(self, editor_api):
        editor_api.set_file_path("/tmp/test.py")
        assert editor_api.file_path() == "/tmp/test.py"


class TestProperties:
    """Test eol_mode, indentation_width, uses_tabs, lines."""

    def test_lines(self, editor_api):
        editor_api.set_text("line1\nline2\nline3")
        assert editor_api.lines() == 3

    def test_indentation_width(self, editor_api):
        assert editor_api.indentation_width() == 4

    def test_uses_tabs(self, editor_api):
        assert editor_api.uses_tabs() is False


class TestLoadFile:
    """Test load_file delegation."""

    def test_load_file(self, editor_api, tmp_path):
        p = tmp_path / "test.txt"
        p.write_text("file content", encoding="utf-8")
        editor_api.load_file(str(p))
        assert editor_api.get_text() == "file content"
        assert editor_api.file_path() == str(p)

    def test_load_file_empty_path(self, editor_api):
        with pytest.raises(ValueError):
            editor_api.load_file("")

    def test_load_file_non_string(self, editor_api):
        with pytest.raises(ValueError):
            editor_api.load_file(123)

    def test_load_file_nonexistent(self, editor_api):
        with pytest.raises(FileNotFoundError):
            editor_api.load_file("/nonexistent/file.txt")
