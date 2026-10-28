"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the CodeEditor dirty flag (single source of truth).
"""

from unittest.mock import patch

import pytest


class TestCodeEditorDirtyState:
    """Tests for the CodeEditor dirty flag (single source of truth)."""

    def test_initial_not_dirty(self, qapp):
        """A new editor starts clean."""
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)

        assert editor.is_dirty() is False
        assert editor._is_dirty is False

    def test_text_change_sets_dirty(self, qapp):
        """A text change marks the editor dirty and emits True."""
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)
        dirty_signals = []
        editor.dirty_state_changed.connect(dirty_signals.append)

        editor._on_text_changed()

        assert editor.is_dirty() is True
        assert editor._is_dirty is True
        assert dirty_signals == [True]

    def test_second_change_does_not_re_emit(self, qapp):
        """Only the clean -> dirty transition emits True."""
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)
        dirty_signals = []
        editor.dirty_state_changed.connect(dirty_signals.append)

        editor._on_text_changed()
        editor._on_text_changed()

        assert dirty_signals == [True]

    def test_clear_dirty_resets_flag(self, qapp):
        """clear_dirty resets the flag without emitting."""
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)
        editor._is_dirty = True

        editor.clear_dirty()

        assert editor.is_dirty() is False
        assert editor._is_dirty is False

    def test_save_clears_dirty(self, qapp, temp_workspace):
        """save() writes the buffer and clears the dirty flag."""
        from editor.Ironica.code_editor import CodeEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        editor = CodeEditor(None)
        editor.load_from_file(str(test_file))
        editor.setText("print('changed')")
        editor._on_text_changed()
        assert editor.is_dirty() is True

        assert editor.save() is True
        assert editor.is_dirty() is False
        assert test_file.read_text() == "print('changed')"

    def test_load_from_file_resets_dirty(self, qapp, temp_workspace):
        """Loading a file resets dirty state and emits False."""
        from editor.Ironica.code_editor import CodeEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        editor = CodeEditor(None)
        editor._is_dirty = True
        dirty_signals = []
        editor.dirty_state_changed.connect(dirty_signals.append)

        editor.load_from_file(str(test_file))

        assert editor.is_dirty() is False
        assert dirty_signals[-1] is False

    def test_load_blocks_signals_while_setting_text(self, qapp, temp_workspace):
        """load_from_file blocks signals while populating the buffer."""
        from editor.Ironica.code_editor import CodeEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        editor = CodeEditor(None)
        with patch.object(editor, "blockSignals", wraps=editor.blockSignals) as spy:
            editor.load_from_file(str(test_file))

        spied_calls = [call.args[0] for call in spy.call_args_list]
        assert True in spied_calls
        assert False in spied_calls

    def test_read_only_file_opens_readonly(self, qapp, temp_workspace):
        """A file without write bits opens read-only."""
        import stat

        from editor.Ironica.code_editor import CodeEditor

        test_file = temp_workspace / "readonly.py"
        test_file.write_text("print('hello')")
        test_file.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        editor = CodeEditor(None)
        editor.load_from_file(str(test_file))

        assert editor.isReadOnly() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])