"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for editor navigation: the per-tab facade, provider delegation, target
resolution, language registration, and outline parsing.

Contract-gap tests deliberately fail when a documented API is absent or
delegates to the wrong handler. They are evidence, not skipped checks.
"""

from unittest.mock import MagicMock

import pytest


class TestEditorAPINavigationDelegation:
    """EditorAPI navigation methods must invoke their matching handler."""

    @staticmethod
    def _api():
        from editor.Ironica.api import EditorAPI

        editor = MagicMock()
        editor.isReadOnly.return_value = False
        return EditorAPI(editor), editor

    def test_goto_definition_delegates_to_definition_handler(self):
        """goto_definition calls execute_goto_definition."""
        api, editor = self._api()

        api.goto_definition(4, 2)

        editor.execute_goto_definition.assert_called_once_with(4, 2)

    def test_goto_declaration_delegates_to_declaration_handler(self):
        """Contract gap: goto_declaration must not reuse the definition handler."""
        api, editor = self._api()

        api.goto_declaration(4, 2)

        editor.execute_goto_definition.assert_not_called()
        editor.execute_goto_declaration.assert_called_once_with(4, 2)

    def test_goto_implementation_delegates_to_implementation_handler(self):
        """Contract gap: goto_implementation must use its own handler."""
        api, editor = self._api()

        api.goto_implementation(4, 2)

        editor.execute_goto_definition.assert_not_called()
        editor.execute_goto_implementation.assert_called_once_with(4, 2)

    @pytest.mark.parametrize(
        "method_name",
        [
            "goto_usage",
            "goto_reference",
            "find_usages",
            "goto_implementation_file",
        ],
    )
    def test_documented_navigation_methods_exist(self, qapp, method_name):
        """Contract gap: methods documented in editor-model.md are missing."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        assert hasattr(api, method_name), f"EditorAPI.{method_name} is documented but not implemented"


class TestCodeEditorDefinitionNavigation:
    """Tests for the real CodeEditor navigation pipeline."""

    @staticmethod
    def _editor_with_provider(provider):
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)
        editor.setText("value = call()\n")
        editor.current_file_path = "/workspace/test.py"
        editor.current_provider = provider
        return editor

    def test_definition_navigation_calls_provider_and_navigates(self, qapp):
        """A single definition target is opened at the returned line."""
        provider = MagicMock()
        provider.has_folding.return_value = False
        provider.has_diagnostics.return_value = False
        provider.get_definition_location.return_value = [("/workspace/other.py", 7, 3)]

        editor = self._editor_with_provider(provider)
        editor._request_async_navigation = MagicMock(return_value=False)
        editor._navigate_to_targets = MagicMock()

        editor.execute_goto_definition(2, 5)

        called_args = provider.get_definition_location.call_args
        # First attempt uses the extended signature; TypeError triggers the
        # three-argument fallback, but a MagicMock accepts any signature.
        assert called_args.args[1:3] == (2, 5)
        editor._navigate_to_targets.assert_called_once_with(
            [("/workspace/other.py", 7, 3)], 2, "/workspace/test.py"
        )

    def test_definition_navigation_without_provider_is_noop(self, qapp):
        """No provider means no navigation attempt."""
        editor = self._editor_with_provider(None)
        editor._request_async_navigation = MagicMock(return_value=False)
        editor._navigate_to_targets = MagicMock()

        editor.execute_goto_definition(0, 0)

        editor._navigate_to_targets.assert_not_called()

    def test_definition_navigation_without_targets_shows_failure(self, qapp):
        """An empty provider result triggers the failure notification path."""
        provider = MagicMock()
        provider.get_definition_location.return_value = None

        editor = self._editor_with_provider(provider)
        editor._request_async_navigation = MagicMock(return_value=False)
        editor._show_navigation_failure = MagicMock()

        editor.execute_goto_definition(0, 0)

        editor._show_navigation_failure.assert_called_once()

    def test_single_target_opens_file_at_line(self, qapp):
        """_navigate_to_targets asks the tab container to open the target."""
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)
        editor.setText("line\n" * 10)
        editor._parent = MagicMock()
        editor._parent.currentWidget.return_value = editor

        editor._navigate_to_targets([("/workspace/other.py", 7, 3)], 0, "/workspace/test.py")

        editor._parent.open_file_at_line.assert_called_once_with("/workspace/other.py", 7)
        assert editor.getCursorPosition() == (7, 3)

    def test_same_file_same_line_target_is_ignored(self, qapp):
        """Navigating to the current line is a no-op."""
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)
        editor._parent = MagicMock()

        editor._navigate_to_targets([("/workspace/test.py", 4, 0)], 4, "/workspace/test.py")

        editor._parent.open_file_at_line.assert_not_called()


class TestLanguageRegistry:
    """Tests for language registration and extension resolution."""

    @staticmethod
    def _config(lang="testnav", extension=".testnav"):
        return {
            "lang": lang,
            "extensions": [extension.lstrip(".")],
            "styles": {"keyword": "#ffffff"},
            "keywords": {"keyword": ["def"]},
        }

    def test_extension_resolves_to_registered_language(self):
        """Registered extensions resolve to their language identifier."""
        from editor.Ironica.language_engine import LanguageRegistry

        assert LanguageRegistry.register_language_dict(self._config())
        try:
            assert LanguageRegistry.get_language_by_extension(".testnav") == "testnav"
            assert LanguageRegistry.get_language_for_file("/tmp/file.testnav") == "testnav"
        finally:
            LanguageRegistry.unregister_language("testnav")

    def test_filenames_take_precedence_over_extensions(self):
        """Exact filename mappings win over extension mappings."""
        from editor.Ironica.language_engine import LanguageRegistry

        config = self._config(lang="testfile", extension=".testfile")
        config["filenames"] = ["Special.testfile"]
        assert LanguageRegistry.register_language_dict(config)
        try:
            assert LanguageRegistry.get_language_for_file("/tmp/special.testfile") == "testfile"
        finally:
            LanguageRegistry.unregister_language("testfile")

    def test_invalid_config_is_rejected(self):
        """A config without extensions/styles is rejected."""
        from editor.Ironica.language_engine import LanguageRegistry

        assert LanguageRegistry.register_language_dict({"lang": "broken"}) is False
        assert LanguageRegistry.is_registered("broken") is False

    def test_provider_is_bound_to_language(self):
        """register_language_dict binds the supplied provider instance."""
        from editor.Ironica.language_engine import (
            BaseLanguageProvider,
            LanguageRegistry,
        )

        class Provider(BaseLanguageProvider):
            def get_hover_hint(self, text, line, col):
                return None

            def get_definition_location(self, text, line, col):
                return None

            def format_source(self, source_code):
                return source_code

        provider = Provider()
        assert LanguageRegistry.register_language_dict(
            self._config(lang="testprovider", extension=".testprovider"),
            provider_instance=provider,
        )
        try:
            assert LanguageRegistry.get_provider("testprovider") is provider
        finally:
            LanguageRegistry.unregister_language("testprovider")


class TestBaseLanguageProvider:
    """Tests for the BaseLanguageProvider contract."""

    def test_abstract_methods_are_required(self):
        """A provider missing abstract methods cannot be instantiated."""
        from editor.Ironica.language_engine import BaseLanguageProvider

        class IncompleteProvider(BaseLanguageProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_minimal_provider_implements_required_surface(self):
        """Three abstract methods are sufficient."""
        from editor.Ironica.language_engine import BaseLanguageProvider

        class MinimalProvider(BaseLanguageProvider):
            def get_hover_hint(self, text, line, col):
                return "Hint"

            def get_definition_location(self, text, line, col):
                return ("file.py", 1, 1)

            def format_source(self, source_code):
                return source_code

        provider = MinimalProvider()

        assert provider.get_hover_hint("", 0, 0) == "Hint"
        assert provider.get_definition_location("", 0, 0) == ("file.py", 1, 1)
        assert provider.format_source("code") == "code"

    def test_optional_methods_have_safe_defaults(self):
        """Optional navigation/diagnostic hooks default to empty values."""
        from editor.Ironica.language_engine import BaseLanguageProvider

        class MinimalProvider(BaseLanguageProvider):
            def get_hover_hint(self, text, line, col):
                return None

            def get_definition_location(self, text, line, col):
                return None

            def format_source(self, source_code):
                return source_code

        provider = MinimalProvider()

        assert provider.get_hover_display("", 0, 0) is None
        assert provider.get_declaration_location("", 0, 0) == []
        assert provider.get_implementation_location("", 0, 0) == []
        assert provider.get_references("", 0, 0) == []
        assert provider.get_semantic_highlights("") is None
        assert provider.has_folding() is False
        assert provider.get_fold_regions("") == []
        assert provider.has_diagnostics() is False
        assert provider.create_diagnostic_manager(None, "", None) is None
        assert provider.has_outline() is False
        assert provider.get_outline("") is None
        assert provider.post_fold_setup(None, []) is None


class TestOutlinePanel:
    """Tests for outline parser registration and building."""

    def test_build_outline_uses_registered_parser(self):
        """build_outline delegates to the parser and fills the root name."""
        from editor.utils.file_properties.outline import (
            OutlineNode,
            OutlineResult,
            SymbolKind,
            build_outline,
            register_parser,
            unregister_parser,
        )

        def parser(source):
            return OutlineResult(
                root=OutlineNode(
                    name="",
                    kind=SymbolKind.FILE,
                    children=[OutlineNode(name="function", kind=SymbolKind.FUNCTION)],
                ),
                language="testoutline",
            )

        register_parser("testoutline", parser)
        try:
            result = build_outline("def function(): pass", "testoutline", "test.py")

            assert result is not None
            assert result.root.name == "test.py"
            assert result.root.children[0].kind is SymbolKind.FUNCTION
        finally:
            unregister_parser("testoutline")

    def test_build_outline_without_parser_returns_none(self):
        """Unknown languages produce no outline."""
        from editor.utils.file_properties.outline import build_outline

        assert build_outline("text", "unknown-language-xyz") is None

    def test_unregister_parser(self):
        """unregister_parser removes a previously registered parser."""
        from editor.utils.file_properties.outline import (
            get_parser,
            register_parser,
            unregister_parser,
        )

        def parser(source):
            return None

        register_parser("testoutline2", parser)
        assert get_parser("testoutline2") is parser

        assert unregister_parser("testoutline2") is True
        assert get_parser("testoutline2") is None

    def test_symbol_kind_enum_values(self):
        """SymbolKind exposes the documented symbol categories."""
        from editor.utils.file_properties.outline import SymbolKind

        assert SymbolKind.FUNCTION.value == "function"
        assert SymbolKind.CLASS.value == "class"
        assert SymbolKind.METHOD.value == "method"
        assert SymbolKind.VARIABLE.value == "variable"
        assert SymbolKind.MODULE.value == "module"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
