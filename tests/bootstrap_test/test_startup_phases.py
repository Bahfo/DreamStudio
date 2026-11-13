"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for startup.py helper functions and PhaseContext.
"""

from unittest.mock import MagicMock

import pytest


class TestStartupEntryPoint:
    """Tests for startup.py helper functions."""

    def test_parse_project_arg(self):
        """_parse_project_arg extracts a path from supported flags."""
        from startup import _parse_project_arg

        assert _parse_project_arg(["--project", "/path/to/proj"]) == "/path/to/proj"
        assert _parse_project_arg(["--solution", "/path/to/sol"]) == "/path/to/sol"
        assert _parse_project_arg(["-p", "/path/short"]) == "/path/short"
        assert _parse_project_arg(["--project"]) is None
        assert _parse_project_arg(["--project", "-invalid"]) is None
        assert _parse_project_arg([]) is None

    def test_reveal_result_cancelled(self, qapp):
        """_reveal_result closes the splash for a cancelled startup."""
        from config.manager import StartupResult
        from startup import _reveal_result

        result = StartupResult(cancelled=True)
        splash = MagicMock()
        splash.is_visible = True

        _reveal_result(result, splash)

        splash.close.assert_called_once()

    def test_reveal_result_failure_without_window(self, qapp):
        """_reveal_result leaves a failed startup to the caller."""
        from config.manager import StartupResult
        from startup import _reveal_result

        result = StartupResult(success=False)
        splash = MagicMock()
        splash.is_visible = True

        _reveal_result(result, splash)

        splash.close.assert_not_called()


class TestPhaseContext:
    """Tests for PhaseContext defaults and mutation."""

    def test_defaults(self):
        """PhaseContext starts with empty service slots."""
        from config.phases import PhaseContext

        ctx = PhaseContext()

        assert ctx.base_dir == ""
        assert ctx.app is None
        assert ctx.registry is None
        assert ctx.config_service is None
        assert ctx.resource_manager is None
        assert ctx.splash is None
        assert ctx.warnings == []
        assert ctx.errors == []
        assert ctx.workspace_path == ""
        assert ctx.pending_scaffold == {}

    def test_context_is_mutated_in_place(self):
        """Phases receive the same context and mutate it in place."""
        from config.phases import PhaseContext

        ctx = PhaseContext()
        ctx.config_service = MagicMock()
        ctx.workspace_path = "/test/workspace"

        assert ctx.config_service is not None
        assert ctx.workspace_path == "/test/workspace"


class TestErrorTaxonomy:
    """Tests for startup error classification."""

    def test_startup_error_carries_phase_and_details(self):
        """StartupError is fatal and exposes its phase and details."""
        from config.phases import StartupError

        error = StartupError("configuration", "Fatal error", details="trace")

        assert error.phase == "configuration"
        assert error.details == "trace"
        assert str(error) == "[configuration] Fatal error"

    def test_recoverable_error_carries_subsystem(self):
        """RecoverableError is logged but does not abort startup."""
        from config.phases import RecoverableError

        error = RecoverableError("resources", "Non-fatal", subsystem="icons")

        assert error.phase == "resources"
        assert error.subsystem == "icons"
        assert str(error) == "[resources] Non-fatal"

    def test_solution_prompt_cancelled(self):
        """SolutionPromptCancelled represents a clean user cancellation."""
        from config.phases import SolutionPromptCancelled

        error = SolutionPromptCancelled()

        assert isinstance(error, Exception)
        assert str(error) == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])