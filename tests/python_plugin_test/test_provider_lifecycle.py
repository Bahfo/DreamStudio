"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for provider construction, capability flags, and delegated services.
"""

from __future__ import annotations

import builtins

import pytest

from editor.Ironica.plugins.python import folding as folding_module
from editor.Ironica.plugins.python import semantic_highlights as highlights_module
from editor.Ironica.plugins.python.cache import LanguageCache
from editor.Ironica.plugins.python.jedi_adapter import JediAdapter
from editor.Ironica.plugins.python.provider import (
    PythonLanguageProvider,
    create_provider,
)
from tests.python_plugin_test.helpers import RecordingAdapter


class TestProviderConstruction:
    """Tests for the provider factory and initial state."""

    def test_create_provider_wires_jedi_adapter_and_cache(self):
        """The factory returns a fully wired production provider."""
        provider = create_provider()

        assert isinstance(provider, PythonLanguageProvider)
        assert isinstance(provider._adapter, JediAdapter)
        assert isinstance(provider._cache, LanguageCache)
        assert provider.file_path is None
        assert provider.project_root is None

    def test_factory_returns_a_fresh_provider_each_time(self):
        """Every call yields an independent provider."""
        assert create_provider() is not create_provider()

    def test_supplied_cache_is_used(self):
        """Callers may inject a cache instance."""
        cache = LanguageCache(max_size=3)
        provider = PythonLanguageProvider(RecordingAdapter(), cache=cache)

        assert provider._cache is cache

    def test_default_cache_is_created_when_omitted(self):
        """A provider without a supplied cache owns one."""
        provider = PythonLanguageProvider(RecordingAdapter())

        assert isinstance(provider._cache, LanguageCache)

    @pytest.mark.parametrize(
        ("attribute", "expected"),
        [
            ("remote_analysis", True),
            ("remote_kind", "analysis"),
            ("language_id", "python"),
        ],
    )
    def test_class_level_capabilities(self, attribute, expected):
        """Remote analysis dispatch and the language id are stable."""
        assert getattr(PythonLanguageProvider, attribute) == expected

    @pytest.mark.parametrize(
        "method",
        ["has_folding", "has_diagnostics", "has_outline"],
    )
    def test_feature_flags_are_enabled(self, method):
        """Python advertises folding, diagnostics, and outlines."""
        provider = PythonLanguageProvider(RecordingAdapter())

        assert getattr(provider, method)() is True

    def test_file_path_and_project_root_round_trip(self):
        """The path properties store and return values."""
        provider = PythonLanguageProvider(RecordingAdapter())

        provider.file_path = "/tmp/module.py"
        provider.project_root = "/tmp/project"

        assert provider.file_path == "/tmp/module.py"
        assert provider.project_root == "/tmp/project"

    def test_completion_manager_starts_as_none(self):
        """No completion manager exists until one is created."""
        provider = PythonLanguageProvider(RecordingAdapter())

        assert provider.completion_manager is None


class TestProviderFormatting:
    """Tests for black-backed source formatting."""

    def test_simple_source_is_formatted(self):
        """Black normalizes spacing and ensures a trailing newline."""
        provider = PythonLanguageProvider(RecordingAdapter())

        formatted = provider.format_source("def f( x ):\n    return x")

        assert formatted == "def f(x):\n    return x\n"

    def test_empty_source_is_returned_unchanged(self):
        """An empty buffer is never handed to black."""
        provider = PythonLanguageProvider(RecordingAdapter())

        assert provider.format_source("") == ""

    @pytest.mark.parametrize("source", ["   ", "\n\n", "\t "])
    def test_whitespace_only_source_is_returned_unchanged(self, source):
        """Whitespace-only buffers are left untouched."""
        provider = PythonLanguageProvider(RecordingAdapter())

        assert provider.format_source(source) == source

    def test_syntax_error_returns_the_original_source(self):
        """Formatting failures degrade to the unformatted buffer."""
        provider = PythonLanguageProvider(RecordingAdapter())
        broken = "def broken(:\n    pass\n"

        assert provider.format_source(broken) == broken

    def test_missing_black_returns_the_original_source(self, monkeypatch):
        """A missing formatter dependency is tolerated."""
        provider = PythonLanguageProvider(RecordingAdapter())
        source = "x=1\n"
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "black":
                raise ImportError("black is not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        assert provider.format_source(source) == source


class TestProviderDelegation:
    """Tests for services forwarded to plugin submodules."""

    def test_semantic_highlights_delegate_to_the_module_function(self, monkeypatch):
        """The provider exposes the module-level highlighting pipeline."""
        sentinel = [(0, 3, "#FF0000")]
        received = []

        def fake_highlights(text):
            received.append(text)
            return sentinel

        monkeypatch.setattr(
            highlights_module, "get_semantic_highlights", fake_highlights
        )
        provider = PythonLanguageProvider(RecordingAdapter())

        assert provider.get_semantic_highlights("def f(): pass") == sentinel
        assert received == ["def f(): pass"]

    def test_invalidate_cache_delegates_to_the_module_function(self, monkeypatch):
        """The provider drops the global semantic cache through the module."""
        calls = []
        monkeypatch.setattr(
            highlights_module, "invalidate_semantic_cache", lambda: calls.append(True)
        )
        provider = PythonLanguageProvider(RecordingAdapter())

        provider.invalidate_cache()

        assert calls == [True]

    def test_fold_regions_delegate_to_the_module_function(self, monkeypatch):
        """Fold computation is forwarded verbatim."""
        sentinel = [object()]
        received = []

        def fake_regions(text):
            received.append(text)
            return sentinel

        monkeypatch.setattr(folding_module, "compute_fold_regions", fake_regions)
        provider = PythonLanguageProvider(RecordingAdapter())

        assert provider.get_fold_regions("def f():\n    pass") == sentinel
        assert received == ["def f():\n    pass"]

    def test_outline_without_file_path_keeps_empty_root_name(self):
        """A nameless outline is not renamed without a provider path."""
        provider = PythonLanguageProvider(RecordingAdapter())

        result = provider.get_outline("")

        assert result.language == "python"
        assert result.root.name == ""

    def test_outline_is_named_after_the_provider_file_path(self):
        """The provider supplies the filename for a nameless root."""
        provider = PythonLanguageProvider(RecordingAdapter())
        provider.file_path = "/tmp/module.py"

        result = provider.get_outline("x = 1\n")

        assert result.root.name == "/tmp/module.py"

    def test_empty_outline_without_file_path_stays_unnamed(self):
        """A nameless root remains nameless when no path is configured."""
        provider = PythonLanguageProvider(RecordingAdapter())

        result = provider.get_outline("def named():\n    pass\n")

        assert result.root.name == ""


class TestProviderManagerCreation:
    """Tests for factory methods that build Qt manager objects."""

    def test_completion_manager_is_created_and_tracked(self, fake_editor):
        """The completion factory stores and returns the new manager."""
        provider = PythonLanguageProvider(RecordingAdapter())
        manager = provider.create_completion_manager(
            fake_editor, "/tmp/module.py", None
        )
        try:
            assert provider.completion_manager is manager
            assert manager._file_path == "/tmp/module.py"
            assert provider.file_path == "/tmp/module.py"
        finally:
            manager.shutdown()

    def test_completion_manager_updates_provider_path(self, fake_editor):
        """Creating a manager repoints the provider at the editor's file."""
        provider = PythonLanguageProvider(RecordingAdapter())
        manager = provider.create_completion_manager(fake_editor, "/tmp/a.py", None)
        try:
            assert provider.file_path == "/tmp/a.py"
        finally:
            manager.shutdown()

    def test_completion_manager_without_path_clears_provider_path(self, fake_editor):
        """An unsaved buffer clears a stale path instead of reusing it."""
        provider = PythonLanguageProvider(RecordingAdapter())
        provider.file_path = "/tmp/stale.py"

        manager = provider.create_completion_manager(fake_editor, None, None)
        try:
            assert provider.file_path is None
        finally:
            manager.shutdown()

    def test_diagnostic_manager_is_created_with_path(self, fake_editor):
        """The diagnostics factory forwards the path to the manager."""
        provider = PythonLanguageProvider(RecordingAdapter())

        manager = provider.create_diagnostic_manager(
            fake_editor, "/tmp/module.py", None
        )
        try:
            assert manager._file_path == "/tmp/module.py"
            assert manager.owner_id == id(fake_editor)
        finally:
            manager.shutdown()

    def test_post_fold_setup_labels_import_regions(self):
        """Import folds receive a custom display label with their line count."""
        provider = PythonLanguageProvider(RecordingAdapter())
        calls = []

        class FoldEditor:
            def _setup_folding_display_text(self):
                calls.append("setup")

            def set_custom_import_fold_text(self, start_line, count):
                calls.append((start_line, count))

        class Region:
            def __init__(self, kind, start, end):
                self.kind = kind
                self.start_line = start
                self.end_line = end

        regions = [Region("import", 0, 3), Region("function", 5, 9)]
        provider.post_fold_setup(FoldEditor(), regions)

        assert calls == ["setup", (0, 4)]

    def test_post_fold_setup_tolerates_editors_without_the_feature(self):
        """A plain editor without fold display support is accepted."""
        provider = PythonLanguageProvider(RecordingAdapter())

        class PlainEditor:
            pass

        class Region:
            kind = "import"
            start_line = 0
            end_line = 1

        provider.post_fold_setup(PlainEditor(), [Region()])
