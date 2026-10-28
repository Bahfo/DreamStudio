"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for go-to-definition orchestration and its LRU cache integration.
"""

from __future__ import annotations

import pytest

from editor.Ironica.plugins.python.cache import LanguageCache
from editor.Ironica.plugins.python.domain_models import DefinitionLocation
from editor.Ironica.plugins.python.provider import PythonLanguageProvider
from tests.python_plugin_test.helpers import RecordingAdapter


def _provider(
    location: DefinitionLocation | None = None,
    cache: LanguageCache | None = None,
    error: Exception | None = None,
) -> tuple[PythonLanguageProvider, RecordingAdapter]:
    """Build a provider wired to a deterministic recording adapter."""
    adapter = RecordingAdapter(definition=location, definition_error=error)
    return PythonLanguageProvider(adapter=adapter, cache=cache), adapter


class TestDefinitionLocationTranslation:
    """Tests for converting Jedi's 1-based location into the editor's 0-based row."""

    def test_definition_is_returned_as_editor_tuple(self):
        """The adapter's model becomes ``(path, 0-based line, column)``."""
        provider, _adapter = _provider(
            DefinitionLocation("/tmp/target.py", 12, 4, "def target():")
        )

        result = provider.get_definition_location("call()", 0, 0)

        assert result == ("/tmp/target.py", 11, 4)

    def test_first_line_is_mapped_to_row_zero(self):
        """A definition on line 1 maps to editor row 0, not -1."""
        provider, _adapter = _provider(DefinitionLocation("/tmp/target.py", 1, 0))

        assert provider.get_definition_location("name", 0, 0) == (
            "/tmp/target.py",
            0,
            0,
        )

    def test_missing_path_becomes_empty_string(self):
        """A definition without a module path keeps its coordinates."""
        provider, _adapter = _provider(DefinitionLocation(None, 3, 8))

        assert provider.get_definition_location("builtin", 0, 0) == ("", 2, 8)

    def test_negative_adapter_line_is_clamped_to_zero(self):
        """Defensive clamping keeps the editor row non-negative."""
        provider, _adapter = _provider(DefinitionLocation("/tmp/a.py", 0, 2))

        assert provider.get_definition_location("name", 0, 0) == ("/tmp/a.py", 0, 2)

    def test_adapter_none_yields_none(self):
        """No definition is reported as ``None``."""
        provider, _adapter = _provider(None)

        assert provider.get_definition_location("unknown", 0, 0) is None

    def test_string_coordinates_are_coerced(self):
        """Path-like and string coordinates are normalized to the tuple contract."""
        provider, _adapter = _provider(DefinitionLocation("/tmp/a.py", "7", "3"))  # type: ignore[arg-type]

        assert provider.get_definition_location("name", 0, 0) == ("/tmp/a.py", 6, 3)


class TestDefinitionContext:
    """Tests for the context handed to the adapter."""

    def test_context_uses_one_based_line(self):
        """Editor rows are incremented for Jedi's 1-based line numbering."""
        provider, adapter = _provider(DefinitionLocation("/tmp/a.py", 1, 0))

        provider.get_definition_location("a\nb\nc", 2, 1)

        context = adapter.calls[0][1]
        assert context.source_code == "a\nb\nc"
        assert context.line == 3
        assert context.column == 1

    def test_provider_paths_are_used_by_default(self):
        """Configured provider paths flow into the request context."""
        provider, adapter = _provider(DefinitionLocation("/tmp/a.py", 1, 0))
        provider.file_path = "/tmp/default.py"
        provider.project_root = "/tmp/default-root"

        provider.get_definition_location("name", 0, 0)

        context = adapter.calls[0][1]
        assert context.file_path == "/tmp/default.py"
        assert context.project_root == "/tmp/default-root"

    def test_explicit_paths_override_provider_paths(self):
        """Per-call paths win over provider defaults."""
        provider, adapter = _provider(DefinitionLocation("/tmp/a.py", 1, 0))
        provider.file_path = "/tmp/default.py"
        provider.project_root = "/tmp/default-root"

        provider.get_definition_location(
            "name",
            0,
            0,
            file_path="/tmp/explicit.py",
            project_root="/tmp/explicit-root",
        )

        context = adapter.calls[0][1]
        assert context.file_path == "/tmp/explicit.py"
        assert context.project_root == "/tmp/explicit-root"

    def test_empty_text_is_still_forwarded(self):
        """Definition lookup does not pre-filter empty buffers."""
        provider, adapter = _provider(None)

        assert provider.get_definition_location("", 0, 0) is None
        assert len(adapter.calls) == 1
        assert adapter.calls[0][1].source_code == ""


class TestDefinitionCaching:
    """Tests for the definition-specific LRU cache entries."""

    def test_repeated_request_hits_the_cache(self):
        """A second identical request never reaches the adapter."""
        provider, adapter = _provider(DefinitionLocation("/tmp/a.py", 5, 2))

        first = provider.get_definition_location("call()", 0, 0)
        second = provider.get_definition_location("call()", 0, 0)

        assert first == second == ("/tmp/a.py", 4, 2)
        assert len(adapter.calls) == 1

    def test_different_caret_positions_are_cached_separately(self):
        """Each caret position has its own cache entry."""
        provider, adapter = _provider(DefinitionLocation("/tmp/a.py", 5, 2))

        provider.get_definition_location("call()", 0, 0)
        provider.get_definition_location("call()", 0, 1)

        assert len(adapter.calls) == 2

    def test_changed_source_invalidates_the_cache_key(self):
        """Editing the buffer produces a different cache key."""
        provider, adapter = _provider(DefinitionLocation("/tmp/a.py", 5, 2))

        provider.get_definition_location("call()", 0, 0)
        provider.get_definition_location("call(1)", 0, 0)

        assert len(adapter.calls) == 2

    def test_none_results_are_not_cached(self):
        """A failed lookup is retried on the next request."""
        provider, adapter = _provider(None)

        assert provider.get_definition_location("unknown", 0, 0) is None
        assert provider.get_definition_location("unknown", 0, 0) is None
        assert len(adapter.calls) == 2

    def test_cache_is_shared_with_the_supplied_instance(self):
        """Callers may inject a pre-populated cache."""
        cache = LanguageCache()
        provider, adapter = _provider(DefinitionLocation("/tmp/a.py", 2, 0), cache)
        provider.get_definition_location("call()", 0, 0)

        assert cache.get(adapter.calls[0][1], "definition") == ("/tmp/a.py", 1, 0)

    def test_zero_capacity_cache_degrades_to_uncached_lookups(self):
        """A disabled cache still returns correct results."""
        provider, adapter = _provider(
            DefinitionLocation("/tmp/a.py", 2, 0), LanguageCache(max_size=0)
        )

        assert provider.get_definition_location("call()", 0, 0) == ("/tmp/a.py", 1, 0)
        assert provider.get_definition_location("call()", 0, 0) == ("/tmp/a.py", 1, 0)
        assert len(adapter.calls) == 2


class TestDefinitionErrorPropagation:
    """Tests for adapter failures during navigation."""

    def test_adapter_exception_propagates(self):
        """Navigation does not swallow unexpected adapter errors."""
        provider, _adapter = _provider(error=RuntimeError("jedi crashed"))

        with pytest.raises(RuntimeError, match="jedi crashed"):
            provider.get_definition_location("call()", 0, 0)

    def test_failed_request_is_not_cached(self):
        """An exception must not poison later lookups."""
        provider, adapter = _provider(error=RuntimeError("temporary"))

        with pytest.raises(RuntimeError):
            provider.get_definition_location("call()", 0, 0)

        adapter.definition_error = None
        adapter.definition = DefinitionLocation("/tmp/a.py", 2, 0)

        assert provider.get_definition_location("call()", 0, 0) == ("/tmp/a.py", 1, 0)
