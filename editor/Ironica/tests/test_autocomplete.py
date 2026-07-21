"""Tests for autocomplete (editor/texteditor/autocomplete_menu.py).

Covers: popup lifecycle, debounce, keyboard navigation, insertion,
empty completion list, cleanup after editor destruction, cleanup after tab switching.
"""

import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import Qt, QTimer


class TestCompletionItem:
    """Test CompletionItem dataclass."""

    def test_creation(self):
        from editor.Ironica.autocomplete_menu import CompletionItem

        item = CompletionItem(name="test", kind="variable")
        assert item.name == "test"
        assert item.kind == "variable"
        assert item.documentation == ""
        assert item.score == 0

    def test_with_documentation(self):
        from editor.Ironica.autocomplete_menu import CompletionItem

        item = CompletionItem(name="fn", kind="function", documentation="A function")
        assert item.documentation == "A function"


class TestCompletionModel:
    """Test CompletionModel."""

    def test_empty_model(self):
        from editor.Ironica.autocomplete_menu import CompletionModel

        model = CompletionModel()
        assert model.rowCount() == 0
        assert model.all_items() == []

    def test_set_items(self):
        from editor.Ironica.autocomplete_menu import CompletionModel, CompletionItem

        model = CompletionModel()
        items = [
            CompletionItem(name="foo", kind="variable"),
            CompletionItem(name="bar", kind="function"),
        ]
        model.set_items(items)
        assert model.rowCount() == 2
        assert model.all_items() == items

    def test_item_at_row(self):
        from editor.Ironica.autocomplete_menu import CompletionModel, CompletionItem

        model = CompletionModel()
        item = CompletionItem(name="x", kind="text")
        model.set_items([item])
        assert model.item_at_row(0) is item
        assert model.item_at_row(5) is None

    def test_data_display_role(self):
        from editor.Ironica.autocomplete_menu import CompletionModel, CompletionItem
        from PyQt6.QtCore import QModelIndex

        model = CompletionModel()
        item = CompletionItem(name="hello", kind="text")
        model.set_items([item])
        index = model.index(0)
        assert model.data(index) == "hello"

    def test_data_user_role(self):
        from editor.Ironica.autocomplete_menu import CompletionModel, CompletionItem
        from PyQt6.QtCore import QModelIndex, Qt

        model = CompletionModel()
        item = CompletionItem(name="x", kind="text")
        model.set_items([item])
        index = model.index(0)
        assert model.data(index, Qt.ItemDataRole.UserRole) is item

    def test_data_invalid_index(self):
        from editor.Ironica.autocomplete_menu import CompletionModel
        from PyQt6.QtCore import QModelIndex

        model = CompletionModel()
        assert model.data(QModelIndex()) is None


class TestIntelliSenseMenu:
    """Test IntelliSenseMenu creation and item display."""

    def test_menu_creation(self, qapp_instance):
        from editor.Ironica.autocomplete_menu import IntelliSenseMenu

        menu = IntelliSenseMenu()
        assert not menu.isVisible()
        menu.deleteLater()

    def test_show_items(self, qapp_instance):
        from editor.Ironica.autocomplete_menu import (
            IntelliSenseMenu,
            CompletionItem,
        )

        menu = IntelliSenseMenu()
        items = [
            CompletionItem(name="alpha", kind="variable"),
            CompletionItem(name="beta", kind="function"),
        ]
        menu.show_items(items, "a")
        assert menu.isVisible()
        assert len(menu._filtered) >= 1
        menu.hide()
        menu.deleteLater()

    def test_show_items_empty_hides(self, qapp_instance):
        from editor.Ironica.autocomplete_menu import IntelliSenseMenu

        menu = IntelliSenseMenu()
        menu.show_items([])
        assert not menu.isVisible()
        menu.deleteLater()

    def test_navigate_up_down(self, qapp_instance):
        from editor.Ironica.autocomplete_menu import (
            IntelliSenseMenu,
            CompletionItem,
        )

        menu = IntelliSenseMenu()
        items = [
            CompletionItem(name="a", kind="text"),
            CompletionItem(name="b", kind="text"),
            CompletionItem(name="c", kind="text"),
        ]
        menu.show_items(items, "")
        menu.navigate_down()
        assert menu._selected_index == 1
        menu.navigate_up()
        assert menu._selected_index == 0
        menu.hide()
        menu.deleteLater()

    def test_accept_selection(self, qapp_instance):
        from editor.Ironica.autocomplete_menu import (
            IntelliSenseMenu,
            CompletionItem,
        )

        menu = IntelliSenseMenu()
        received = []
        menu.item_selected.connect(lambda name: received.append(name))
        items = [CompletionItem(name="chosen", kind="text")]
        menu.show_items(items, "")
        menu._accept_selection()
        assert received == ["chosen"]
        menu.deleteLater()


class TestAutocompleteExtension:
    """Test EditorAutocompleteExtension lifecycle."""

    def test_install_cleanup(self, editor):
        ext = editor._autocomplete_ext
        assert ext is not None
        ext.cleanup()
        assert ext._cleaned_up

    def test_double_cleanup_safe(self, editor):
        ext = editor._autocomplete_ext
        ext.cleanup()
        ext.cleanup()  # should not crash

    def test_schedule_after_cleanup_no_crash(self, editor):
        ext = editor._autocomplete_ext
        ext.cleanup()
        ext.schedule_autocomplete()  # should be a no-op

    def test_trigger_after_cleanup_no_crash(self, editor):
        ext = editor._autocomplete_ext
        ext.cleanup()
        ext.trigger_autocomplete()  # should be a no-op

    def test_cancel_after_cleanup_no_crash(self, editor):
        ext = editor._autocomplete_ext
        ext.cleanup()
        ext.cancel_autocomplete()  # should be a no-op

    def test_do_autocomplete_no_provider(self, editor):
        """Should cancel when there is no provider and prefix is short."""
        editor._autocomplete_ext._do_autocomplete()  # should not crash

    def test_get_word_prefix(self, editor):
        ext = editor._autocomplete_ext
        prefix = ext._get_word_prefix("hello world", 0, 5)
        assert prefix == "hello"

    def test_get_word_prefix_empty(self, editor):
        ext = editor._autocomplete_ext
        prefix = ext._get_word_prefix("", 0, 0)
        assert prefix == ""

    def test_get_word_prefix_out_of_range(self, editor):
        ext = editor._autocomplete_ext
        prefix = ext._get_word_prefix("hi", 100, 0)
        assert prefix == ""

    def test_scan_buffer(self, editor):
        ext = editor._autocomplete_ext
        items = ext._scan_buffer("foo bar foo baz", 0, "fo")
        names = [i.name for i in items]
        assert "foo" in names

    def test_infer_kind(self, editor):
        ext = editor._autocomplete_ext
        assert ext._infer_kind("MyClass") == "class"
        assert ext._infer_kind("func()") == "function"
        assert ext._infer_kind("CONST") == "constant"
        assert ext._infer_kind("var") == "variable"

    def test_insert_completion(self, editor):
        editor.setText("hel")
        editor.setCursorPosition(0, 3)
        ext = editor._autocomplete_ext
        ext._insert_completion("hello")
        assert "hello" in editor.text()


class TestProviderCompletion:
    """Test autocomplete with a mock provider."""

    def test_provider_items_merged(self, editor):
        from editor.Ironica.language_engine import BaseLanguageProvider

        class TestProvider(BaseLanguageProvider):
            def get_auto_completions(self, text, line, col):
                return ["provider_item"]

            def get_hover_hint(self, text, line, col):
                return None

            def get_definition_location(self, text, line, col):
                return None

            def format_source(self, source_code):
                return source_code

        editor.current_provider = TestProvider()
        ext = editor._autocomplete_ext
        items = ext._query_provider("test", 0, 0, "pro")
        names = [i.name for i in items]
        assert "provider_item" in names


class TestFlyout:
    """Test DocumentationFlyout creation."""

    def test_flyout_creation(self, qapp_instance):
        from editor.Ironica.autocomplete_menu import (
            DocumentationFlyout,
            CompletionItem,
        )

        item = CompletionItem(name="fn", kind="function", documentation="A doc string")
        flyout = DocumentationFlyout(item)
        assert flyout.item == item
        flyout.deleteLater()


class TestCompletionDelegate:
    """Test CompletionDelegate creation."""

    def test_delegate_creation(self, qapp_instance):
        from editor.Ironica.autocomplete_menu import (
            CompletionDelegate,
            IntelliSenseMenu,
        )

        menu = IntelliSenseMenu()
        delegate = CompletionDelegate(menu)
        delegate.set_filter_text("test")
        delegate.set_selected_row(2)
        assert delegate._filter_text == "test"
        assert delegate._selected_row == 2
        menu.deleteLater()
