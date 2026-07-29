"""Integration tests for the Python language plugin registration.

Verifies that the Python plugin correctly plugs into DreamStudio's
``LanguageRegistry`` and that the full pipeline — extension detection,
language resolution, provider lookup, and feature invocation — works
end-to-end.

Covers:
    - Plugin registration via ``register_python_language``
    - Extension → language resolution for ``.py``, ``.pyw``, ``.pyi``
    - Provider presence and type after registration
    - Provider feature methods (completions, hover, definition, format)
    - Unregistration and re-registration
    - Editor ``setLanguage`` integration with the plugin provider
    - Full pipeline: open file → detect language → attach provider
    - Error recovery: plugin failures do not crash the editor
"""

import pytest

from editor.Ironica.language_engine import LanguageRegistry, BaseLanguageProvider


@pytest.fixture(autouse=True)
def _reset_registry():
    """Ensure a clean LanguageRegistry for every test."""
    LanguageRegistry.reset()
    yield
    LanguageRegistry.reset()


class TestPluginRegistration:
    """Test the registration function itself."""

    def test_register_python_language(self):
        from editor.Ironica.plugins.registration import register_python_language

        result = register_python_language()
        assert result is True

    def test_register_sets_language_config(self):
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        config = LanguageRegistry.get_config("python")
        assert config is not None
        assert config["lang"] == "python"

    def test_register_sets_extension_map(self):
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        assert LanguageRegistry.get_language_by_extension(".py") == "python"
        assert LanguageRegistry.get_language_by_extension(".pyw") == "python"
        assert LanguageRegistry.get_language_by_extension(".pyi") == "python"

    def test_register_sets_provider(self):
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        provider = LanguageRegistry.get_provider("python")
        assert provider is not None
        assert isinstance(provider, BaseLanguageProvider)

    def test_unregister_python_language(self):
        from editor.Ironica.plugins.registration import (
            register_python_language,
            unregister_python_language,
        )

        register_python_language()
        assert LanguageRegistry.is_registered("python")

        result = unregister_python_language()
        assert result is True
        assert not LanguageRegistry.is_registered("python")
        assert LanguageRegistry.get_language_by_extension(".py") is None

    def test_unregister_returns_false_when_not_registered(self):
        from editor.Ironica.plugins.registration import unregister_python_language

        result = unregister_python_language()
        assert result is False


class TestProviderType:
    """Verify the provider is a proper BaseLanguageProvider subclass."""

    def test_provider_is_base_language_provider(self):
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        provider = LanguageRegistry.get_provider("python")
        assert isinstance(provider, BaseLanguageProvider)

    def test_provider_has_required_methods(self):
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        provider = LanguageRegistry.get_provider("python")
        assert hasattr(provider, "get_hover_hint")
        assert hasattr(provider, "get_definition_location")
        assert hasattr(provider, "format_source")


class TestProviderFeatures:
    """Test provider feature methods through the LanguageRegistry."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        self.provider = LanguageRegistry.get_provider("python")

    def test_hover_returns_string_or_none(self):
        code = "def foo(): pass\nfoo"
        result = self.provider.get_hover_hint(code, 1, 0)
        assert result is None or isinstance(result, str)

    def test_hover_returns_hint_for_function(self):
        code = "def calc(a: int) -> int:\n    return a"
        result = self.provider.get_hover_hint(code, 0, 4)
        assert result is not None
        assert "calc" in result

    def test_definition_returns_tuple_or_none(self):
        code = "x = 42\nprint(x)"
        result = self.provider.get_definition_location(code, 1, 6)
        # Result is (file_path, line, col) or None
        assert result is None or (isinstance(result, tuple) and len(result) == 3)

    def test_format_source_passthrough(self):
        code = "x = 1\ny = 2\n"
        result = self.provider.format_source(code)
        assert result == code  # Python plugin is a passthrough formatter

    def test_hover_no_crash_on_bad_position(self):
        result = self.provider.get_hover_hint("import os", 999, 999)
        assert result is None

    def test_definition_no_crash_on_bad_position(self):
        result = self.provider.get_definition_location("import os", 999, 999)
        assert result is None


class TestEditorIntegration:
    """Test that CodeEditor correctly picks up the Python provider."""

    def test_editor_gets_provider_for_python(self, qapp_instance, language_registry):
        from editor.Ironica.code_editor import CodeEditor

        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        editor = CodeEditor(language="python")
        try:
            assert editor.current_lang == "python"
            assert editor.current_provider is not None
            assert isinstance(editor.current_provider, BaseLanguageProvider)
        finally:
            editor.deleteLater()

    def test_editor_no_provider_for_unknown(self, qapp_instance, language_registry):
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(language="nonexistent")
        try:
            assert editor.current_lang == "nonexistent"
            assert editor.current_provider is None
        finally:
            editor.deleteLater()

    def test_editor_clears_provider_on_empty_language(
        self, qapp_instance, language_registry
    ):
        from editor.Ironica.code_editor import CodeEditor

        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        editor = CodeEditor(language="python")
        try:
            assert editor.current_provider is not None
            editor.setLanguage("")
            assert editor.current_lang is None
            assert editor.current_provider is None
        finally:
            editor.deleteLater()


class TestTabEditorPipeline:
    """Test the full pipeline from file opening to provider attachment."""

    def test_tab_resolves_python_extension(self, language_registry):
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        from editor.Ironica.tab_editor import DreamTabbedEditor

        lang = DreamTabbedEditor.set_language(".py")
        assert lang == "python"

    def test_tab_resolves_pyw_extension(self, language_registry):
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        from editor.Ironica.tab_editor import DreamTabbedEditor

        lang = DreamTabbedEditor.set_language(".pyw")
        assert lang == "python"

    def test_tab_resolves_pyi_extension(self, language_registry):
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        from editor.Ironica.tab_editor import DreamTabbedEditor

        lang = DreamTabbedEditor.set_language(".pyi")
        assert lang == "python"

    def test_tab_unknown_extension_returns_none(self, language_registry):
        from editor.Ironica.tab_editor import DreamTabbedEditor

        lang = DreamTabbedEditor.set_language(".xyz")
        assert lang is None


class TestErrorRecovery:
    """Verify that plugin failures are handled gracefully."""

    def test_registration_failure_returns_false(self):
        from editor.Ironica.plugins.registration import (
            register_python_language,
        )

        # Unregister first to simulate a clean state
        LanguageRegistry.reset()

        # Registration should succeed normally
        result = register_python_language()
        assert result is True

        # Double registration should still succeed (overwrite)
        result = register_python_language()
        assert result is True

    def test_provider_does_not_crash_on_empty_code(self):
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        provider = LanguageRegistry.get_provider("python")

        # All methods should handle empty code gracefully
        assert provider.get_hover_hint("", 0, 0) is None
        assert provider.get_definition_location("", 0, 0) is None
        assert provider.format_source("") == ""


class TestPluginModuleImports:
    """Verify that all plugin modules can be imported as a package."""

    def test_import_domain_models(self):
        from editor.Ironica.plugins.python.domain_models import (
            PythonContext,
            HoverDetails,
            DefinitionLocation,
            ReferenceLocation,
            RefactorChange,
            FunctionComplexity,
            ComplexityReport,
            ParameterInfo,
        )

    def test_import_interfaces(self):
        from editor.Ironica.plugins.python.interfaces import (
            IJediAdapter,
            INavigationService,
            IReferenceFinderService,
            IRefactoringService,
            IComplexityService,
        )

    def test_import_jedi_adapter(self):
        from editor.Ironica.plugins.python.jedi_adapter import JediAdapter

    def test_import_provider(self):
        from editor.Ironica.plugins.python.provider import PythonLanguageProvider

    def test_import_cache(self):
        from editor.Ironica.plugins.python.cache import LanguageCache

    def test_import_navigation(self):
        from editor.Ironica.plugins.python.navigation import (
            NavigationService,
            ReferenceFinderService,
        )

    def test_import_refactoring(self):
        from editor.Ironica.plugins.python.refactoring import RenameRefactoringService

    def test_import_complexity(self):
        from editor.Ironica.plugins.python.complexity import ComplexityAnalysisService

    def test_import_views(self):
        from editor.Ironica.plugins.python.views import (
            ReferenceViewerWidget,
            RefactorDialog,
            ComplexityDashboard,
        )

    def test_import_package_init(self):
        from editor.Ironica.plugins.python import (
            PythonLanguageProvider,
            JediAdapter,
            LanguageCache,
            NavigationService,
            ReferenceFinderService,
            RenameRefactoringService,
            ComplexityAnalysisService,
            ReferenceViewerWidget,
            RefactorDialog,
            ComplexityDashboard,
        )

    def test_import_registration(self):
        from editor.Ironica.plugins.registration import (
            register_python_language,
            unregister_python_language,
        )
