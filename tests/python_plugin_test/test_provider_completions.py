"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for completion forwarding, error tolerance, and context construction.
"""

from __future__ import annotations

import pytest

from editor.Ironica.plugins.python.domain_models import CompletionDetails
from editor.Ironica.plugins.python.provider import PythonLanguageProvider
from tests.python_plugin_test.helpers import RecordingAdapter


def _provider(
    completions: list[CompletionDetails] | None = None,
    error: Exception | None = None,
) -> tuple[PythonLanguageProvider, RecordingAdapter]:
    """Build a provider wired to a deterministic completion adapter."""
    adapter = RecordingAdapter(completions=completions, completions_error=error)
    return PythonLanguageProvider(adapter=adapter), adapter


class TestCompletionForwarding:
    """Tests for the adapter-to-editor completion bridge."""

    def test_adapter_results_are_returned_unchanged(self):
        """The provider forwards the adapter's completion objects verbatim."""
        expected = [
            CompletionDetails("path", "path", "module", "def path(...)"),
            CompletionDetails("open", "open", "function", "def open(...)"),
        ]
        provider, _adapter = _provider(expected)

        result = provider.get_completions("import os\nos.pa", (1, 5), "pa")

        assert result == expected

    def test_empty_adapter_result_yields_empty_list(self):
        """No suggestions means an empty list, not ``None``."""
        provider, _adapter = _provider([])

        assert provider.get_completions("x = 1", (0, 0), "") == []

    def test_empty_text_short_circuits_without_adapter_call(self):
        """An empty buffer is never sent to Jedi."""
        provider, adapter = _provider([CompletionDetails("x")])

        assert provider.get_completions("", (0, 0), "x") == []
        assert adapter.calls == []

    def test_prefix_is_accepted_but_not_forwarded(self):
        """The prefix argument is part of the editor surface only."""
        provider, adapter = _provider([CompletionDetails("value")])

        provider.get_completions("val", (0, 3), "val")

        context = adapter.calls[0][1]
        assert context.source_code == "val"
        assert context.line == 1
        assert context.column == 3


class TestCompletionContext:
    """Tests for the snapshot built for completion requests."""

    @pytest.mark.parametrize(
        ("cursor", "expected_line", "expected_column"),
        [
            ((0, 0), 1, 0),
            ((0, 7), 1, 7),
            ((4, 2), 5, 2),
            ((99, 0), 100, 0),
        ],
    )
    def test_cursor_position_maps_to_one_based_line(
        self, cursor, expected_line, expected_column
    ):
        """The tuple's row/column become Jedi's line/column pair."""
        provider, adapter = _provider([])

        provider.get_completions("text", cursor, "")

        context = adapter.calls[0][1]
        assert context.line == expected_line
        assert context.column == expected_column

    def test_provider_paths_are_used_by_default(self):
        """Configured paths flow into the completion request."""
        provider, adapter = _provider([])
        provider.file_path = "/tmp/module.py"
        provider.project_root = "/tmp/project"

        provider.get_completions("text", (0, 0), "")

        context = adapter.calls[0][1]
        assert context.file_path == "/tmp/module.py"
        assert context.project_root == "/tmp/project"

    def test_explicit_paths_override_provider_paths(self):
        """Per-request paths take precedence."""
        provider, adapter = _provider([])
        provider.file_path = "/tmp/default.py"
        provider.project_root = "/tmp/default-root"

        provider.get_completions(
            "text",
            (0, 0),
            "",
            file_path="/tmp/explicit.py",
            project_root="/tmp/explicit-root",
        )

        context = adapter.calls[0][1]
        assert context.file_path == "/tmp/explicit.py"
        assert context.project_root == "/tmp/explicit-root"

    def test_unsaved_buffer_context_has_no_path(self):
        """Without a configured path the context path is ``None``."""
        provider, adapter = _provider([])

        provider.get_completions("text", (0, 0), "")

        assert adapter.calls[0][1].file_path is None


class TestCompletionErrorTolerance:
    """Tests for the provider's completion error boundary."""

    def test_adapter_exception_becomes_empty_list(self):
        """Completion failures never break the editor."""
        provider, _adapter = _provider(error=RuntimeError("jedi crashed"))

        assert provider.get_completions("text", (0, 0), "") == []

    @pytest.mark.parametrize(
        "error",
        [
            RuntimeError("boom"),
            ValueError("bad cursor"),
            TimeoutError("jedi timeout"),
        ],
    )
    def test_every_exception_type_is_swallowed(self, error):
        """The contract intentionally catches broad exceptions."""
        provider, _adapter = _provider(error=error)

        assert provider.get_completions("text", (0, 0), "") == []

    def test_failure_is_logged(self, caplog):
        """A completion failure is reported to the plugin logger."""
        provider, _adapter = _provider(error=RuntimeError("jedi crashed"))

        with caplog.at_level("WARNING", logger="DreamStudio.PythonSupport.Provider"):
            provider.get_completions("text", (0, 0), "")

        assert "Completion request failed" in caplog.text
        assert "jedi crashed" in caplog.text

    def test_subsequent_requests_still_reach_the_adapter(self):
        """A failed call does not disable later completion requests."""
        provider, adapter = _provider(error=RuntimeError("temporary"))
        assert provider.get_completions("text", (0, 0), "") == []

        adapter.completions_error = None
        adapter.completions = [CompletionDetails("value")]

        assert provider.get_completions("text", (0, 0), "") == [
            CompletionDetails("value")
        ]
        assert len(adapter.calls) == 2
