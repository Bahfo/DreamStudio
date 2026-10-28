"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the tab bar's mirror of editor dirty state.
"""

import pytest


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])