"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Unit and integration tests for the startup kernel (``config/`` package,
formerly referred to as ``bootstrap/`` in older documentation).
"""

import json
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


class TestServiceRegistry:
    """Tests for ServiceRegistry key-value storage."""

    def test_register_and_get(self):
        """Register and retrieve a service by string key."""
        from config.registry import ServiceRegistry

        registry = ServiceRegistry()
        registry.register("test_key", "test_value")

        assert registry.get("test_key") == "test_value"
        assert registry.has("test_key") is True
        assert registry.has("missing_key") is False

    def test_register_factory_is_lazy(self):
        """Factory services are instantiated only on first access."""
        from config.registry import ServiceRegistry

        registry = ServiceRegistry()
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return f"instance_{call_count}"

        registry.register_factory("lazy_service", factory)
        assert call_count == 0
        assert registry.has("lazy_service") is True

        assert registry.get("lazy_service") == "instance_1"
        assert registry.get("lazy_service") == "instance_1"
        assert call_count == 1
        assert registry.is_initialized("lazy_service") is True

    def test_get_missing_raises(self):
        """Getting a missing key raises KeyError with the key name."""
        from config.registry import ServiceRegistry

        registry = ServiceRegistry()

        with pytest.raises(KeyError, match="nonexistent"):
            registry.get("nonexistent")

    def test_registered_and_initialized_names(self):
        """Registered/initialized name listings reflect registry state."""
        from config.registry import ServiceRegistry

        registry = ServiceRegistry()
        registry.register("eager", object())
        registry.register_factory("lazy", lambda: object())

        assert registry.registered_names() == ["eager", "lazy"]
        assert registry.initialized_names() == ["eager"]

        registry.get("lazy")
        assert registry.initialized_names() == ["eager", "lazy"]

    def test_clear(self):
        """clear removes services, factories, and initialization state."""
        from config.registry import ServiceRegistry

        registry = ServiceRegistry()
        registry.register("eager", object())
        registry.register_factory("lazy", lambda: object())
        registry.get("lazy")

        registry.clear()

        assert registry.registered_names() == []
        assert registry.initialized_names() == []
        assert registry.has("eager") is False
        assert registry.has("lazy") is False


class TestConfigurationService:
    """Tests for ConfigurationService loading and validation."""

    def test_load_creates_default_config(self, temp_config_dir):
        """load() creates .configs/config.json with defaults when missing."""
        from config.config import ConfigurationService

        config_dir = temp_config_dir / ".configs"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        assert not config_file.exists()

        service = ConfigurationService(base_dir=str(temp_config_dir))
        config = service.load()

        assert config_file.exists()
        assert config["version"] == 2
        assert config["editor"]["theme"] == "dark"
        assert config["workspace"]["last_directory"] == ""

    def test_load_existing_config_merges_defaults(self, temp_config_dir):
        """Loading existing config keeps user values and fills defaults."""
        from config.config import ConfigurationService

        config_dir = temp_config_dir / ".configs"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        existing = {
            "version": 2,
            "editor": {"theme": "light"},
            "workspace": {"last_directory": "/home/user"},
        }
        config_file.write_text(json.dumps(existing))

        service = ConfigurationService(base_dir=str(temp_config_dir))
        config = service.load()

        assert config["editor"]["theme"] == "light"
        assert "font_family" in config["editor"]
        assert "font_size" in config["editor"]
        assert config["workspace"]["last_directory"] == "/home/user"

    def test_save_persists_current_data(self, temp_config_dir):
        """save() persists the in-memory config to disk."""
        from config.config import ConfigurationService

        service = ConfigurationService(base_dir=str(temp_config_dir))
        config = service.load()
        config["editor"]["theme"] = "tokyonight"
        service.save()

        saved = json.loads((temp_config_dir / ".configs" / "config.json").read_text())
        assert saved["editor"]["theme"] == "tokyonight"

    def test_repair_corrupt_config(self, temp_config_dir):
        """Corrupt config is repaired and the original backed up."""
        from config.config import ConfigurationService

        config_dir = temp_config_dir / ".configs"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text("{ invalid json")

        service = ConfigurationService(base_dir=str(temp_config_dir))
        config = service.load()

        assert config["version"] == 2
        assert "editor" in config
        assert (temp_config_dir / ".configs" / "config.json.corrupt.bak").exists()
        assert json.loads(config_file.read_text())["version"] == 2

    def test_get_and_set_top_level_sections(self, temp_config_dir):
        """get/set operate on top-level configuration sections."""
        from config.config import ConfigurationService

        service = ConfigurationService(base_dir=str(temp_config_dir))
        service.load()

        editor = service.get("editor")
        assert editor["theme"] == "dark"
        assert service.get("missing", default="fallback") == "fallback"

        service.set("editor", {**editor, "theme": "light"})
        reloaded = ConfigurationService(base_dir=str(temp_config_dir))
        assert reloaded.load()["editor"]["theme"] == "light"

    def test_migrates_version_one_config(self, temp_config_dir):
        """Version 1 configs are migrated to schema version 2."""
        from config.config import ConfigurationService

        config_dir = temp_config_dir / ".configs"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"version": 1, "editor": {"theme": "monokai"}}))

        service = ConfigurationService(base_dir=str(temp_config_dir))
        config = service.load()

        assert config["version"] == 2
        assert config["editor"]["theme"] == "monokai"
        assert json.loads(config_file.read_text())["version"] == 2


class TestResourceManager:
    """Tests for ResourceManager theme and asset loading."""

    def test_load_theme_falls_back_to_dark(self, project_root):
        """Unknown theme names fall back to dark.qss."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        qss = manager.load_theme("nonexistent_theme")

        assert qss
        assert "QMainWindow" in qss
        assert "background-color" in qss

    def test_load_theme_caches(self, project_root):
        """Second load returns the cached content."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        first = manager.load_theme("dark")
        second = manager.load_theme("dark")

        assert first is second
        assert len(manager._theme_cache) == 1

    def test_available_themes(self, project_root):
        """Available themes lists shipped theme names."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        themes = manager.available_themes()

        assert "dark" in themes
        assert "light" in themes
        assert "tokyonight" in themes
        assert len(themes) >= 14

    def test_get_icon_path_resolves_system_icon(self, project_root):
        """Icon resolution finds a shipped system icon."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        path = manager.get_icon_path("add.png", category="system")

        assert path is not None
        assert path.endswith("add.png")

    def test_get_icon_path_missing_returns_none(self, project_root):
        """Missing icons return None and are tracked."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        path = manager.get_icon_path("definitely_missing_icon.png")

        assert path is None
        assert "system/definitely_missing_icon.png" in manager.missing_resources()

    def test_verify_assets(self, project_root):
        """Asset verification reports every expected directory as present."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        result = manager.verify_assets()

        assert isinstance(result, dict)
        assert result
        assert all(result.values()), f"Missing asset directories: {result}"


class TestSplashController:
    """Tests for SplashController construction and timing contract."""

    def test_splash_creation(self, qapp):
        """SplashController can be constructed without showing."""
        from config.splash import SplashController

        splash = SplashController()

        assert splash is not None
        assert splash.is_visible is False
        assert hasattr(splash, "show")
        assert hasattr(splash, "close")
        assert hasattr(splash, "update_status")
        assert hasattr(splash, "set_step_count")

    def test_minimum_visible_duration_constant(self):
        """Splash enforces a five second minimum visible duration."""
        from config import splash as splash_module

        assert splash_module._MIN_VISIBLE_SECONDS == 5.0


class TestRecoveryWindow:
    """Tests for RecoveryWindow crash display."""

    def test_recovery_window_creation(self, qapp):
        """RecoveryWindow renders the supplied message."""
        from config.recovery import RecoveryWindow

        window = RecoveryWindow(message="Test error message")

        assert window._message == "Test error message"
        assert window.windowTitle() == "DreamStudio - Startup Error"
        window.deleteLater()

    def test_recovery_window_custom_details_and_actions(self, qapp):
        """Recovery actions are retained for the retry path."""
        from config.recovery import RecoveryWindow

        called = []
        window = RecoveryWindow(
            title="Custom Title",
            message="Boom",
            details="Traceback",
            recovery_actions=[("retry", lambda: called.append("retry"))],
        )

        assert window.windowTitle() == "Custom Title"
        assert window._details == "Traceback"
        assert window._recovery_actions
        window.deleteLater()


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
