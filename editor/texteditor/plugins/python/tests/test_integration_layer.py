"""
Integration tests for the Python plugin ↔ editor integration layer.

Covers:
- Integration layer initialization and lifecycle
- Context builder coordinate translation
- Result translator conversions
- All plugin features wired through the integration layer
- Error isolation
- Registration lifecycle

Run with: pytest test_integration_layer.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from editor.texteditor.plugins.python.domain_models import (
    PythonContext,
    CompletionItem,
    HoverDetails,
    ParameterInfo,
    DefinitionLocation,
    ReferenceLocation,
    RefactorChange,
    ComplexityReport,
    FunctionComplexity,
)
from editor.texteditor.plugins.python.editor_integration import (
    PythonIntegrationLayer,
    ContextBuilder,
    ResultTranslator,
    EditorPluginState,
)
from editor.texteditor.plugins.python.provider import PythonLanguageProvider
from editor.texteditor.plugins.python.jedi_adapter import JediAdapter
from editor.texteditor.plugins.python.cache import LanguageCache
from editor.texteditor.plugins.python.interfaces import IJediAdapter


# ======================================================================
# ContextBuilder tests
# ======================================================================


class TestContextBuilder:
    """Tests for coordinate translation and validation."""

    def test_build_converts_line_to_jedi_1_indexed(self):
        ctx = ContextBuilder.build("hello\nworld", line=0, col=0)
        assert ctx.line == 1

    def test_build_converts_line_1_to_jedi_2(self):
        ctx = ContextBuilder.build("hello\nworld", line=1, col=0)
        assert ctx.line == 2

    def test_build_preserves_column(self):
        ctx = ContextBuilder.build("hello world", line=0, col=5)
        assert ctx.column == 5

    def test_build_includes_file_path(self):
        ctx = ContextBuilder.build("x=1", line=0, col=0, file_path="/a/b.py")
        assert ctx.file_path == "/a/b.py"

    def test_build_no_file_path(self):
        ctx = ContextBuilder.build("x=1", line=0, col=0)
        assert ctx.file_path is None

    def test_build_clamps_negative_line(self):
        ctx = ContextBuilder.build("hello", line=-5, col=0)
        assert ctx.line == 1

    def test_build_clamps_negative_column(self):
        ctx = ContextBuilder.build("hello", line=0, col=-3)
        assert ctx.column == 0

    def test_build_empty_text(self):
        ctx = ContextBuilder.build("", line=0, col=0)
        assert ctx.source_code == ""
        assert ctx.line == 1

    def test_validate_position_in_range(self):
        line, col = ContextBuilder.validate_position("hello\nworld", 1, 3)
        assert line == 1
        assert col == 3

    def test_validate_position_clamps_line(self):
        line, col = ContextBuilder.validate_position("hello\nworld", 99, 0)
        assert line == 1

    def test_validate_position_clamps_column(self):
        line, col = ContextBuilder.validate_position("hello", 0, 99)
        assert col == 5

    def test_validate_position_empty_text(self):
        line, col = ContextBuilder.validate_position("", 0, 0)
        assert line == 0
        assert col == 0


# ======================================================================
# ResultTranslator tests
# ======================================================================


class TestResultTranslator:
    """Tests for domain model → editor format conversion."""

    def test_completions_to_strings(self):
        items = [
            CompletionItem(label="foo", insert_text="foo", kind="function"),
            CompletionItem(label="bar", insert_text="bar", kind="variable"),
        ]
        result = ResultTranslator.completions_to_strings(items)
        assert result == ["foo", "bar"]

    def test_completions_to_strings_empty(self):
        assert ResultTranslator.completions_to_strings([]) == []

    def test_hover_to_tooltip_full(self):
        details = HoverDetails(
            name="my_func",
            kind="function",
            signature="def my_func(x: int) -> str",
            parameters=[ParameterInfo(name="x", type_hint="int")],
            return_type="str",
            docstring="Converts x to string.",
        )
        tooltip = ResultTranslator.hover_to_tooltip(details)
        assert "function" in tooltip
        assert "my_func" in tooltip
        assert "x" in tooltip
        assert "str" in tooltip
        assert "Converts x to string." in tooltip

    def test_hover_to_tooltip_none(self):
        assert ResultTranslator.hover_to_tooltip(None) is None

    def test_hover_to_tooltip_minimal(self):
        details = HoverDetails(
            name="x", kind="variable", signature="x: int"
        )
        tooltip = ResultTranslator.hover_to_tooltip(details)
        assert "x" in tooltip
        assert "int" in tooltip

    def test_definition_to_tuple(self):
        loc = DefinitionLocation(file_path="/a.py", line=10, column=5)
        result = ResultTranslator.definition_to_tuple(loc)
        assert result == ("/a.py", 10, 5)

    def test_definition_to_tuple_none(self):
        assert ResultTranslator.definition_to_tuple(None) is None

    def test_references_to_list(self):
        refs = [
            ReferenceLocation(
                file_path="/a.py",
                line=5,
                column=0,
                context_line="x = foo()",
                symbol_length=3,
            ),
        ]
        result = ResultTranslator.references_to_list(refs)
        assert len(result) == 1
        assert result[0]["file_path"] == "/a.py"
        assert result[0]["line"] == 5
        assert result[0]["symbol_length"] == 3

    def test_references_to_list_empty(self):
        assert ResultTranslator.references_to_list([]) == []


# ======================================================================
# PythonIntegrationLayer tests
# ======================================================================


class TestPythonIntegrationLayerLifecycle:
    """Tests for initialization, shutdown, and singleton behavior."""

    def setup_method(self):
        PythonIntegrationLayer.reset_instance()

    def teardown_method(self):
        PythonIntegrationLayer.reset_instance()

    def test_singleton_returns_same_instance(self):
        a = PythonIntegrationLayer.get_instance()
        b = PythonIntegrationLayer.get_instance()
        assert a is b

    def test_reset_instance_creates_new(self):
        a = PythonIntegrationLayer.get_instance()
        PythonIntegrationLayer.reset_instance()
        b = PythonIntegrationLayer.get_instance()
        assert a is not b

    def test_initialize_returns_true(self):
        layer = PythonIntegrationLayer.get_instance()
        result = layer.initialize()
        assert result is True

    def test_initialize_creates_provider(self):
        layer = PythonIntegrationLayer.get_instance()
        layer.initialize()
        assert layer.provider is not None

    def test_shutdown_clears_state(self):
        layer = PythonIntegrationLayer.get_instance()
        layer.initialize()
        layer.shutdown()
        assert layer._initialized is False


class TestPythonIntegrationLayerCompletions:
    """Tests for completion features through the integration layer."""

    def setup_method(self):
        PythonIntegrationLayer.reset_instance()
        self.layer = PythonIntegrationLayer.get_instance()
        self.layer.initialize()

    def teardown_method(self):
        PythonIntegrationLayer.reset_instance()

    def test_completions_basic(self):
        code = "text = 'hello'\ntext.up"
        result = self.layer.get_completions(code, 1, 5)
        assert isinstance(result, list)
        assert len(result) > 0
        assert "upper" in result

    def test_completions_empty_code(self):
        result = self.layer.get_completions("", 0, 0)
        assert result == []

    def test_completions_no_crash_on_bad_position(self):
        result = self.layer.get_completions("import os", 999, 999)
        assert isinstance(result, list)

    def test_completions_no_provider(self):
        PythonIntegrationLayer.reset_instance()
        layer = PythonIntegrationLayer()
        result = layer.get_completions("x=1", 0, 0)
        assert result == []


class TestPythonIntegrationLayerHover:
    """Tests for hover features through the integration layer."""

    def setup_method(self):
        PythonIntegrationLayer.reset_instance()
        self.layer = PythonIntegrationLayer.get_instance()
        self.layer.initialize()

    def teardown_method(self):
        PythonIntegrationLayer.reset_instance()

    def test_hover_returns_string(self):
        code = "def calc(a: int) -> int:\n    return a"
        result = self.layer.get_hover(code, 0, 4)
        assert result is not None
        assert "calc" in result

    def test_hover_returns_none_for_empty(self):
        result = self.layer.get_hover("", 0, 0)
        assert result is None

    def test_hover_no_crash_on_bad_position(self):
        result = self.layer.get_hover("import os", 999, 999)
        assert isinstance(result, (str, type(None)))

    def test_hover_html(self):
        code = "def calc(a: int) -> int:\n    return a"
        result = self.layer.get_hover_html(code, 0, 4)
        if result is not None:
            assert "calc" in result
            assert "<" in result  # HTML tags present

    def test_hover_no_provider(self):
        PythonIntegrationLayer.reset_instance()
        layer = PythonIntegrationLayer()
        result = layer.get_hover("x=1", 0, 0)
        assert result is None


class TestPythonIntegrationLayerDefinition:
    """Tests for go-to-definition through the integration layer."""

    def setup_method(self):
        PythonIntegrationLayer.reset_instance()
        self.layer = PythonIntegrationLayer.get_instance()
        self.layer.initialize()

    def teardown_method(self):
        PythonIntegrationLayer.reset_instance()

    def test_definition_returns_tuple(self):
        code = "x = 42\nprint(x)"
        result = self.layer.get_definition(code, 1, 6)
        if result is not None:
            assert isinstance(result, tuple)
            assert len(result) == 3

    def test_definition_no_crash_on_bad_position(self):
        result = self.layer.get_definition("import os", 999, 999)
        assert result is None or isinstance(result, tuple)


class TestPythonIntegrationLayerReferences:
    """Tests for find-references through the integration layer."""

    def setup_method(self):
        PythonIntegrationLayer.reset_instance()
        self.layer = PythonIntegrationLayer.get_instance()
        self.layer.initialize()

    def teardown_method(self):
        PythonIntegrationLayer.reset_instance()

    def test_references_returns_list(self):
        code = "def foo(): pass\nfoo()\nfoo()"
        result = self.layer.get_references(code, 0, 4)
        assert isinstance(result, list)

    def test_references_no_crash_on_bad_position(self):
        result = self.layer.get_references("import os", 999, 999)
        assert isinstance(result, list)


class TestPythonIntegrationLayerRename:
    """Tests for rename refactoring through the integration layer."""

    def setup_method(self):
        PythonIntegrationLayer.reset_instance()
        self.layer = PythonIntegrationLayer.get_instance()
        self.layer.initialize()

    def teardown_method(self):
        PythonIntegrationLayer.reset_instance()

    def test_rename_returns_list(self):
        code = "def foo(): pass\nfoo()"
        result = self.layer.get_rename_changes(code, 0, 4, "bar")
        assert isinstance(result, list)

    def test_rename_no_crash_on_bad_position(self):
        result = self.layer.get_rename_changes("import os", 999, 999, "new_name")
        assert isinstance(result, list)


class TestPythonIntegrationLayerComplexity:
    """Tests for complexity analysis through the integration layer."""

    def setup_method(self):
        PythonIntegrationLayer.reset_instance()
        self.layer = PythonIntegrationLayer.get_instance()
        self.layer.initialize()

    def teardown_method(self):
        PythonIntegrationLayer.reset_instance()

    def test_complexity_returns_dict(self):
        code = (
            "def evaluate_val(x):\n"
            "    if x > 10:\n"
            "        return 'high'\n"
            "    return 'low'\n"
        )
        result = self.layer.get_complexity(code)
        assert result is not None
        assert "total_loc" in result
        assert "function_count" in result
        assert "max_cyclomatic_complexity" in result
        assert result["function_count"] == 1

    def test_complexity_empty_source(self):
        result = self.layer.get_complexity("")
        assert result is not None
        assert result["total_loc"] == 0

    def test_complexity_no_provider(self):
        PythonIntegrationLayer.reset_instance()
        layer = PythonIntegrationLayer()
        result = layer.get_complexity("x = 1")
        assert result is None


class TestPythonIntegrationLayerErrorIsolation:
    """Tests that plugin errors never crash the integration layer."""

    def setup_method(self):
        PythonIntegrationLayer.reset_instance()
        self.layer = PythonIntegrationLayer.get_instance()
        self.layer.initialize()

    def teardown_method(self):
        PythonIntegrationLayer.reset_instance()

    def test_completions_with_broken_adapter(self):
        mock_adapter = Mock(spec=IJediAdapter)
        mock_adapter.get_completions.side_effect = RuntimeError("Jedi broke")
        self.layer._adapter = mock_adapter
        self.layer._provider = PythonLanguageProvider(
            adapter=mock_adapter, cache=LanguageCache()
        )
        result = self.layer.get_completions("x=1", 0, 0)
        assert result == []

    def test_hover_with_broken_adapter(self):
        mock_adapter = Mock(spec=IJediAdapter)
        mock_adapter.get_hover.side_effect = RuntimeError("Jedi broke")
        self.layer._adapter = mock_adapter
        self.layer._provider = PythonLanguageProvider(
            adapter=mock_adapter, cache=LanguageCache()
        )
        result = self.layer.get_hover("x=1", 0, 0)
        assert result is None

    def test_definition_with_broken_adapter(self):
        mock_adapter = Mock(spec=IJediAdapter)
        mock_adapter.get_definition.side_effect = RuntimeError("Jedi broke")
        self.layer._adapter = mock_adapter
        self.layer._provider = PythonLanguageProvider(
            adapter=mock_adapter, cache=LanguageCache()
        )
        result = self.layer.get_definition("x=1", 0, 0)
        assert result is None

    def test_references_with_broken_adapter(self):
        mock_adapter = Mock(spec=IJediAdapter)
        mock_adapter.get_references.side_effect = RuntimeError("Jedi broke")
        self.layer._adapter = mock_adapter
        self.layer._provider = PythonLanguageProvider(
            adapter=mock_adapter, cache=LanguageCache()
        )
        result = self.layer.get_references("x=1", 0, 0)
        assert result == []

    def test_rename_with_broken_adapter(self):
        mock_adapter = Mock(spec=IJediAdapter)
        mock_adapter.get_rename_changes.side_effect = RuntimeError("Jedi broke")
        self.layer._adapter = mock_adapter
        self.layer._provider = PythonLanguageProvider(
            adapter=mock_adapter, cache=LanguageCache()
        )
        result = self.layer.get_rename_changes("x=1", 0, 0, "y")
        assert result == []


class TestEditorPluginState:
    """Tests for per-editor plugin state."""

    def test_state_holds_provider_reference(self):
        adapter = JediAdapter()
        cache = LanguageCache()
        provider = PythonLanguageProvider(adapter=adapter, cache=cache)
        state = EditorPluginState(provider)
        assert state.provider is provider
        assert state.cache is cache
        assert state.last_hover_details is None


class TestProviderCoordinateConversion:
    """Tests that the provider correctly translates 0-indexed to 1-indexed."""

    def test_provider_adds_one_to_line(self):
        adapter = Mock(spec=IJediAdapter)
        adapter.get_completions.return_value = []
        cache = LanguageCache()
        provider = PythonLanguageProvider(adapter=adapter, cache=cache)

        provider.get_auto_completions("hello\nworld", line=0, col=0)

        call_args = adapter.get_completions.call_args
        ctx = call_args[0][0]
        assert ctx.line == 1  # 0-indexed 0 → 1-indexed 1

    def test_provider_line_1_becomes_2(self):
        adapter = Mock(spec=IJediAdapter)
        adapter.get_completions.return_value = []
        cache = LanguageCache()
        provider = PythonLanguageProvider(adapter=adapter, cache=cache)

        provider.get_auto_completions("hello\nworld", line=1, col=0)

        call_args = adapter.get_completions.call_args
        ctx = call_args[0][0]
        assert ctx.line == 2

    def test_provider_passes_file_path(self):
        adapter = Mock(spec=IJediAdapter)
        adapter.get_completions.return_value = []
        cache = LanguageCache()
        provider = PythonLanguageProvider(adapter=adapter, cache=cache, file_path="/a/b.py")

        provider.get_auto_completions("x=1", line=0, col=0)

        call_args = adapter.get_completions.call_args
        ctx = call_args[0][0]
        assert ctx.file_path == "/a/b.py"

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
