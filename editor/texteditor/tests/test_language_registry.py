"""Tests for LanguageRegistry and LanguageLexer (editor/texteditor/language_engine.py).

Covers: valid registration, malformed JSON, duplicate registration,
duplicate extensions, missing provider, invalid provider, provider lookup,
language lookup, configuration lookup.
"""

import json
import pytest


class TestLanguageRegistryRegistration:
    """Test register_language with various inputs."""

    def test_register_valid(self, language_registry, sample_language_json):
        result = language_registry.register_language(sample_language_json)
        assert result is True
        assert language_registry.is_registered("test_lang")

    def test_register_returns_true(self, language_registry, sample_language_json):
        result = language_registry.register_language(sample_language_json)
        assert result is True

    def test_register_malformed_json(self, language_registry, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{invalid json", encoding="utf-8")
        result = language_registry.register_language(str(p))
        assert result is False

    def test_register_missing_lang_key(self, language_registry, tmp_path):
        p = tmp_path / "no_lang.json"
        p.write_text(json.dumps({"extensions": ["x"]}), encoding="utf-8")
        result = language_registry.register_language(str(p))
        assert result is False

    def test_register_nonexistent_file(self, language_registry):
        result = language_registry.register_language("/nonexistent/file.json")
        assert result is False

    def test_register_duplicate_language(self, language_registry, sample_language_json):
        language_registry.register_language(sample_language_json)
        result = language_registry.register_language(sample_language_json)
        # Should succeed (overwrite) but log a warning
        assert result is True

    def test_register_duplicate_extension(self, language_registry, tmp_path):
        config1 = {"lang": "lang_a", "extensions": ["txt"], "styles": {}, "keywords": {}}
        config2 = {"lang": "lang_b", "extensions": ["txt"], "styles": {}, "keywords": {}}

        p1 = tmp_path / "a.json"
        p2 = tmp_path / "b.json"
        p1.write_text(json.dumps(config1), encoding="utf-8")
        p2.write_text(json.dumps(config2), encoding="utf-8")

        language_registry.register_language(str(p1))
        result = language_registry.register_language(str(p2))
        assert result is True
        # lang_b should have taken over the extension
        assert language_registry.get_language_by_extension(".txt") == "lang_b"

    def test_register_empty_extensions_warns(self, language_registry, tmp_path):
        config = {"lang": "no_ext", "extensions": [], "styles": {}, "keywords": {}}
        p = tmp_path / "no_ext.json"
        p.write_text(json.dumps(config), encoding="utf-8")
        result = language_registry.register_language(str(p))
        # Empty extensions is a validation error
        assert result is False

    def test_register_missing_styles_warns(self, language_registry, tmp_path):
        config = {"lang": "no_styles", "extensions": ["ns"], "keywords": {}}
        p = tmp_path / "no_styles.json"
        p.write_text(json.dumps(config), encoding="utf-8")
        result = language_registry.register_language(str(p))
        assert result is False  # missing styles is an error


class TestLanguageRegistryProvider:
    """Test provider registration and lookup."""

    def test_register_with_provider(self, language_registry, sample_language_json):
        from editor.texteditor.language_engine import BaseLanguageProvider

        class DummyProvider(BaseLanguageProvider):
            def get_auto_completions(self, text, line, col):
                return []

            def get_hover_hint(self, text, line, col):
                return None

            def get_definition_location(self, text, line, col):
                return None

            def format_source(self, source_code):
                return source_code

        provider = DummyProvider()
        language_registry.register_language(sample_language_json, provider)
        assert language_registry.get_provider("test_lang") is provider

    def test_register_invalid_provider(self, language_registry, sample_language_json):
        result = language_registry.register_language(
            sample_language_json, provider_instance="not_a_provider"
        )
        assert result is False

    def test_get_provider_unknown_language(self, language_registry):
        assert language_registry.get_provider("nonexistent") is None

    def test_get_provider_no_provider(self, language_registry, sample_language_json):
        language_registry.register_language(sample_language_json)
        assert language_registry.get_provider("test_lang") is None


class TestLanguageRegistryLookup:
    """Test get_language_by_extension, get_config, get_all_extensions."""

    def test_get_language_by_extension(self, language_registry, sample_language_json):
        language_registry.register_language(sample_language_json)
        assert language_registry.get_language_by_extension(".tst") == "test_lang"
        assert language_registry.get_language_by_extension(".test") == "test_lang"

    def test_get_language_by_unknown_extension(self, language_registry):
        assert language_registry.get_language_by_extension(".xyz") is None

    def test_get_config(self, language_registry, sample_language_json):
        language_registry.register_language(sample_language_json)
        config = language_registry.get_config("test_lang")
        assert config is not None
        assert config["lang"] == "test_lang"

    def test_get_config_unknown(self, language_registry):
        assert language_registry.get_config("nonexistent") is None

    def test_get_all_extensions(self, language_registry, sample_language_json):
        language_registry.register_language(sample_language_json)
        exts = language_registry.get_all_extensions()
        assert ".tst" in exts
        assert ".test" in exts
        assert exts[".tst"] == "test_lang"


class TestLanguageRegistryMisc:
    """Test is_registered, list_languages, unregister, reset."""

    def test_is_registered(self, language_registry, sample_language_json):
        assert not language_registry.is_registered("test_lang")
        language_registry.register_language(sample_language_json)
        assert language_registry.is_registered("test_lang")

    def test_list_languages(self, language_registry, sample_language_json):
        language_registry.register_language(sample_language_json)
        langs = language_registry.list_languages()
        assert "test_lang" in langs

    def test_unregister(self, language_registry, sample_language_json):
        language_registry.register_language(sample_language_json)
        assert language_registry.is_registered("test_lang")
        result = language_registry.unregister_language("test_lang")
        assert result is True
        assert not language_registry.is_registered("test_lang")
        assert language_registry.get_language_by_extension(".tst") is None

    def test_unregister_unknown(self, language_registry):
        result = language_registry.unregister_language("nonexistent")
        assert result is False

    def test_reset(self, language_registry, sample_language_json):
        language_registry.register_language(sample_language_json)
        language_registry.reset()
        assert not language_registry.is_registered("test_lang")
        assert language_registry.list_languages() == []


class TestLegacyConfigNormalization:
    """Test conversion from legacy words/colors_schema format."""

    def test_legacy_format(self, language_registry, sample_legacy_json):
        result = language_registry.register_language(sample_legacy_json)
        assert result is True
        config = language_registry.get_config("legacy_lang")
        assert "styles" in config
        assert "keywords" in config
        assert "keyword" in config["styles"]
        assert "string" in config["styles"]

    def test_legacy_keywords_grouped(self, language_registry, sample_legacy_json):
        language_registry.register_language(sample_legacy_json)
        config = language_registry.get_config("legacy_lang")
        assert "if" in config["keywords"]["keyword"]
        assert "else" in config["keywords"]["keyword"]
        assert "hello" in config["keywords"]["string"]


class TestRegisterLanguageDict:
    """Test register_language_dict (in-memory registration)."""

    def test_register_dict(self, language_registry):
        config = {
            "lang": "dict_lang",
            "extensions": ["dl"],
            "styles": {"kw": "#000"},
            "keywords": {"kw": ["foo"]},
        }
        result = language_registry.register_language_dict(config)
        assert result is True
        assert language_registry.is_registered("dict_lang")

    def test_register_dict_invalid(self, language_registry):
        result = language_registry.register_language_dict({})
        assert result is False


class TestLanguageLexer:
    """Test LanguageLexer with a valid config."""

    def test_lexer_creation(self, qapp_instance):
        from editor.texteditor.code_editor import CodeEditor
        from editor.texteditor.language_engine import LanguageLexer

        editor = CodeEditor()
        config = {
            "styles": {"keyword": "#FF0000", "string": "#00FF00"},
            "keywords": {"keyword": ["if", "else"], "string": ["hello"]},
        }
        lexer = LanguageLexer(editor, config)
        assert lexer.description(1) == "keyword"
        assert lexer.description(2) == "string"
        assert lexer.description(999) == ""
        editor._autocomplete_ext.cleanup()
        editor.deleteLater()

    def test_lexer_empty_config(self, qapp_instance):
        from editor.texteditor.code_editor import CodeEditor
        from editor.texteditor.language_engine import LanguageLexer

        editor = CodeEditor()
        lexer = LanguageLexer(editor, {})
        assert lexer.description(0) == ""
        editor._autocomplete_ext.cleanup()
        editor.deleteLater()
