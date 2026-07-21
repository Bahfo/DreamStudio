"""Tests for DreamTabbedEditor (editor/texteditor/tab_editor.py).

Covers: opening multiple editors, duplicate files, reopening saved files,
closing tabs, dirty tracking, readonly indicators, tab index consistency,
file lookup map consistency.
"""

import pytest
from PyQt6.QtCore import Qt


def _make_tab_parent():
    """Create a QWidget with the attributes DreamTabbedEditor expects."""
    from PyQt6.QtWidgets import QWidget

    parent = QWidget()
    parent.currentDirectory = "/tmp"
    parent.status_bar = None
    parent.current_theme = "dark"
    return parent


class TestTabEditorConstruction:
    """Test DreamTabbedEditor instantiation."""

    def test_tabs_closable(self, qapp_instance):
        from PyQt6.QtWidgets import QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = _make_tab_parent()

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        assert tabs.tabsClosable()
        parent.deleteLater()

    def test_add_new_editor(self, qapp_instance):
        from PyQt6.QtWidgets import QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor
        from editor.Ironica.code_editor import CodeEditor

        parent = _make_tab_parent()

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        editor = tabs.add_new_editor()
        assert isinstance(editor, CodeEditor)
        assert tabs.count() == 1

        editor._autocomplete_ext.cleanup()
        parent.deleteLater()


class TestDuplicateOpening:
    """Test that opening the same file twice reuses the existing tab."""

    def test_duplicate_file_reuses_tab(self, qapp_instance, tmp_path):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor
        from editor.Ironica.code_editor import CodeEditor

        parent = _make_tab_parent()

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        p = tmp_path / "test.txt"
        p.write_text("content", encoding="utf-8")

        editor1 = tabs.add_new_editor(
            file_name="test.txt", file_path=str(p), language=None
        )
        assert tabs.count() == 1

        editor2 = tabs.add_new_editor(
            file_name="test.txt", file_path=str(p), language=None
        )
        # Should reuse the same tab, not create a new one
        assert tabs.count() == 1

        parent.deleteLater()


class TestClosingTabs:
    """Test close_editor, close_tab, and index adjustment."""

    def test_close_editor_adjusts_indices(self, qapp_instance):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = _make_tab_parent()

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        tabs.add_new_editor(content="tab1")
        tabs.add_new_editor(content="tab2")
        tabs.add_new_editor(content="tab3")
        assert tabs.count() == 3

        tabs.close_editor(0)
        assert tabs.count() == 2

        parent.deleteLater()

    def test_close_nonexistent_tab(self, qapp_instance):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = _make_tab_parent()

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        tabs.close_editor(0)  # should not crash when no tabs exist
        tabs.close_tab()  # should not crash

        parent.deleteLater()

    def test_opened_files_map_after_close(self, qapp_instance, tmp_path):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = _make_tab_parent()

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        p1 = tmp_path / "a.txt"
        p2 = tmp_path / "b.txt"
        p1.write_text("a", encoding="utf-8")
        p2.write_text("b", encoding="utf-8")

        tabs.add_new_editor(file_name="a.txt", file_path=str(p1))
        tabs.add_new_editor(file_name="b.txt", file_path=str(p2))
        assert len(tabs.opened_files) == 2

        # Close the first tab
        tabs.close_editor(0)
        assert len(tabs.opened_files) == 1

        parent.deleteLater()


class TestDirtyTracking:
    """Test dirty dot indicator sync."""

    def test_dirty_tracker_integration(self, qapp_instance):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = _make_tab_parent()

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        editor = tabs.add_new_editor(content="test")
        editor.setText("modified")
        assert editor.is_dirty()

        parent.deleteLater()


class TestResolveKey:
    """Test the path normalisation helper."""

    def test_resolve_key_none(self):
        from editor.Ironica.tab_editor import DreamTabbedEditor

        assert DreamTabbedEditor.resolve_key(None) is None

    def test_resolve_key_empty(self):
        from editor.Ironica.tab_editor import DreamTabbedEditor

        assert DreamTabbedEditor.resolve_key("") is None

    def test_resolve_key_normalizes(self):
        from editor.Ironica.tab_editor import DreamTabbedEditor

        result = DreamTabbedEditor.resolve_key("/tmp/../tmp/test.txt")
        assert result is not None


class TestFontPropagation:
    """Test set_font_size propagates to all editors."""

    def test_set_font_size(self, qapp_instance):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = _make_tab_parent()

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        tabs.add_new_editor(content="tab1")
        tabs.add_new_editor(content="tab2")
        tabs.set_font_size(16)

        for i in range(tabs.count()):
            w = tabs.widget(i)
            if hasattr(w, "font_size"):
                assert w.font_size == 16

        parent.deleteLater()


class TestFallBack:
    """Test the FallBack widget."""

    def test_fallback_set_text(self, qapp_instance):
        from editor.Ironica.tab_editor import FallBack

        fb = FallBack()
        fb.setText("test message")
        assert fb.page_label.text() == "test message"
        fb.deleteLater()


class TestCloseInterceptor:
    """Test close interceptor add/remove."""

    def test_interceptor_prevents_close(self, qapp_instance):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from editor.Ironica.tab_editor import DreamTabbedEditor

        parent = _make_tab_parent()

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        tabs.add_new_editor(content="keep me")
        assert tabs.count() == 1

        def reject_close(index, editor):
            return False

        tabs.add_close_interceptor(reject_close)
        tabs.close_editor(0)
        assert tabs.count() == 1  # interceptor prevented close

        tabs.remove_close_interceptor(reject_close)
        tabs.close_editor(0)
        assert tabs.count() == 0

        parent.deleteLater()
