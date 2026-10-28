"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for tab deduplication by normalized path.
"""

import os

import pytest


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])