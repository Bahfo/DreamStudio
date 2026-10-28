"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for tab open/close/save lifecycle.
"""

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])