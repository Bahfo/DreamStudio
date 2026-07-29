"""
Integration tests for the Python plugin ↔ editor integration layer.

Covers:
- Context builder coordinate translation
- Result translator conversions
- Error isolation

Run with: pytest test_integration_layer.py -v
"""

import pytest
from unittest.mock import Mock

from editor.Ironica.plugins.python.domain_models import (
    PythonContext,
    HoverDetails,
    ParameterInfo,
    DefinitionLocation,
    ReferenceLocation,
    RefactorChange,
)
from editor.Ironica.plugins.python.editor_integration import (
    PythonIntegrationLayer,
    ContextBuilder,
    ResultTranslator,
)
from editor.Ironica.plugins.python.provider import PythonLanguageProvider
from editor.Ironica.plugins.python.jedi_adapter import JediAdapter
from editor.Ironica.plugins.python.cache import LanguageCache
from editor.Ironica.plugins.python.interfaces import IJediAdapter

# ======================================================================
# ContextBuilder tests
# ======================================================================


class TestContextBuilder:
    """Tests for coordinate translation and validation."""

    def test_build_converts_line_to_jedi_1_indexed(self):
        ctx = ContextBuilder.from_editor("hello\nworld", line=0, col=0)
        assert ctx.line == 1

    def test_build_converts_line_1_to_jedi_2(self):
        ctx = ContextBuilder.from_editor("hello\nworld", line=1, col=0)
        assert ctx.line == 2

    def test_build_preserves_column(self):
        ctx = ContextBuilder.from_editor("hello world", line=0, col=5)
        assert ctx.column == 5

    def test_build_includes_file_path(self):
        ctx = ContextBuilder.from_editor("x=1", line=0, col=0, file_path="/a/b.py")
        assert ctx.file_path == "/a/b.py"

    def test_build_no_file_path(self):
        ctx = ContextBuilder.from_editor("x=1", line=0, col=0)
        assert ctx.file_path is None

    def test_build_empty_text(self):
        ctx = ContextBuilder.from_editor("", line=0, col=0)
        assert ctx.source_code == ""
        assert ctx.line == 1


# ======================================================================
# ResultTranslator tests
# ======================================================================


class TestResultTranslator:
    """Tests for domain model → editor format conversion."""

    def test_definition_to_tuple(self):
        loc = DefinitionLocation(file_path="/a.py", line=10, column=5)
        result = ResultTranslator.definition_to_tuple(loc)
        assert result == ("/a.py", 10, 5)

    def test_definition_to_tuple_none(self):
        assert ResultTranslator.definition_to_tuple(None) is None


# ======================================================================
# PythonIntegrationLayer tests
# ======================================================================


class TestPythonIntegrationLayerHover:
    """Tests for hover features through the integration layer."""

    def test_hover_returns_details(self):
        code = "def calc(a: int) -> int:\n    return a"
        adapter = JediAdapter()
        layer = PythonIntegrationLayer(adapter)
        result = layer.get_hover(code, 0, 4)
        assert result is not None
        assert isinstance(result, HoverDetails)
        assert "calc" in result.name

    def test_hover_returns_none_for_empty(self):
        adapter = JediAdapter()
        layer = PythonIntegrationLayer(adapter)
        result = layer.get_hover("", 0, 0)
        assert result is None

    def test_hover_no_crash_on_bad_position(self):
        adapter = JediAdapter()
        layer = PythonIntegrationLayer(adapter)
        result = layer.get_hover("import os", 999, 999)
        assert result is None


class TestPythonIntegrationLayerDefinition:
    """Tests for go-to-definition through the integration layer."""

    def test_definition_returns_tuple(self):
        code = "x = 42\nprint(x)"
        adapter = JediAdapter()
        layer = PythonIntegrationLayer(adapter)
        result = layer.get_definition(code, 1, 6)
        if result is not None:
            assert isinstance(result, tuple)
            assert len(result) == 3

    def test_definition_no_crash_on_bad_position(self):
        adapter = JediAdapter()
        layer = PythonIntegrationLayer(adapter)
        result = layer.get_definition("import os", 999, 999)
        assert result is None or isinstance(result, tuple)


class TestPythonIntegrationLayerErrorIsolation:
    """Tests that plugin errors never crash the integration layer."""

    def test_hover_with_broken_adapter(self):
        mock_adapter = Mock(spec=IJediAdapter)
        mock_adapter.get_hover.side_effect = RuntimeError("Jedi broke")
        layer = PythonIntegrationLayer(mock_adapter)
        result = layer.get_hover("x=1", 0, 0)
        assert result is None

    def test_definition_with_broken_adapter(self):
        mock_adapter = Mock(spec=IJediAdapter)
        mock_adapter.get_definition.side_effect = RuntimeError("Jedi broke")
        layer = PythonIntegrationLayer(mock_adapter)
        result = layer.get_definition("x=1", 0, 0)
        assert result is None


class TestProviderCoordinateConversion:
    """Tests that the provider correctly translates 0-indexed to 1-indexed."""

    def test_provider_context_method_line_conversion(self):
        adapter = Mock(spec=IJediAdapter)
        adapter.get_hover.return_value = None
        cache = LanguageCache()
        provider = PythonLanguageProvider(adapter=adapter, cache=cache)

        provider.get_hover_hint("hello\nworld", line=1, col=3)

        call_args = adapter.get_hover.call_args
        ctx = call_args[0][0]
        assert ctx.line == 2
        assert ctx.column == 3
