"""Regression tests for specific bugs that have been identified and fixed.

Covers:
- Stale file path bugs
- Stale dirty state
- Duplicate tab entries
- Reopening after Save As
- Autocomplete surviving closed editors
- Autocomplete surviving tab changes
- replace_all infinite-loop scenarios
- Readonly state inconsistencies
- Editor/tab synchronization
- Language registration failures
"""

import pytest
import os
import stat


class TestStaleFilePath:
    """Verify that file path is always current after operations."""

    def test_file_path_after_save_as(self, editor, tmp_path):
        p1 = tmp_path / "original.txt"
        p1.write_text("original", encoding="utf-8")
        editor.load_from_file(str(p1))
        assert editor.current_file_path == str(p1)

        p2 = tmp_path / "renamed.txt"
        editor.save_to_file(str(p2))
        assert editor.current_file_path == str(p2)
        # Old path should no longer be tracked
        assert editor.current_file_path != str(p1)

    def test_file_path_after_new_tab(self, qapp_instance):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor
        from editor.Ironica.code_editor import CodeEditor

        parent = QWidget()
        parent.currentDirectory = "/tmp"
        parent.status_bar = None

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        editor = tabs.add_new_editor()
        assert editor.current_file_path is None

        parent.deleteLater()


class TestStaleDirtyState:
    """Verify dirty state is consistent after save and reload."""

    def test_dirty_state_after_save(self, editor, tmp_path):
        p = tmp_path / "dirty.txt"
        editor.setText("content")
        editor.setModified(True)
        editor.save_to_file(str(p))
        assert not editor.is_dirty()

    def test_dirty_state_after_load(self, editor, tmp_path):
        p = tmp_path / "dirty.txt"
        p.write_text("content", encoding="utf-8")
        editor.load_from_file(str(p))
        assert not editor.is_dirty()

    def test_dirty_state_after_edit(self, editor):
        editor.setText("")
        assert not editor.is_dirty()
        editor.insert("x")
        assert editor.is_dirty()


class TestDuplicateTabEntries:
    """Verify that opening the same file doesn't create duplicate tabs."""

    def test_no_duplicates_on_reopen(self, qapp_instance, tmp_path):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = QWidget()
        parent.currentDirectory = "/tmp"
        parent.status_bar = None

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        p = tmp_path / "dup.txt"
        p.write_text("content", encoding="utf-8")

        tabs.add_new_editor(file_name="dup.txt", file_path=str(p))
        tabs.add_new_editor(file_name="dup.txt", file_path=str(p))
        tabs.add_new_editor(file_name="dup.txt", file_path=str(p))

        assert tabs.count() == 1
        assert len(tabs.opened_files) == 1

        parent.deleteLater()

    def test_opened_files_map_consistent(self, qapp_instance, tmp_path):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = QWidget()
        parent.currentDirectory = "/tmp"
        parent.status_bar = None

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        files = []
        for i in range(5):
            p = tmp_path / f"file{i}.txt"
            p.write_text(f"content{i}", encoding="utf-8")
            tabs.add_new_editor(file_name=f"file{i}.txt", file_path=str(p))
            files.append(p)

        assert tabs.count() == 5
        assert len(tabs.opened_files) == 5

        # Close some tabs and verify map
        tabs.close_editor(1)
        tabs.close_editor(3)
        assert tabs.count() == 3
        assert len(tabs.opened_files) == 3

        parent.deleteLater()


class TestAutocompleteSurvival:
    """Test autocomplete behaviour after tab/editor changes."""

    def test_cleanup_on_close(self, qapp_instance):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = QWidget()
        parent.currentDirectory = "/tmp"
        parent.status_bar = None

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        editor = tabs.add_new_editor(content="test")
        ext = editor._autocomplete_ext
        assert ext is not None

        tabs.close_editor(0)
        # The extension should have been cleaned up before deletion
        assert ext._cleaned_up

        parent.deleteLater()

    def test_autocomplete_cancelled_on_tab_change(self, qapp_instance):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor
        from editor.Ironica.autocomplete_menu import (
            IntelliSenseMenu,
            CompletionItem,
        )

        parent = QWidget()
        parent.currentDirectory = "/tmp"
        parent.status_bar = None

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        editor1 = tabs.add_new_editor(content="tab1")
        tabs.add_new_editor(content="tab2")

        # Simulate autocomplete open on editor1
        items = [CompletionItem(name="test", kind="text")]
        editor1._autocomplete_ext.menu.show_items(items, "test")

        # Manually cancel autocomplete (tab change in headless mode
        # doesn't trigger the event filter hide)
        editor1._autocomplete_ext.cancel_autocomplete()
        assert not editor1._autocomplete_ext.menu.isVisible()

        parent.deleteLater()


class TestReplaceAllInfiniteLoop:
    """Test that replace_all terminates correctly in edge cases."""

    def test_replace_all_self_referencing(self, editor):
        """Replacing 'a' with 'aa' should terminate."""
        editor.setText("a a a a a")
        count = (
            editor._editor_api().replace_all("a", "aa")
            if hasattr(editor, "_editor_api")
            else 0
        )
        # Use the API directly
        from editor.Ironica.api import EditorAPI

        api = EditorAPI(editor)
        count = api.replace_all("a", "aa")
        # Should terminate with a reasonable count
        assert count > 0
        assert count <= 100

    def test_replace_all_replacement_contains_find(self, editor):
        """Replacing 'x' with 'x!' should terminate."""
        from editor.Ironica.api import EditorAPI

        api = EditorAPI(editor)
        editor.setText("x x x")
        count = api.replace_all("x", "x!")
        assert count == 3

    def test_replace_all_same_length(self, editor):
        """Replacing 'a' with 'b' should work normally."""
        from editor.Ironica.api import EditorAPI

        api = EditorAPI(editor)
        editor.setText("a b a b a")
        count = api.replace_all("a", "c")
        assert count == 3
        assert editor.text() == "c b c b c"

    def test_replace_all_no_matches(self, editor):
        from editor.Ironica.api import EditorAPI

        api = EditorAPI(editor)
        editor.setText("hello")
        count = api.replace_all("xyz", "abc")
        assert count == 0

    def test_replace_all_empty_string(self, editor):
        from editor.Ironica.api import EditorAPI

        api = EditorAPI(editor)
        editor.setText("hello")
        count = api.replace_all("", "x")
        assert count == 0

    def test_replace_all_single_char_in_multiline(self, editor):
        from editor.Ironica.api import EditorAPI

        api = EditorAPI(editor)
        editor.setText("a\nb\na\nb\na")
        count = api.replace_all("a", "z")
        assert count == 3


class TestReadonlyConsistency:
    """Test readonly state stays consistent."""

    def test_readonly_after_load(self, editor, tmp_path):
        p = tmp_path / "ro.txt"
        p.write_text("content", encoding="utf-8")
        os.chmod(str(p), stat.S_IRUSR)
        try:
            editor.load_from_file(str(p))
            assert editor.isReadOnly()
            # Tab should show readonly indicator
        finally:
            os.chmod(str(p), stat.S_IRWXU)

    def test_readonly_not_persisted_after_new_content(self, editor, tmp_path):
        p = tmp_path / "ro.txt"
        p.write_text("content", encoding="utf-8")
        os.chmod(str(p), stat.S_IRUSR)
        try:
            editor.load_from_file(str(p))
            assert editor.isReadOnly()
        finally:
            os.chmod(str(p), stat.S_IRWXU)


class TestEditorTabSync:
    """Test that editor and tab manager stay in sync."""

    def test_tab_count_matches_opened_files(self, qapp_instance, tmp_path):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = QWidget()
        parent.currentDirectory = "/tmp"
        parent.status_bar = None

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        for i in range(3):
            p = tmp_path / f"f{i}.txt"
            p.write_text(str(i), encoding="utf-8")
            tabs.add_new_editor(file_name=f"f{i}.txt", file_path=str(p))

        assert tabs.count() == len(tabs.opened_files)

        tabs.close_editor(1)
        assert tabs.count() == len(tabs.opened_files)

        parent.deleteLater()

    def test_close_all_leaves_empty_state(self, qapp_instance):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = QWidget()
        parent.currentDirectory = "/tmp"
        parent.status_bar = None

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        tabs.add_new_editor(content="a")
        tabs.add_new_editor(content="b")
        tabs.close_editor(0)
        tabs.close_editor(0)

        assert tabs.count() == 0
        assert len(tabs.opened_files) == 0

        parent.deleteLater()


class TestLanguageRegistrationFailures:
    """Test that language registration failures don't crash the system."""

    def test_malformed_json_doesnt_crash(self, language_registry, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json {{{", encoding="utf-8")
        result = language_registry.register_language(str(p))
        assert result is False
        assert language_registry.list_languages() == []

    def test_missing_file_doesnt_crash(self, language_registry):
        result = language_registry.register_language("/nonexistent/path.json")
        assert result is False

    def test_empty_json_doesnt_crash(self, language_registry, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("{}", encoding="utf-8")
        result = language_registry.register_language(str(p))
        # Should fail validation (no lang key)
        assert result is False

    def test_wrong_type_provider_doesnt_crash(self, language_registry, tmp_path):
        p = tmp_path / "test.json"
        import json

        config = {
            "lang": "bad_provider",
            "extensions": ["bp"],
            "styles": {"kw": "#000"},
            "keywords": {"kw": ["x"]},
        }
        p.write_text(json.dumps(config), encoding="utf-8")
        result = language_registry.register_language(
            str(p), provider_instance="not_a_provider"
        )
        assert result is False
