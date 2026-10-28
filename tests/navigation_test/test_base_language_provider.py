"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the BaseLanguageProvider contract.
"""

import pytest


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])