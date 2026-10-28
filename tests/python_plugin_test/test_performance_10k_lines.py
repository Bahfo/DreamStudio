"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Wall-clock performance coverage for the Python plugin on files above 10,000
lines.

These tests never assert pass/fail on elapsed time. They validate that each
service still produces correct results on a large buffer and record samples
through the suite's ``timing_recorder``; pytest prints median/min/max values
in the terminal summary.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from editor.Ironica import analysis_server
from editor.Ironica.plugins.python.cache import LanguageCache
from editor.Ironica.plugins.python.domain_models import (
    CompletionDetails,
    DefinitionLocation,
    HoverDetails,
    PythonContext,
)
from editor.Ironica.plugins.python.folding import compute_fold_regions
from editor.Ironica.plugins.python.jedi_adapter import JediAdapter
from editor.Ironica.plugins.python.jedi_worker import _syntax_diagnostics
from editor.Ironica.plugins.python.outline_parser import parse_python_outline
from editor.Ironica.plugins.python.provider import PythonLanguageProvider
from editor.Ironica.plugins.python.semantic_highlights import PythonSemanticProvider
from editor.utils.file_properties.outline import SymbolKind
from tests.python_plugin_test.helpers import build_large_python_module

pytestmark = [pytest.mark.performance, pytest.mark.slow]

_EXPECTED_CLASSES = 60
_EXPECTED_METHODS = 60 * 24


@pytest.fixture(scope="module")
def large_file(tmp_path_factory) -> SimpleNamespace:
    """Build a >10k-line module plus valid/invalid variants on disk.

    Each Jedi benchmark receives its own file path so the first measured call
    includes Jedi's cold parse of the large buffer.
    """
    workdir = tmp_path_factory.mktemp("python_plugin_performance")
    source = build_large_python_module()
    line_count = len(source.splitlines())
    assert line_count > 10_000

    call_source = source + "\ncall_result = Widget0().method_0()\n"
    call_lines = call_source.splitlines()
    call_line = next(
        index
        for index, line in enumerate(call_lines, start=1)
        if line.startswith("call_result")
    )
    call_column = call_lines[call_line - 1].index("method_0") + 3
    call_path = workdir / "large_valid_call.py"
    call_path.write_text(call_source, encoding="utf-8")

    completion_source = source + "\ncompletion_result = Widget0().method_\n"
    completion_lines = completion_source.splitlines()
    completion_line = len(completion_lines)
    completion_column = len(completion_lines[-1])
    completion_path = workdir / "large_completion.py"
    completion_path.write_text(completion_source, encoding="utf-8")

    cache_source = source + "\ncache_result = Widget0().method_0()\n"
    cache_lines = cache_source.splitlines()
    cache_line = next(
        index
        for index, line in enumerate(cache_lines, start=1)
        if line.startswith("cache_result")
    )
    cache_column = cache_lines[cache_line - 1].index("method_0") + 3
    cache_path = workdir / "large_cache.py"
    cache_path.write_text(cache_source, encoding="utf-8")

    method_line = next(
        index
        for index, line in enumerate(source.splitlines(), start=1)
        if line.strip().startswith("def method_0")
    )

    return SimpleNamespace(
        source=source,
        line_count=line_count,
        method_line=method_line,
        call_source=call_source,
        call_line=call_line,
        call_column=call_column,
        call_path=call_path,
        completion_source=completion_source,
        completion_line=completion_line,
        completion_column=completion_column,
        completion_path=completion_path,
        cache_source=cache_source,
        cache_line=cache_line,
        cache_column=cache_column,
        cache_path=cache_path,
        detail=f"{line_count:,} lines, {_EXPECTED_CLASSES} classes",
    )


class TestLargeFilePremise:
    """Sanity checks for the synthetic 10k-line fixture itself."""

    def test_fixture_exceeds_ten_thousand_lines(self, large_file):
        """Every benchmark operates on a file larger than 10,000 lines."""
        assert large_file.line_count > 10_000
        assert large_file.source.count("\nclass Widget") == _EXPECTED_CLASSES
        assert large_file.source.count("    def method_") == _EXPECTED_METHODS
        assert large_file.call_path.is_file()
        assert large_file.completion_path.is_file()


class TestOutlinePerformance:
    """Timing for AST-backed outline construction on a large module."""

    def test_outline_parsing(self, timing_recorder, large_file):
        """Outline parsing stays linear in file size with annotated symbols."""
        result = timing_recorder.time_call(
            "outline",
            "parse",
            lambda: parse_python_outline(large_file.source),
            repeats=3,
            detail=large_file.detail,
        )

        classes = [
            child for child in result.root.children if child.kind is SymbolKind.CLASS
        ]
        assert result.language == "python"
        assert len(classes) == _EXPECTED_CLASSES
        assert sum(len(node.children) for node in classes) == _EXPECTED_METHODS
        assert any(child.kind is SymbolKind.IMPORT for child in result.root.children)


class TestSemanticHighlightPerformance:
    """Timing for the lexical and AST semantic-highlight pipelines."""

    def test_cold_pipeline(self, timing_recorder, large_file):
        """A fresh provider parses and classifies the entire buffer."""
        ranges = timing_recorder.time_call(
            "semantic_highlights",
            "cold",
            lambda: PythonSemanticProvider().get_semantic_ranges(large_file.source),
            repeats=2,
            detail=large_file.detail,
        )

        encoded_length = len(large_file.source.encode("utf-8"))
        assert ranges
        assert ranges == sorted(ranges, key=lambda item: item[0])
        assert all(
            start >= 0 and length > 0 and start + length <= encoded_length
            for start, length, _colour in ranges
        )
        assert all(
            colour.startswith("#") and len(colour) == 7
            for _start, _length, colour in ranges
        )

    def test_cached_pipeline(self, timing_recorder, large_file):
        """Repeated highlight requests reuse the provider's token cache."""
        provider = PythonSemanticProvider()
        cold = provider.get_semantic_ranges(large_file.source)

        cached = timing_recorder.time_call(
            "semantic_highlights",
            "cached",
            lambda: provider.get_semantic_ranges(large_file.source),
            repeats=5,
            detail=large_file.detail,
        )

        assert cached == cold


class TestFoldingPerformance:
    """Timing for indentation-based fold-region computation."""

    def test_fold_regions(self, timing_recorder, large_file):
        """Every class, method, and import group is discovered."""
        regions = timing_recorder.time_call(
            "folding",
            "compute",
            lambda: compute_fold_regions(large_file.source),
            repeats=3,
            detail=large_file.detail,
        )

        kinds = [region.kind for region in regions]
        assert kinds.count("class") == _EXPECTED_CLASSES
        assert kinds.count("function") == _EXPECTED_METHODS
        assert kinds.count("import") == 1
        assert len(regions) == _EXPECTED_CLASSES + _EXPECTED_METHODS + 1
        assert all(region.start_line <= region.end_line for region in regions)
        assert len({region.uid for region in regions}) == len(regions)


class TestDiagnosticsPerformance:
    """Timing for in-process syntax diagnostics on large buffers."""

    def test_valid_file_has_no_diagnostics(self, timing_recorder, large_file):
        """A compilable 10k-line buffer produces no syntax errors."""
        diagnostics = timing_recorder.time_call(
            "diagnostics",
            "valid",
            lambda: _syntax_diagnostics(large_file.source),
            repeats=3,
            detail=large_file.detail,
        )

        assert diagnostics == []

    def test_invalid_file_degrades_to_a_located_error(
        self, timing_recorder, large_file
    ):
        """A late syntax error is recovered without scanning past the buffer."""
        broken = large_file.source + "def broken(:\n    pass\n"

        diagnostics = timing_recorder.time_call(
            "diagnostics",
            "invalid",
            lambda: _syntax_diagnostics(broken),
            repeats=2,
            detail=large_file.detail,
        )

        assert diagnostics
        assert diagnostics[0]["line"] == large_file.line_count + 1
        assert diagnostics[0]["message"] == "invalid syntax"
        assert all(
            diagnostic["line"] >= large_file.line_count for diagnostic in diagnostics
        )


class TestAnalysisServerPerformance:
    """Timing for the subprocess-side whole-document analysis request."""

    def test_analysis_request_cold_and_cached(self, timing_recorder, large_file):
        """The server returns highlights and folds on cold and cached calls."""
        request = (
            "analysis",
            101,
            large_file.source,
            None,
            "",
            None,
        )

        cold = timing_recorder.time_call(
            "analysis_server",
            "analysis_cold",
            lambda: analysis_server.handle_request(request),
            repeats=1,
            detail=large_file.detail,
        )
        cached = timing_recorder.time_call(
            "analysis_server",
            "analysis_cached",
            lambda: analysis_server.handle_request(request),
            repeats=3,
            detail=large_file.detail,
        )

        assert cold == cached
        kind, request_id, highlights, folds = cold
        assert (kind, request_id) == ("analysis", 101)
        assert highlights
        assert len(folds) == _EXPECTED_CLASSES + _EXPECTED_METHODS + 1


class TestJediPerformance:
    """Timing for real Jedi calls against a 10k-line module."""

    def test_hover(self, timing_recorder, large_file):
        """The first hover includes Jedi's cold parse of the buffer."""
        adapter = JediAdapter()
        context = PythonContext(
            large_file.call_source,
            large_file.call_line,
            large_file.call_column,
            str(large_file.call_path),
        )

        details = timing_recorder.time_call(
            "jedi",
            "hover",
            lambda: adapter.get_hover(context),
            repeats=3,
            detail=large_file.detail,
        )

        assert isinstance(details, HoverDetails)
        assert details.name == "method_0"
        assert details.kind == "function"
        assert "value" in [parameter.name for parameter in details.parameters]
        assert details.docstring is not None
        assert "Method 0 of widget 0." in details.docstring

    def test_definition(self, timing_recorder, large_file):
        """Go-to-definition resolves a call inside the large module."""
        adapter = JediAdapter()
        context = PythonContext(
            large_file.call_source,
            large_file.call_line,
            large_file.call_column,
            str(large_file.call_path),
        )

        location = timing_recorder.time_call(
            "jedi",
            "definition",
            lambda: adapter.get_definition(context),
            repeats=3,
            detail=large_file.detail,
        )

        assert isinstance(location, DefinitionLocation)
        assert location.file_path is not None
        assert large_file.call_path.resolve() == Path(location.file_path).resolve()
        assert 1 <= location.line < large_file.line_count
        assert location.context_line is not None
        assert location.context_line.strip().startswith("def method_0")

    def test_completions(self, timing_recorder, large_file):
        """Attribute completion still enumerates the class methods."""
        adapter = JediAdapter()
        context = PythonContext(
            large_file.completion_source,
            large_file.completion_line,
            large_file.completion_column,
            str(large_file.completion_path),
        )

        results = timing_recorder.time_call(
            "jedi",
            "completions",
            lambda: adapter.get_completions(context),
            repeats=2,
            detail=large_file.detail,
        )

        names = {completion.text for completion in results}
        assert isinstance(results, list)
        assert all(isinstance(completion, CompletionDetails) for completion in results)
        assert {"method_0", "method_1", "method_23"} <= names
        assert all(completion.insert_text == completion.text for completion in results)


class TestProviderCachePerformance:
    """Timing for the provider's definition LRU on a 10k-line buffer."""

    def test_definition_cache_avoids_repeated_jedi_work(
        self, timing_recorder, large_file
    ):
        """Repeated navigation returns the cached tuple without re-invoking Jedi."""
        provider = PythonLanguageProvider(adapter=JediAdapter(), cache=LanguageCache())

        def navigate():
            return provider.get_definition_location(
                large_file.cache_source,
                large_file.cache_line - 1,
                large_file.cache_column,
                file_path=str(large_file.cache_path),
            )

        first = timing_recorder.time_call(
            "provider",
            "definition_uncached",
            navigate,
            repeats=1,
            detail=large_file.detail,
        )
        cached = timing_recorder.time_call(
            "provider",
            "definition_cached",
            navigate,
            repeats=5,
            detail=large_file.detail,
        )

        assert first is not None
        assert first == cached
        path, line, column = first
        assert large_file.cache_path.resolve() == Path(path).resolve()
        assert line == large_file.method_line - 1
        assert column >= 4
