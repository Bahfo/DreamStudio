"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for tab lifecycle management in ``DreamTabbedEditor`` and the
per-tab ``EditorAPI`` facade.
"""

import os
from unittest.mock import patch

import pytest


def _dialog_factory(result):
    """Build a drop-in UnsavedChangesDialog that returns *result*."""

    class FakeDialog:
        RESULT_SAVE = "save"
        RESULT_DISCARD = "discard"
        RESULT_CANCEL = "cancel"

        def __init__(self, *args, **kwargs):
            self.result = result

        def exec(self):
            return result

    return FakeDialog


class TestTabEditorDedup:
    """Tests for tab deduplication by normalized path."""

    def test_open_same_file_twice_activates_existing(self, qapp, tab_editor_parent, temp_workspace):
        """Opening the same path twice keeps a single tab."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.open_file_by_path(str(test_file))
        first = tabs.widget(0)

        tabs.open_file_by_path(str(test_file))

        assert tabs.count() == 1
        assert tabs.widget(0) is first
        assert tabs.currentIndex() == 0

    def test_resolve_key_normalizes(self, qapp, tab_editor_parent):
        """resolve_key normalizes ``..`` segments."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        tabs = DreamTabbedEditor(tab_editor_parent)

        key1 = tabs.resolve_key("/path/to/file.py")
        key2 = tabs.resolve_key("/path/to/../to/file.py")

        assert key1 == key2
        assert key1 == os.path.normcase(os.path.normpath(key1))

    def test_resolve_key_empty_returns_none(self, qapp, tab_editor_parent):
        """Empty paths have no dedup key."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        tabs = DreamTabbedEditor(tab_editor_parent)

        assert tabs.resolve_key("") is None

    def test_normcase_platform_semantics(self, qapp, tab_editor_parent):
        """Keys are case-insensitive only where normcase is."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        tabs = DreamTabbedEditor(tab_editor_parent)
        key1 = tabs.resolve_key("C:/Path/File.py")
        key2 = tabs.resolve_key("c:/path/file.py")

        if os.name == "nt":
            assert key1 == key2
        else:
            pytest.skip("POSIX paths are case-sensitive by definition")

    def test_untitled_tabs_get_unique_keys(self, qapp, tab_editor_parent):
        """Tabs created without a path receive distinct synthetic keys."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.add_new_editor(file_name="one.txt", content="one")
        tabs.add_new_editor(file_name="two.txt", content="two")

        key1 = tabs.widget(0).file_key
        key2 = tabs.widget(1).file_key

        assert key1 != key2
        assert key1.startswith("__untitled_")
        assert key2.startswith("__untitled_")


class TestTabLifecycle:
    """Tests for tab open/close/save lifecycle."""

    def test_open_file_creates_tab(self, qapp, tab_editor_parent, temp_workspace):
        """open_file_by_path creates a tab backed by a CodeEditor."""
        from editor.Ironica.code_editor import CodeEditor
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.open_file_by_path(str(test_file))

        assert tabs.count() == 1
        editor = tabs.get_editor_for_path(str(test_file))
        assert isinstance(editor, CodeEditor)
        assert editor.current_file_path == str(test_file)
        assert editor.text().startswith("print('hello')")

    def test_close_editor_removes_tab(self, qapp, tab_editor_parent, temp_workspace):
        """close_editor removes the tab and its dedup entry."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.open_file_by_path(str(test_file))
        assert tabs.count() == 1

        tabs.close_editor(0)

        assert tabs.count() == 0
        assert tabs.opened_files == {}

    def test_close_dirty_cancel_keeps_tab(self, qapp, tab_editor_parent, temp_workspace):
        """Cancelling the unsaved-changes prompt leaves the tab open."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.open_file_by_path(str(test_file))
        editor = tabs.get_editor_for_path(str(test_file))
        editor.insertAt("changed ", 0, 0)
        assert editor.isModified() is True

        fake_dialog = _dialog_factory("cancel")
        with patch("editor.widgets.QExitDialog.UnsavedChangesDialog", fake_dialog):
            tabs._on_close_requested(0)

        assert tabs.count() == 1
        assert editor.isModified() is True

    def test_close_dirty_save_closes_tab(self, qapp, tab_editor_parent, temp_workspace):
        """Choosing Save persists the buffer and closes the tab."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.open_file_by_path(str(test_file))
        editor = tabs.get_editor_for_path(str(test_file))
        editor.insertAt("changed ", 0, 0)

        fake_dialog = _dialog_factory("save")
        with patch("editor.widgets.QExitDialog.UnsavedChangesDialog", fake_dialog):
            tabs._on_close_requested(0)

        assert tabs.count() == 0
        assert "changed" in test_file.read_text()

    def test_close_dirty_save_failure_keeps_tab(self, qapp, tab_editor_parent, temp_workspace):
        """A failed save leaves the tab open so work is not lost."""
        from editor.Ironica.code_editor import CodeEditor
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.open_file_by_path(str(test_file))
        editor = tabs.get_editor_for_path(str(test_file))
        editor.insertAt("changed ", 0, 0)

        fake_dialog = _dialog_factory("save")
        with (
            patch("editor.widgets.QExitDialog.UnsavedChangesDialog", fake_dialog),
            patch.object(CodeEditor, "save", return_value=False),
        ):
            tabs._on_close_requested(0)

        assert tabs.count() == 1

    def test_save_all_saves_every_file_backed_editor(self, qapp, tab_editor_parent, temp_workspace):
        """save_all_files calls save() once per file-backed editor."""
        from editor.Ironica.code_editor import CodeEditor
        from editor.Ironica.tab_editor import DreamTabbedEditor

        file1 = temp_workspace / "test1.py"
        file1.write_text("print('1')")
        file2 = temp_workspace / "test2.py"
        file2.write_text("print('2')")

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.open_file_by_path(str(file1))
        tabs.open_file_by_path(str(file2))

        with patch.object(CodeEditor, "save", return_value=True) as save:
            tabs.save_all_files()

        assert save.call_count == 2
        assert tabs.count() == 2


class TestTabCloseInterceptors:
    """Tests for close interceptors."""

    def test_interceptor_can_abort_close(self, qapp, tab_editor_parent, temp_workspace):
        """An interceptor returning False aborts close_editor."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.open_file_by_path(str(test_file))

        def abort_interceptor(index, editor):
            return False

        tabs.add_close_interceptor(abort_interceptor)

        tabs.close_editor(0)
        assert tabs.count() == 1

        tabs.remove_close_interceptor(abort_interceptor)
        tabs.close_editor(0)
        assert tabs.count() == 0

    def test_interceptor_exception_does_not_block_close(self, qapp, tab_editor_parent, temp_workspace):
        """An interceptor that raises is ignored (documented behaviour)."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.open_file_by_path(str(test_file))

        def broken_interceptor(index, editor):
            raise RuntimeError("interceptor failure")

        tabs.add_close_interceptor(broken_interceptor)
        tabs.close_editor(0)

        assert tabs.count() == 0


class TestEditorAPIFacade:
    """Tests for the EditorAPI per-tab facade."""

    def test_editor_api_requires_editor(self, qapp):
        """EditorAPI rejects a None editor."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        with pytest.raises(ValueError):
            EditorAPI(None)

        editor = QsciScintilla()
        api = EditorAPI(editor)
        assert api.editor is editor

    def test_read_only_blocks_mutations(self, qapp):
        """Mutating methods no-op on a read-only editor."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        editor = QsciScintilla()
        editor.setText("original")
        editor.setReadOnly(True)

        api = EditorAPI(editor)
        api.cut()
        api.paste()
        api.delete()
        api.indent()
        api.unindent()
        api.duplicate_line()

        assert editor.text() == "original"

    def test_clipboard_methods_exist(self, qapp):
        """Clipboard methods exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        for name in (
            "cut",
            "copy",
            "copy_as_plain_text",
            "paste",
            "delete",
            "select_all",
            "select_none",
        ):
            assert hasattr(api, name), name

    def test_history_methods_exist(self, qapp):
        """Undo/redo exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        assert hasattr(api, "undo")
        assert hasattr(api, "redo")

    def test_structure_methods_exist(self, qapp):
        """Structural editing methods exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        for name in (
            "indent",
            "unindent",
            "format_code",
            "comment_line",
            "comment",
            "uncomment_line",
            "uncomment",
            "duplicate_line",
            "duplicate_selection",
        ):
            assert hasattr(api, name), name

    def test_navigation_methods_exist(self, qapp):
        """Implemented navigation methods exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        for name in (
            "goto_definition",
            "goto_declaration",
            "goto_implementation",
        ):
            assert hasattr(api, name), name

    def test_folding_methods_exist(self, qapp):
        """Folding methods exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        for name in (
            "expand_current",
            "expand_all",
            "collapse_current",
            "smart_collapse",
            "collapse_includes",
        ):
            assert hasattr(api, name), name

    def test_file_methods_exist(self, qapp):
        """load_file/save exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        assert hasattr(api, "load_file")
        assert hasattr(api, "save")

    def test_set_language_method_exists(self, qapp):
        """Contract gap: documented set_language() is absent from EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        assert hasattr(api, "set_language")


class TestFallbackTab:
    """Tests for FallBack tabs when a file cannot be shown normally."""

    def test_binary_file_opens_binary_editor(self, qapp, tab_editor_parent, temp_workspace):
        """ELF paths are routed to add_binary_editor."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "binary"
        test_file.write_bytes(b"\x7fELF")

        tabs = DreamTabbedEditor(tab_editor_parent)

        with (
            patch.object(DreamTabbedEditor, "_is_elf_binary", return_value=True),
            patch.object(DreamTabbedEditor, "add_binary_editor") as add_binary,
        ):
            tabs.open_file_by_path(str(test_file))

        add_binary.assert_called_once()

    def test_decode_error_opens_fallback(self, qapp, tab_editor_parent, temp_workspace):
        """A UnicodeDecodeError during load creates a FallBack tab."""
        from editor.Ironica.code_editor import CodeEditor
        from editor.Ironica.tab_editor import DreamTabbedEditor, FallBack

        test_file = temp_workspace / "bad.py"
        test_file.write_bytes(b"\xff\xfe")

        tabs = DreamTabbedEditor(tab_editor_parent)

        error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        with patch.object(CodeEditor, "load_from_file", side_effect=error):
            tabs.open_file_by_path(str(test_file))

        assert tabs.count() == 1
        assert isinstance(tabs.widget(0), FallBack)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
