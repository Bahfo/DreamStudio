"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for BootstrapManager phase orchestration.
"""

from unittest.mock import MagicMock

import pytest


class TestBootstrapManager:
    """Tests for BootstrapManager phase orchestration."""

    def test_manager_creation(self):
        """BootstrapManager stores its base and project directories."""
        from config.manager import BootstrapManager

        manager = BootstrapManager(base_dir="/test", project_dir=None)

        assert manager._base_dir == "/test"
        assert manager._project_dir == ""

    def test_default_phases_order(self):
        """Default phases are in the documented fixed order."""
        from config.manager import BootstrapManager

        phase_names = [name for name, _ in BootstrapManager._DEFAULT_PHASES]
        expected = [
            "application_startup",
            "bootstrap_init",
            "user_home_setup",
            "configuration",
            "resources",
            "core_services",
            "solution_prompt",
            "main_window",
            "language_plugins",
            "finish",
        ]

        assert phase_names == expected

    def test_add_phase_inserts_correctly(self):
        """add_phase inserts a phase directly after the named phase."""
        from config.manager import BootstrapManager

        manager = BootstrapManager(base_dir="/test", project_dir=None)
        original_len = len(manager._phases)
        phase_names = [name for name, _ in manager._phases]
        assert "finish" in phase_names

        def dummy_phase(ctx):
            pass

        manager.add_phase("custom_phase", dummy_phase, after="configuration")

        assert len(manager._phases) == original_len + 1
        names = [name for name, _ in manager._phases]
        assert names.index("custom_phase") == names.index("configuration") + 1

    def test_add_phase_unknown_anchor_appends_before_finish(self):
        """Unknown anchors fall back to inserting before the final phase."""
        from config.manager import BootstrapManager

        manager = BootstrapManager(base_dir="/test", project_dir=None)

        manager.add_phase("orphan_phase", lambda ctx: None, after="missing_phase")

        names = [name for name, _ in manager._phases]
        assert names[-1] == "finish"
        assert names[-2] == "orphan_phase"

    def test_startup_result_defaults(self):
        """StartupResult has documented defaults."""
        from config.manager import StartupResult

        result = StartupResult()

        assert result.success is False
        assert result.window is None
        assert result.app is None
        assert result.cancelled is False
        assert result.failed_phase == ""
        assert result.errors == []
        assert result.warnings == []
        assert result.scaffold == {}

    def test_run_executes_custom_phase_pipeline(self, qapp):
        """run() executes phases in order and returns success."""
        from config.manager import BootstrapManager

        manager = BootstrapManager(base_dir="/test", project_dir=None)
        executed = []

        manager._phases = [
            ("first", lambda ctx: executed.append("first")),
            ("second", lambda ctx: executed.append("second")),
        ]

        result = manager.run(splash=None)

        assert executed == ["first", "second"]
        assert result.success is True
        assert result.window is None
        assert result.errors == []

    def test_run_recovers_from_startup_error(self, qapp):
        """StartupError marks the failed phase and does not escape run()."""
        from config import manager as manager_module
        from config.manager import BootstrapManager
        from config.phases import StartupError

        def failing_phase(ctx):
            raise StartupError("configuration", "boom", details="trace")

        manager = BootstrapManager(base_dir="/test", project_dir=None)
        manager._phases = [("configuration", failing_phase)]

        recovery = MagicMock()
        with pytest.MonkeyPatch.context() as patcher:
            patcher.setattr(manager_module, "RecoveryWindow", recovery, raising=False)
            with pytest.MonkeyPatch.context() as patcher2:
                patcher2.setattr(
                    "config.manager.BootstrapManager._enter_recovery",
                    lambda self, message, details, splash=None: None,
                )
                result = manager.run(splash=None)

        assert result.success is False
        assert result.failed_phase == "configuration"
        assert result.errors

    def test_run_records_recoverable_error(self, qapp):
        """RecoverableError is recorded as a warning and the pipeline continues."""
        from config.manager import BootstrapManager
        from config.phases import RecoverableError

        def recoverable_phase(ctx):
            raise RecoverableError("resources", "minor problem")

        manager = BootstrapManager(base_dir="/test", project_dir=None)
        executed = []
        manager._phases = [
            ("resources", recoverable_phase),
            ("after", lambda ctx: executed.append("after")),
        ]

        result = manager.run(splash=None)

        assert executed == ["after"]
        assert result.success is True
        assert any("minor problem" in warning for warning in result.warnings)

    def test_run_handles_solution_prompt_cancelled(self, qapp):
        """SolutionPromptCancelled produces a clean cancelled result."""
        from config.manager import BootstrapManager
        from config.phases import SolutionPromptCancelled

        def cancel_phase(ctx):
            raise SolutionPromptCancelled()

        manager = BootstrapManager(base_dir="/test", project_dir=None)
        manager._phases = [("solution_prompt", cancel_phase)]

        result = manager.run(splash=None)

        assert result.success is False
        assert result.cancelled is True
        assert result.failed_phase == "solution_prompt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])