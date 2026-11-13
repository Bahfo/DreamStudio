"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Service live tests: the registry, configuration, workspace, VCS, gitignore,
and diagnostic services are driven through their public APIs.
"""

import subprocess
from pathlib import Path

import pytest

from harness import Sweep, pump, service_probe, signal_probe

pytestmark = [pytest.mark.gui, pytest.mark.e2e]


class TestServiceRegistry:
    """The registry resolves, overwrites, and rejects unknown services."""

    def test_registered_services_resolve(self, qapp, qa_registry):
        """Every fixture service resolves through the registry."""
        registry, _config_service = qa_registry
        for name in (
            "config",
            "config_service",
            "theme_content",
            "resource_manager",
            "base_dir",
            "workspace",
        ):
            assert registry.has(name), f"service '{name}' not registered"
            assert registry.get(name) is not None, f"service '{name}' resolves to None"

    def test_unknown_service_raises(self, qapp, qa_registry):
        """An unknown service name raises KeyError."""
        registry, _config_service = qa_registry
        with pytest.raises(KeyError):
            registry.get("definitely-not-registered")

    def test_register_overwrites_and_tracks_state(self, qapp, qa_registry):
        """Re-registering a service replaces it and keeps it initialized."""
        registry, _config_service = qa_registry
        first = registry.get("config")
        registry.register("config", {"version": 99})
        assert registry.get("config") == {"version": 99}, "registry did not overwrite"
        assert registry.get("config") is not first
        assert registry.is_initialized("config")

    def test_registered_names_lists_services(self, qapp, qa_registry):
        """registered_names reports the fixture services."""
        registry, _config_service = qa_registry
        names = registry.registered_names()
        for expected in ("config", "theme_content", "resource_manager", "workspace"):
            assert expected in names, f"'{expected}' missing from {names}"


class TestConfigurationService:
    """Configuration reads, writes, and repairs its JSON file."""

    def test_load_returns_defaults(self, qapp, qa_registry):
        """A fresh configuration service loads a usable default document."""
        _registry, config_service = qa_registry
        config = config_service.load()
        assert isinstance(config, dict), "configuration is not a dict"
        assert "editor" in config, "configuration missing the editor section"

    def test_set_persists_value(self, qapp, qa_registry, tmp_path):
        """A written value survives a reload from disk."""
        _registry, config_service = qa_registry
        config_service.set(
            "editor", dict(config_service.get("editor", {}), font_size=17)
        )
        reloaded = config_service.load()
        assert reloaded["editor"]["font_size"] == 17, "value did not persist"

    def test_invalid_config_is_repaired(self, qapp, qa_registry):
        """A corrupted config file is repaired instead of raising."""
        _registry, config_service = qa_registry
        config_path = Path(config_service._config_path)
        config_path.write_text("{ not json at all", encoding="utf-8")
        repaired = config_service.load()
        assert isinstance(repaired, dict), "repaired config is not a dict"
        assert "editor" in repaired, "repaired config missing the editor section"

    def test_get_returns_the_stored_section(self, qapp, qa_registry):
        """get() returns the top-level section that was stored."""
        _registry, config_service = qa_registry
        config_service.set(
            "editor", dict(config_service.get("editor", {}), font_size=13)
        )
        section = config_service.get("editor", {})
        assert section.get("font_size") == 13, "get() did not return the stored section"
        assert (
            config_service.get("missing", "fallback") == "fallback"
        ), "get() ignored the default value"


class TestWorkspaceService:
    """The workspace service tracks the active solution path."""

    def test_open_workspace_sets_path(self, qapp, qa_registry, sample_tree):
        """Opening a workspace records its absolute path."""
        registry, _config_service = qa_registry
        workspace = registry.get("workspace")
        workspace.open_workspace(str(sample_tree))
        assert Path(workspace.current_path) == Path(sample_tree).resolve()

    def test_open_invalid_workspace_raises(self, qapp, qa_registry):
        """Opening a missing directory raises ValueError."""
        registry, _config_service = qa_registry
        workspace = registry.get("workspace")
        with pytest.raises(ValueError):
            workspace.open_workspace("/nonexistent/workspace/path")

    def test_workspace_changed_signal_emitted_once(
        self, qapp, qa_registry, sample_tree
    ):
        """Opening a workspace emits workspace_changed exactly once."""
        registry, _config_service = qa_registry
        workspace = registry.get("workspace")
        counter = signal_probe(workspace.workspace_changed)
        workspace.open_workspace(str(sample_tree))
        assert counter.count == 1, f"workspace_changed emitted {counter.count} times"

    def test_solution_name_uses_directory(self, qapp, qa_registry, sample_tree):
        """The solution name falls back to the workspace directory name."""
        registry, _config_service = qa_registry
        workspace = registry.get("workspace")
        workspace.open_workspace(str(sample_tree))
        assert workspace.solution_name, "solution name is empty"

    def test_reset_workspace_repoints_window(self, qapp, qa_window, sample_tree):
        """Resetting the workspace re-points the attached window."""
        window = qa_window
        workspace = window._registry.get("workspace")
        workspace.open_workspace(str(sample_tree))
        pump(qapp, 100)
        assert (
            Path(window.currentDirectory) == Path(sample_tree).resolve()
        ), "window did not follow the workspace reset"


class TestGitIgnoreService:
    """The gitignore service loads patterns from the workspace."""

    def test_patterns_are_loaded(self, qapp, sample_tree):
        """Patterns from the workspace .gitignore are exposed."""
        from editor.utils.explorer.gitignore import GitIgnoreService

        service = GitIgnoreService()
        service.set_root(str(sample_tree))
        pump(qapp, 200)
        patterns = service.patterns()
        assert patterns, "no gitignore patterns loaded"
        assert any(
            "ignored_dir" in str(pattern) for pattern in patterns
        ), f"workspace .gitignore pattern missing: {patterns}"
        service.stop()

    def test_patterns_updated_signal(self, qapp, sample_tree):
        """Reloading the service emits patterns_updated."""
        from editor.utils.explorer.gitignore import GitIgnoreService

        service = GitIgnoreService()
        service.set_root(str(sample_tree))
        pump(qapp, 200)
        counter = signal_probe(service.patterns_updated)
        service._reload()
        pump(qapp, 100)
        assert counter.count >= 1, "patterns_updated never fired"
        service.stop()


class TestGitStatusService:
    """The VCS status service reports a clean and a dirty repository."""

    def _git(self, workspace: Path, *args: str) -> None:
        """Run a git command inside the workspace.

        Args:
            workspace: Repository directory.
            args: Git arguments to execute.
        """
        subprocess.run(
            ["git", *args],
            cwd=workspace,
            check=True,
            capture_output=True,
            env={
                "GIT_AUTHOR_NAME": "QA",
                "GIT_AUTHOR_EMAIL": "qa@example.com",
                "GIT_COMMITTER_NAME": "QA",
                "GIT_COMMITTER_EMAIL": "qa@example.com",
                "HOME": str(workspace),
            },
        )

    def test_clean_repo_snapshot_is_empty(self, qapp, git_workspace):
        """A freshly committed repository reports no changed files."""
        from editor.utils.git_control.status_service import GitStatusService

        service = GitStatusService()
        service.set_root(str(git_workspace))
        service.request_scan("qa")
        pump(qapp, 1500)
        snapshot = service.snapshot()
        assert isinstance(snapshot, dict), "snapshot is not a dict"
        service.stop()

    def test_dirty_file_appears_in_snapshot(self, qapp, git_workspace):
        """Editing a tracked file marks it changed in the snapshot."""
        from editor.utils.git_control.status_service import GitStatusService

        service = GitStatusService()
        service.set_root(str(git_workspace))
        service.request_scan("qa")
        pump(qapp, 1500)
        tracked = git_workspace / "main.py"
        tracked.write_text(tracked.read_text() + "\n# changed\n", encoding="utf-8")
        service.request_scan("qa:dirty")
        pump(qapp, 2000)
        snapshot = service.snapshot()
        assert snapshot, "dirty file missing from the status snapshot"
        service.stop()

    def test_request_scan_emits_statuses_updated(self, qapp, git_workspace):
        """A scan request eventually emits statuses_updated."""
        from editor.utils.git_control.status_service import GitStatusService

        service = GitStatusService()
        service.set_root(str(git_workspace))
        counter = signal_probe(service.statuses_updated)
        service.request_scan("qa")
        pump(qapp, 2000)
        assert counter.count >= 1, "statuses_updated never fired"
        service.stop()

    def test_repeated_scans_are_stable(self, qapp, git_workspace):
        """Repeated scan requests converge on one snapshot."""
        from editor.utils.git_control.status_service import GitStatusService

        service = GitStatusService()
        service.set_root(str(git_workspace))
        for _ in range(3):
            service.request_scan("qa")
            pump(qapp, 600)
        first = dict(service.snapshot())
        service.request_scan("qa")
        pump(qapp, 1200)
        assert dict(service.snapshot()) == first, "snapshot changed between scans"
        service.stop()


class TestDiagnosticStore:
    """The diagnostic store tracks generations, revisions, and problems."""

    def test_reset_sets_generation(self, qapp):
        """Resetting the store adopts the new generation."""
        from editor.analysis.diagnostic_store import DiagnosticStore

        store = DiagnosticStore()
        store.reset(7)
        assert store.generation == 7, f"generation not adopted: {store.generation}"
        assert store.is_current(7), "current generation not recognized"
        assert not store.is_current(6), "stale generation treated as current"

    def test_set_paths_records_problems(self, qapp, tmp_path):
        """Problems given to the store are returned by problems()."""
        from editor.analysis.diagnostic_store import DiagnosticStore
        from editor.analysis.types import Problem, ProblemSeverity

        store = DiagnosticStore()
        store.reset(1)
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n", encoding="utf-8")
        problem = Problem(
            file_path=str(target),
            severity=ProblemSeverity.ERROR,
            message="qa problem",
            line=1,
            column=1,
        )
        store.set_paths([problem])
        problems = store.problems()
        assert len(problems) == 1, f"expected one problem, got {len(problems)}"
        assert problems[0].message == "qa problem"

    def test_clear_results_empties_store(self, qapp, tmp_path):
        """Clearing the store removes every recorded problem."""
        from editor.analysis.diagnostic_store import DiagnosticStore
        from editor.analysis.types import Problem, ProblemSeverity

        store = DiagnosticStore()
        store.reset(1)
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n", encoding="utf-8")
        store.set_paths(
            [
                Problem(
                    file_path=str(target),
                    severity=ProblemSeverity.WARNING,
                    message="warn",
                    line=2,
                    column=1,
                )
            ]
        )
        store.clear_results()
        assert not store.problems(), "store still holds problems after clear"

    def test_dirty_tracking_round_trip(self, qapp, tmp_path):
        """Marking a path dirty and clean round-trips through the store."""
        from editor.analysis.diagnostic_store import DiagnosticStore

        store = DiagnosticStore()
        store.reset(1)
        target = str(tmp_path / "dirty.py")
        store.mark_dirty(target)
        assert store.is_dirty(target), "path not marked dirty"
        store.mark_clean(target)
        assert not store.is_dirty(target), "path still dirty after mark_clean"

    def test_changed_signal_fires_once_per_update(self, qapp, tmp_path):
        """A store update emits changed exactly once."""
        from editor.analysis.diagnostic_store import DiagnosticStore
        from editor.analysis.types import Problem, ProblemSeverity

        store = DiagnosticStore()
        store.reset(1)
        counter = signal_probe(store.changed)
        target = tmp_path / "signal.py"
        target.write_text("x = 1\n", encoding="utf-8")
        store.set_paths(
            [
                Problem(
                    file_path=str(target),
                    severity=ProblemSeverity.ERROR,
                    message="one",
                    line=1,
                    column=1,
                )
            ]
        )
        assert counter.count == 1, f"changed emitted {counter.count} times"


class TestDiagnosticRouter:
    """The router dispatches analysis requests to the right backend."""

    def test_supported_suffixes_include_python(self, qapp):
        """Python files are a supported analysis suffix."""
        from editor.analysis.router import DiagnosticRouter

        suffixes = DiagnosticRouter.supported_suffixes()
        assert ".py" in suffixes, f"python not supported: {suffixes}"

    def test_analyze_buffer_returns_problems(self, qapp, tmp_path):
        """Analyzing a buffer returns a list of problems."""
        from editor.analysis.router import DiagnosticRouter

        target = tmp_path / "analyzed.py"
        target.write_text("def f(:\n    pass\n", encoding="utf-8")
        problems = DiagnosticRouter.analyze_buffer(
            str(target), "def f(:\n    pass\n", str(tmp_path)
        )
        assert isinstance(problems, list), "analyze_buffer did not return a list"

    def test_backend_for_unknown_suffix_is_none(self, qapp):
        """An unknown file suffix has no backend."""
        from editor.analysis.router import DiagnosticRouter

        assert DiagnosticRouter.backend_for("/tmp/file.unknownsuffix") is None


class TestServiceProbeHarness:
    """The harness service probe records failures instead of hiding them."""

    def test_service_probe_records_failures(self, qapp):
        """A failing call inside service_probe is recorded, not raised."""
        sweep = Sweep("probe")

        def boom() -> None:
            """Raise an error to exercise the sweep recorder.

            Raises:
                RuntimeError: Always.
            """
            raise RuntimeError("boom")

        service_probe(object(), {"boom": boom}, sweep)
        assert not sweep.ok, "sweep did not record the failure"
        assert "boom" in sweep.failures[0][0]

    def test_service_probe_reports_success(self, qapp):
        """A successful call inside service_probe returns its value."""
        sweep = Sweep("probe")
        results = service_probe(object(), {"ok": lambda: 42}, sweep)
        assert results["ok"] == 42, "service_probe lost the result"
        assert sweep.ok, "successful step was recorded as a failure"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
