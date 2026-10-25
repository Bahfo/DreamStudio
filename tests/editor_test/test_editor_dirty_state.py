"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for editor dirty-state management and its downstream fan-out.
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


class TestTabBarDirtyMirror:
    """Tests for the tab bar's mirror of editor dirty state."""

    def test_mark_dirty_adds_and_removes_index(self, qapp):
        """mark_dirty maintains the dirty index set."""
        from editor.widgets.QDreamTabEditor import DreamStudioIDETabBar

        tab_bar = DreamStudioIDETabBar()

        tab_bar.mark_dirty(0, True)
        assert 0 in tab_bar._dirty_indices

        tab_bar.mark_dirty(0, False)
        assert 0 not in tab_bar._dirty_indices

    def test_rebuild_dirty_indices_from_widgets(self, qapp):
        """rebuild_dirty_indices derives the set from tab widgets."""
        from PyQt6.QtWidgets import QWidget

        from editor.widgets.QDreamTabEditor import QDreamTabEditor

        class DummyEditor(QWidget):
            def __init__(self, dirty):
                super().__init__()
                self._dirty = dirty

            def is_dirty(self):
                return self._dirty

        tabs = QDreamTabEditor()
        tabs.addTab(DummyEditor(True), "dirty")
        tabs.addTab(DummyEditor(False), "clean")

        tabs.tabBar().rebuild_dirty_indices()

        assert tabs.tabBar()._dirty_indices == {0}

    def test_rebuild_readonly_indices_from_widgets(self, qapp):
        """rebuild_readonly_indices derives the lock set from tab widgets."""
        from PyQt6.QtWidgets import QWidget

        from editor.widgets.QDreamTabEditor import QDreamTabEditor

        class DummyEditor(QWidget):
            def __init__(self, readonly):
                super().__init__()
                self._readonly = readonly

            def isReadOnly(self):
                return self._readonly

        tabs = QDreamTabEditor()
        tabs.addTab(DummyEditor(False), "writable")
        tabs.addTab(DummyEditor(True), "locked")

        tabs.tabBar().rebuild_readonly_indices()

        assert tabs.tabBar()._readonly_indices == {1}


class TestDirtyDrivesDiagnostics:
    """Tests for the dirty flag driving the diagnostic store merge policy."""

    @staticmethod
    def _problem(message, code="E101", severity="error", path="test.py", line=1):
        from editor.analysis.types import Problem

        return Problem(
            file_path=path,
            severity=severity,
            message=message,
            line=line,
            column=0,
            source="test",
            code=code,
            end_line=line,
            end_column=10,
        )

    def test_dirty_buffer_shows_live_only(self, qapp):
        """A dirty buffer hides stale on-disk diagnostics (invariant D3)."""
        from editor.analysis.diagnostic_store import DiagnosticStore

        store = DiagnosticStore()
        store.set_disk_results(
            [("test.py", [self._problem("Disk error", "E101", line=1)])],
            "disk_builtin",
        )
        store.set_disk_results(
            [("test.py", [self._problem("Ruff error", "RUF001", line=2)])],
            "disk_external:ruff",
        )
        store.set_live_results("test.py", 1, [self._problem("Live error", "L101", line=3)])

        store.mark_dirty("test.py")
        problems = store.problems_for("test.py")

        assert [p.code for p in problems] == ["L101"]

    def test_clean_buffer_shows_merged_results(self, qapp):
        """A clean buffer merges live, builtin, and external buckets (D4)."""
        from editor.analysis.diagnostic_store import DiagnosticStore

        store = DiagnosticStore()
        store.set_disk_results(
            [("test.py", [self._problem("Disk error", "E101", line=1)])],
            "disk_builtin",
        )
        store.set_disk_results(
            [("test.py", [self._problem("Ruff error", "RUF001", line=2)])],
            "disk_external:ruff",
        )
        store.set_live_results("test.py", 1, [self._problem("Live error", "L101", line=3)])

        problems = store.problems_for("test.py")

        assert {p.code for p in problems} == {"E101", "RUF001", "L101"}

    def test_stale_revision_is_discarded(self, qapp):
        """Older buffer revisions never overwrite newer ones (invariant D5)."""
        from editor.analysis.diagnostic_store import DiagnosticStore

        store = DiagnosticStore()
        revision_one = store.note_buffer_change("test.py")
        store.set_live_results("test.py", revision_one, [self._problem("Old", "L101")])

        revision_two = store.note_buffer_change("test.py")
        store.set_live_results("test.py", revision_two, [self._problem("New", "L102")])

        # A delayed result from the older buffer revision must be ignored.
        store.set_live_results("test.py", revision_one, [self._problem("Stale", "L100")])

        problems = store.problems_for("test.py")

        assert [p.code for p in problems] == ["L102"]

    def test_mark_clean_reports_state_change(self, qapp):
        """mark_clean reports whether the path was dirty."""
        from editor.analysis.diagnostic_store import DiagnosticStore

        store = DiagnosticStore()
        store.mark_dirty("test.py")

        assert store.is_dirty("test.py") is True
        assert store.mark_clean("test.py") is True
        assert store.is_dirty("test.py") is False
        assert store.mark_clean("test.py") is False


class TestDirtyDrivesGit:
    """Tests for the dirty flag requesting a VCS status scan."""

    def test_dirty_true_requests_git_scan(self, qapp, tab_editor_parent):
        """A dirty editor requests a git scan tagged editor:dirty_true."""
        from editor.Ironica.tab_editor import DreamTabbedEditor
        from editor.utils.git_control import status_service

        tabs = DreamTabbedEditor(tab_editor_parent)

        with patch.object(status_service, "get_status_service") as get_service:
            tabs._on_editor_dirty_changed_explicit(tabs, True)

        get_service.return_value.request_scan.assert_called_once_with("editor:dirty_true")

    def test_dirty_false_requests_git_scan(self, qapp, tab_editor_parent):
        """A saved editor requests a git scan tagged editor:dirty_false."""
        from editor.Ironica.tab_editor import DreamTabbedEditor
        from editor.utils.git_control import status_service

        tabs = DreamTabbedEditor(tab_editor_parent)

        with patch.object(status_service, "get_status_service") as get_service:
            tabs._on_editor_dirty_changed_explicit(tabs, False)

        get_service.return_value.request_scan.assert_called_once_with("editor:dirty_false")


class TestEncodingFallback:
    """Tests for the documented encoding fallback chain."""

    def test_utf8_loads(self, qapp, temp_workspace):
        """A plain UTF-8 file loads intact."""
        from editor.Ironica.code_editor import CodeEditor

        test_file = temp_workspace / "utf8.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        editor = CodeEditor(None)
        editor.load_from_file(str(test_file))

        assert "hello" in editor.text()

    def test_utf8_sig_loads_without_bom(self, qapp, temp_workspace):
        """A UTF-8 BOM file loads and the BOM is stripped."""
        from editor.Ironica.code_editor import CodeEditor

        test_file = temp_workspace / "utf8_sig.py"
        test_file.write_text("print('hello')", encoding="utf-8-sig")

        editor = CodeEditor(None)
        editor.load_from_file(str(test_file))

        assert editor.text().startswith("print('hello')")

    def test_undecodable_bytes_never_raise(self, qapp, temp_workspace):
        """The final fallback decodes with errors='replace' (invariant E4)."""
        from editor.Ironica.code_editor import CodeEditor

        test_file = temp_workspace / "binary.py"
        test_file.write_bytes(b"print('\xff\xfe')")

        editor = CodeEditor(None)
        editor.load_from_file(str(test_file))

        assert "\ufffd" in editor.text()

    def test_missing_file_raises_file_not_found(self, qapp, temp_workspace):
        """Loading a missing file raises FileNotFoundError."""
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)

        with pytest.raises(FileNotFoundError):
            editor.load_from_file(str(temp_workspace / "missing.py"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
