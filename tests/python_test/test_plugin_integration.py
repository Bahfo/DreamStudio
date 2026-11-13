"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Integration tests for plugin registration, analysis-server dispatch, and the
whole-document analysis worker/manager.
"""

from __future__ import annotations

import dataclasses
import os
import sys
from types import SimpleNamespace

import pytest

from editor.Ironica import analysis_server
from editor.Ironica.analysis_bridge import AnalysisProcessError
from editor.Ironica.analysis_worker import (
    AnalysisManager,
    _AnalysisRequest,
    _AnalysisWorker,
)
from editor.Ironica.language_engine import LanguageRegistry
from editor.Ironica.plugins import registration
from editor.Ironica.plugins.python.provider import PythonLanguageProvider
from editor.Ironica.process_manager import process_manager
from editor.utils.file_properties import outline as outline_backend
from tests.python_plugin_test.helpers import python_language_config


def _language_config() -> dict:
    """Return a valid Python language configuration."""
    return python_language_config()


@pytest.fixture
def isolated_analysis_state(monkeypatch):
    """Reset the analysis server's environment memoization per test."""
    monkeypatch.setattr(analysis_server, "_LAST_THEME", "")
    monkeypatch.setattr(analysis_server, "_LAST_CONFIGS", {})
    monkeypatch.setattr(analysis_server, "_JEDI_LAST_SOURCE", "")
    monkeypatch.setattr(analysis_server, "_JEDI_LAST_PATH", None)
    monkeypatch.setattr(analysis_server, "_JEDI_LAST_SCRIPT", None)
    yield


@pytest.fixture
def isolated_python_registry():
    """Snapshot and restore the global language/outline registries."""
    configs = dict(LanguageRegistry._configs)
    providers = dict(LanguageRegistry._providers)
    extensions = dict(LanguageRegistry._extension_map)
    snippets = dict(LanguageRegistry._snippet_paths)
    parsers = dict(outline_backend._PARSERS)

    yield

    for store, saved in (
        (LanguageRegistry._configs, configs),
        (LanguageRegistry._providers, providers),
        (LanguageRegistry._extension_map, extensions),
        (LanguageRegistry._snippet_paths, snippets),
        (outline_backend._PARSERS, parsers),
    ):
        store.clear()
        store.update(saved)


class TestAnalysisServerDiagnostics:
    """Tests for the diagnostics request handler."""

    def test_valid_source_returns_no_diagnostics(self, isolated_analysis_state):
        """The handler reports an empty list for compilable source."""
        response = analysis_server.handle_request(
            ("diagnostics", 3, "value = 1\n", "/tmp/a.py")
        )

        assert response == ("diagnostics", 3, [])

    def test_invalid_source_returns_wire_diagnostics(self, isolated_analysis_state):
        """Syntax errors cross the wire as plain dictionaries."""
        response = analysis_server.handle_request(
            ("diagnostics", 4, "def broken(:\n    pass\n", None)
        )

        assert response[0] == "diagnostics"
        assert response[1] == 4
        assert response[2]
        diagnostic = response[2][0]
        assert set(diagnostic) == {
            "line",
            "start_col",
            "end_line",
            "end_col",
            "color",
            "message",
        }

    def test_diagnostics_are_json_friendly(self, isolated_analysis_state):
        """Every diagnostic value is a primitive, not a parser object."""
        _, _, diagnostics = analysis_server.handle_request(
            ("diagnostics", 5, "def broken(:\n", None)
        )

        for diagnostic in diagnostics:
            assert isinstance(diagnostic["line"], int)
            assert isinstance(diagnostic["start_col"], int)
            assert isinstance(diagnostic["end_col"], int)
            assert isinstance(diagnostic["color"], str)
            assert isinstance(diagnostic["message"], str)


class TestAnalysisServerCompletions:
    """Tests for the completions request handler."""

    def test_completions_are_wire_dictionaries(self, isolated_analysis_state):
        """Jedi completions are flattened to serializable dictionaries."""
        source = "import os\nos.pa\n"

        kind, request_id, results = analysis_server.handle_request(
            ("completions", 9, source, 1, 5, "/tmp/module.py")
        )

        assert (kind, request_id) == ("completions", 9)
        assert isinstance(results, list)
        assert results
        assert set(results[0]) == {"text", "insert_text", "kind", "signature"}
        assert any(item["text"] == "path" for item in results)

    def test_results_are_capped(self, isolated_analysis_state):
        """The server never returns more than its documented limit."""
        _, _, results = analysis_server.handle_request(
            ("completions", 1, "", 0, 0, None)
        )

        assert len(results) == analysis_server._MAX_COMPLETION_ITEMS

    def test_caret_is_clamped_to_the_line(self, isolated_analysis_state):
        """An out-of-range column is clamped instead of failing."""
        response = analysis_server.handle_request(
            ("completions", 2, "import os\nos.pa", 1, 500, "/tmp/a.py")
        )

        assert response[2]
        assert any(item["text"] == "path" for item in response[2])

    def test_caret_line_is_clamped_to_the_buffer(self, isolated_analysis_state):
        """An out-of-range row is clamped to the final line."""
        response = analysis_server.handle_request(
            ("completions", 3, "value = 1\n", 99, 0, None)
        )

        assert response[0] == "completions"
        assert isinstance(response[2], list)

    def test_jedi_failure_returns_empty_results(
        self, isolated_analysis_state, monkeypatch
    ):
        """A Jedi failure is reported as no suggestions."""

        class BrokenScript:
            def complete(self, **kwargs):
                raise RuntimeError("jedi failed")

        monkeypatch.setattr(
            analysis_server, "_jedi_script", lambda source, path: BrokenScript()
        )

        response = analysis_server.handle_request(
            ("completions", 4, "value", 0, 0, None)
        )

        assert response == ("completions", 4, [])

    def test_script_is_reused_for_the_same_buffer(self, isolated_analysis_state):
        """The server caches the last Jedi script by path and source."""
        first = analysis_server._jedi_script("value = 1\n", "/tmp/a.py")
        second = analysis_server._jedi_script("value = 1\n", "/tmp/a.py")

        assert first is second

    def test_changed_buffer_invalidates_the_script(self, isolated_analysis_state):
        """Editing or repathing the buffer creates a fresh script."""
        first = analysis_server._jedi_script("value = 1\n", "/tmp/a.py")
        second = analysis_server._jedi_script("value = 2\n", "/tmp/a.py")
        third = analysis_server._jedi_script("value = 2\n", "/tmp/b.py")

        assert first is not second
        assert second is not third


class TestAnalysisServerAnalysis:
    """Tests for the whole-document analysis request handler."""

    def test_analysis_response_contains_highlights_and_folds(
        self, isolated_analysis_state
    ):
        """The handler returns both semantic overlays and fold regions."""
        source = "def greet(name):\n    message = name\n    return message\n"

        kind, request_id, highlights, folds = analysis_server.handle_request(
            ("analysis", 12, source, None, "", None)
        )

        assert (kind, request_id) == ("analysis", 12)
        assert highlights
        assert any(
            start == 4 and length == 5 and colour.startswith("#")
            for start, length, colour in highlights
        )
        assert len(folds) == 1
        assert (folds[0].start_line, folds[0].end_line, folds[0].kind) == (
            0,
            2,
            "function",
        )

    def test_analysis_accepts_a_registered_config(
        self, isolated_analysis_state, isolated_python_registry
    ):
        """A supplied config is registered before highlighting."""
        source = "def f(x):\n    return x\n"

        response = analysis_server.handle_request(
            ("analysis", 13, source, _language_config(), "dark", None)
        )

        assert response[0] == "analysis"
        assert LanguageRegistry.get_config("python")["lang"] == "python"
        assert response[2]

    def test_workspace_paths_are_removed_after_analysis(
        self, isolated_analysis_state, tmp_path
    ):
        """Temporary workspace site paths never leak into the process."""
        site_packages = tmp_path / "site-packages"
        site_packages.mkdir()
        assert str(site_packages) not in sys.path

        response = analysis_server.handle_request(
            ("analysis", 14, "value = 1\n", None, "", [str(site_packages)])
        )

        assert response[0] == "analysis"
        assert str(site_packages) not in sys.path

    def test_workspace_path_helper_ignores_missing_directories(self, tmp_path):
        """Nonexistent paths are never added."""
        missing = str(tmp_path / "missing")

        added = analysis_server._apply_workspace_paths([missing])

        assert added == []
        assert missing not in sys.path

    def test_workspace_path_helper_removes_every_copy(self, tmp_path):
        """Removal cleans duplicate entries as well."""
        existing = tmp_path / "extra"
        existing.mkdir()
        added = analysis_server._apply_workspace_paths([str(existing)])
        assert added == [str(existing)]
        sys.path.append(str(existing))

        try:
            analysis_server._remove_workspace_paths(added)
            assert sys.path.count(str(existing)) == 0
        finally:
            while str(existing) in sys.path:
                sys.path.remove(str(existing))

    def test_unknown_request_returns_an_error(self, isolated_analysis_state):
        """Unknown payload kinds are reported, not raised."""
        assert analysis_server.handle_request(("unknown", 7)) == (
            "error",
            7,
            "unknown request payload",
        )

    def test_none_payload_is_ignored(self):
        """A closed stream payload yields ``None``."""
        assert analysis_server.handle_request(None) is None

    def test_eight_element_payload_is_rejected(self, isolated_analysis_state):
        """An over-long payload produces an error response."""
        response = analysis_server.handle_request(
            ("analysis", 1, "value = 1\n", None, "", None, "extra", "more")
        )

        assert response[0] == "error"
        assert response[1] == 1
        assert "not enough values" in response[2] or "too many" in response[2]


class TestAnalysisWorkerAnalyze:
    """Tests for the worker's in-process provider analysis."""

    class _Provider:
        def __init__(
            self,
            semantic=True,
            folding=True,
            scoped=False,
            error=None,
        ) -> None:
            self.semantic = semantic
            self.folding = folding
            self.scoped = scoped
            self.error = error
            self.calls: list[tuple[str, dict]] = []

        want_file_path = False

        def get_semantic_highlights(self, source, **kwargs):
            if self.error:
                raise self.error
            self.calls.append(("semantic", kwargs))
            return [(0, 1, "#FFFFFF")]

        def has_folding(self):
            return self.folding

        def get_fold_regions(self, source, **kwargs):
            self.calls.append(("folds", kwargs))
            return ["fold"]

    def test_highlights_and_folds_are_collected(self):
        """A capable provider supplies both result channels."""
        provider = self._Provider()

        assert _AnalysisWorker._analyze(provider, "value = 1") == (
            [(0, 1, "#FFFFFF")],
            ["fold"],
        )
        assert provider.calls == [("semantic", {}), ("folds", {})]

    def test_provider_without_folding_returns_none_folds(self):
        """A provider that does not fold leaves folds unset."""
        provider = self._Provider(folding=False)

        highlights, folds = _AnalysisWorker._analyze(provider, "value")

        assert highlights == [(0, 1, "#FFFFFF")]
        assert folds is None

    def test_provider_without_semantic_support(self):
        """A provider without highlighting leaves highlights unset."""
        provider = SimpleNamespace(has_folding=lambda: False)

        assert _AnalysisWorker._analyze(provider, "value") == (None, None)

    def test_scoped_provider_receives_the_file_path(self):
        """``wants_file_path`` selects the keyword-argument calling convention."""
        provider = self._Provider()
        provider.wants_file_path = True

        _AnalysisWorker._analyze(provider, "value = 1", "/tmp/a.py")

        assert provider.calls == [
            ("semantic", {"file_path": "/tmp/a.py"}),
            ("folds", {"file_path": "/tmp/a.py"}),
        ]

    def test_provider_failure_yields_both_none(self, caplog):
        """An analysis exception never escapes the worker."""
        provider = self._Provider(error=RuntimeError("analysis failed"))

        with caplog.at_level("ERROR", logger="DreamStudio.Analysis.Worker"):
            assert _AnalysisWorker._analyze(provider, "value") == (None, None)

        assert "Whole-document analysis failed" in caplog.text


class TestAnalysisWorkerWorkspacePaths:
    """Tests for workspace site-package discovery."""

    def test_virtual_env_site_packages_are_found(self, tmp_path, monkeypatch):
        """An active venv contributes its site-packages directory."""
        site = tmp_path / "lib" / "python3.12" / "site-packages"
        site.mkdir(parents=True)
        monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path))

        assert _AnalysisWorker._workspace_paths() == [str(site)]

    def test_missing_virtual_env_yields_empty(self, monkeypatch):
        """No configured venv means no extra paths."""
        monkeypatch.delenv("VIRTUAL_ENV", raising=False)

        assert _AnalysisWorker._workspace_paths() == []

    def test_nonexistent_virtual_env_yields_empty(self, monkeypatch):
        """A stale VIRTUAL_ENV is ignored."""
        monkeypatch.setenv("VIRTUAL_ENV", "/does/not/exist")

        assert _AnalysisWorker._workspace_paths() == []


class TestAnalysisWorkerRemote:
    """Tests for the subprocess analysis bridge protocol."""

    class _Provider:
        remote_analysis = True
        remote_kind = "analysis"

        def __init__(self, payload=None) -> None:
            self.payload = payload
            self.builds: list[tuple] = []

        def build_remote_request(self, request_id, source, config, theme):
            self.builds.append((request_id, source, config, theme))
            return self.payload or (
                "analysis",
                request_id,
                source,
                config,
                theme,
            )

    @staticmethod
    def _owner():
        return SimpleNamespace(owner_id=123)

    def _worker(self, response, monkeypatch, workspace_paths=None):
        worker = _AnalysisWorker(self._owner())
        calls = []

        def fake_request(owner_id, payload):
            calls.append((owner_id, payload))
            if isinstance(response, Exception):
                raise response
            return response

        monkeypatch.setattr(process_manager, "request", fake_request)
        if workspace_paths is None:
            monkeypatch.setattr(worker, "_workspace_paths", list)
        else:
            monkeypatch.setattr(worker, "_workspace_paths", lambda: workspace_paths)
        return worker, calls

    def test_successful_response(self, monkeypatch):
        """A valid response yields highlights and folds."""
        worker, calls = self._worker(
            ("analysis", 1, ["highlight"], ["fold"]), monkeypatch
        )
        request = _AnalysisRequest(1, "value", self._Provider(), None, "")

        assert worker._remote_analysis(request) == (["highlight"], ["fold"])
        assert calls[0][0] == 123

    def test_workspace_paths_are_appended_to_the_payload(self, monkeypatch):
        """Discovered site paths are sent as a sixth element."""
        worker, calls = self._worker(
            ("analysis", 1, [], []), monkeypatch, workspace_paths=["/tmp/site"]
        )
        request = _AnalysisRequest(1, "value", self._Provider(), None, "")

        worker._remote_analysis(request)

        assert calls[0][1] == (
            "analysis",
            1,
            "value",
            None,
            "",
            ["/tmp/site"],
        )

    def test_provider_without_builder_uses_default_payload(self, monkeypatch):
        """A generic remote provider uses the default analysis tuple."""
        worker, calls = self._worker(("analysis", 1, [], []), monkeypatch)
        request = _AnalysisRequest(1, "value", SimpleNamespace(), None, "")

        worker._remote_analysis(request)

        assert calls[0][1] == (
            "analysis",
            1,
            "value",
            None,
            "",
            [],
        )

    def test_none_response_means_superseded(self, monkeypatch):
        """A ``None`` response is not an error."""
        worker, _calls = self._worker(None, monkeypatch)
        request = _AnalysisRequest(1, "value", self._Provider(), None, "")

        assert worker._remote_analysis(request) is None

    @pytest.mark.parametrize("response", [[], "text", 42])
    def test_malformed_response_raises(self, monkeypatch, response):
        """Non-tuple or empty responses are protocol errors."""
        worker, _calls = self._worker(response, monkeypatch)
        request = _AnalysisRequest(1, "value", self._Provider(), None, "")

        with pytest.raises(AnalysisProcessError, match="malformed"):
            worker._remote_analysis(request)

    def test_wrong_kind_raises(self, monkeypatch):
        """A response for another service is rejected."""
        worker, _calls = self._worker(("diagnostics", 1, []), monkeypatch)
        request = _AnalysisRequest(1, "value", self._Provider(), None, "")

        with pytest.raises(AnalysisProcessError, match="server error"):
            worker._remote_analysis(request)


class TestAnalysisWorkerQueue:
    """Tests for the latest-wins worker queue."""

    def test_request_is_stored_without_starting_again(self):
        """An already-started worker replaces the pending request."""
        worker = _AnalysisWorker(SimpleNamespace(owner_id=1))
        worker._started_once = True
        provider = object()

        worker.process(4, "value", provider, {"lang": "python"}, "dark", "/tmp/a.py")

        assert worker._current_request == _AnalysisRequest(
            4, "value", provider, {"lang": "python"}, "dark", "/tmp/a.py"
        )

    def test_process_after_shutdown_is_ignored(self):
        """A shutdown worker refuses new work."""
        worker = _AnalysisWorker(SimpleNamespace(owner_id=1))
        worker._started_once = True
        worker.shutdown()

        worker.process(1, "value", object())

        assert worker._current_request is None

    def test_shutdown_clears_pending_work(self):
        """Shutdown drops the queued request."""
        worker = _AnalysisWorker(SimpleNamespace(owner_id=1))
        worker._started_once = True
        worker.process(1, "value", object())

        worker.shutdown()

        assert worker._is_shutting_down is True
        assert worker._current_request is None

    def test_request_is_frozen(self):
        """Worker requests cannot be mutated after submission."""
        request = _AnalysisRequest(1, "value", object())

        with pytest.raises(dataclasses.FrozenInstanceError):
            request.source = "other"


class _ManagerEditor:
    """Editor double for ``AnalysisManager``."""

    def __init__(self) -> None:
        self.current_provider = object()
        self.current_lang = "python"
        self.current_file_path = "/tmp/module.py"
        self._theme_name = "dark"
        self.overlays = []
        self.folds = []
        self.finished = 0
        self.fail_overlay = False

    def _apply_semantic_overlays(self, overlays):
        if self.fail_overlay:
            raise RuntimeError("overlay failed")
        self.overlays = overlays

    def _apply_fold_regions(self, folds):
        self.folds = folds

    def _on_analysis_finished(self):
        self.finished += 1


class _ManagerWorker:
    """Recording replacement for ``_AnalysisWorker``."""

    def __init__(self, shutdown_error=None) -> None:
        self.requests: list[tuple] = []
        self.shutdown_calls = 0
        self.shutdown_error = shutdown_error

    def process(self, *args):
        self.requests.append(args)

    def shutdown(self):
        self.shutdown_calls += 1
        if self.shutdown_error is not None:
            raise self.shutdown_error


@pytest.fixture
def manager_factory(monkeypatch):
    """Create managers with recording workers and a released process."""
    released = []
    monkeypatch.setattr(
        process_manager, "release", lambda owner_id: released.append(owner_id)
    )
    created = []

    def make(editor=None, worker=None):
        editor = editor or _ManagerEditor()
        manager = AnalysisManager(editor)
        fake_worker = worker or _ManagerWorker()
        manager._worker = fake_worker
        created.append(manager)
        return manager, fake_worker, editor

    yield make, released

    for manager in created:
        manager.shutdown()


class TestAnalysisManager:
    """Tests for the UI-side latest-wins analysis manager."""

    def test_request_forwards_editor_state(self, manager_factory, monkeypatch):
        """Requests carry the provider, config, theme, and path."""
        make, _released = manager_factory
        manager, worker, editor = make()
        provider = object()
        editor.current_provider = provider
        monkeypatch.setattr(
            LanguageRegistry,
            "get_config",
            classmethod(lambda cls, lang: {"lang": lang}),
        )

        manager.request_analysis("value = 1\n")

        assert worker.requests == [
            (1, "value = 1\n", provider, {"lang": "python"}, "dark", "/tmp/module.py")
        ]
        assert manager._request_counter == 1

    def test_disabled_manager_does_not_submit(self, manager_factory):
        """A background tab never submits analysis."""
        make, _released = manager_factory
        manager, worker, _editor = make()
        manager.set_enabled(False)

        manager.request_analysis("value = 1\n")

        assert worker.requests == []
        assert manager.is_enabled() is False

    def test_empty_source_does_not_submit(self, manager_factory):
        """An empty buffer is not analyzed."""
        make, _released = manager_factory
        manager, worker, _editor = make()

        manager.request_analysis("")

        assert worker.requests == []

    def test_missing_provider_does_not_submit(self, manager_factory):
        """Editors without a provider are ignored."""
        make, _released = manager_factory
        manager, worker, editor = make()
        editor.current_provider = None

        manager.request_analysis("value = 1\n")

        assert worker.requests == []

    def test_missing_language_uses_none_config(self, manager_factory):
        """An editor without a language still submits, with ``None`` config."""
        make, _released = manager_factory
        manager, worker, editor = make()
        editor.current_lang = None

        manager.request_analysis("value")

        assert worker.requests[0][3] is None

    def test_invalidate_retires_pending_results(self, manager_factory):
        """Invalidation bumps the request counter."""
        make, _released = manager_factory
        manager, _worker, _editor = make()

        manager.invalidate()

        assert manager._request_counter == 1

    def test_results_are_applied_on_the_editor(self, manager_factory):
        """Highlights and folds are rendered, then the editor is notified."""
        make, _released = manager_factory
        manager, _worker, editor = make()

        manager._apply_results(0, ["highlight"], ["fold"])

        assert editor.overlays == ["highlight"]
        assert editor.folds == ["fold"]
        assert editor.finished == 1

    def test_stale_results_are_dropped(self, manager_factory):
        """A result older than the current request is ignored."""
        make, _released = manager_factory
        manager, _worker, editor = make()
        manager._request_counter = 5

        manager._apply_results(4, ["highlight"], ["fold"])

        assert editor.overlays == []
        assert editor.folds == []
        assert editor.finished == 0

    def test_none_channels_are_skipped(self, manager_factory):
        """A ``None`` channel leaves the corresponding editor state alone."""
        make, _released = manager_factory
        manager, _worker, editor = make()

        manager._apply_results(0, None, None)

        assert editor.overlays == []
        assert editor.folds == []
        assert editor.finished == 1

    def test_application_failure_is_swallowed(self, manager_factory):
        """An editor rendering error never propagates."""
        make, _released = manager_factory
        manager, _worker, editor = make()
        editor.fail_overlay = True

        manager._apply_results(0, ["highlight"], ["fold"])

        assert editor.finished == 1

    def test_shutdown_releases_the_process(self, manager_factory):
        """Shutdown stops the worker and releases the owner id."""
        make, released = manager_factory
        manager, worker, editor = make()

        manager.shutdown()

        assert worker.shutdown_calls == 1
        assert released == [id(editor)]

    def test_shutdown_tolerates_worker_errors(self, manager_factory):
        """A failing worker shutdown is logged, not raised."""
        make, released = manager_factory
        manager, _worker, editor = make(worker=_ManagerWorker(RuntimeError("boom")))

        manager.shutdown()

        assert released == [id(editor)]


class TestPluginRegistration:
    """Tests for legacy bundled-plugin discovery and registration."""

    def test_python_spec_is_discovered(self):
        """The manifest-less Python provider is discovered as a legacy plugin."""
        specs = registration._discover_plugin_specs()

        assert "python" in specs
        spec = specs["python"]
        assert spec["root"] == registration._IRONICA_DIR
        assert spec["provider"] == (
            "editor.Ironica.plugins.python.provider.create_provider"
        )
        assert spec["keywords"] == os.path.join("keywords", "python.json")

    def test_dotted_factory_imports_the_provider(self):
        """The discovered dotted path resolves to a callable factory."""
        factory = registration._import_dotted_factory(
            "editor.Ironica.plugins.python.provider.create_provider"
        )

        assert callable(factory)
        assert isinstance(factory(), PythonLanguageProvider)

    def test_invalid_dotted_factory_returns_none(self):
        """A missing module or attribute is reported as ``None``."""
        assert registration._import_dotted_factory("does.not.exist.factory") is None
        assert (
            registration._import_dotted_factory(
                "editor.Ironica.plugins.python.provider.missing_factory"
            )
            is None
        )

    def test_registering_python_wires_every_surface(self, isolated_python_registry):
        """Registration configures language, provider, snippets, and outlines."""
        spec = registration._discover_plugin_specs()["python"]

        success, warning = registration._register_one("python", spec)

        assert success is True
        assert warning is None
        config = LanguageRegistry.get_config("python")
        assert config["lang"] == "python"
        assert set(config["extensions"]) >= {"py", "pyw", "pyi"}
        assert isinstance(
            LanguageRegistry.get_provider("python"), PythonLanguageProvider
        )
        assert LanguageRegistry.get_snippet_path("python").endswith("python.json")
        assert outline_backend.get_parser("python") is not None

    def test_registered_outline_parser_builds_a_named_tree(
        self, isolated_python_registry
    ):
        """The registered parser is reachable through the outline backend."""
        spec = registration._discover_plugin_specs()["python"]
        registration._register_one("python", spec)

        result = outline_backend.build_outline(
            "def f():\n    pass\n", "python", filename="/tmp/module.py"
        )

        assert result is not None
        assert result.root.name == "/tmp/module.py"
        assert [child.name for child in result.root.children] == ["f"]

    def test_register_outline_parser_is_idempotent(self, isolated_python_registry):
        """Registering the same provider twice leaves one working parser."""
        provider = PythonLanguageProvider.__new__(PythonLanguageProvider)
        provider._file_path = None

        registration._register_outline_parser("python", provider)
        registration._register_outline_parser("python", provider)

        assert outline_backend.get_parser("python") is not None

    def test_provider_without_outline_is_not_registered(self, isolated_python_registry):
        """A provider that declines outlines is skipped."""
        provider = SimpleNamespace(has_outline=lambda: False)

        registration._register_outline_parser("python", provider)

        assert outline_backend.get_parser("python") is None

    def test_register_outline_parser_tolerates_none(self, isolated_python_registry):
        """A missing provider is a no-op."""
        registration._register_outline_parser("python", None)

        assert outline_backend.get_parser("python") is None
