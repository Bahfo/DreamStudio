"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for language registration and extension resolution.
"""

import pytest


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])