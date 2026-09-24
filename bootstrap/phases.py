"""
Startup phases for DreamStudio bootstrap.

Each phase is a callable that receives a PhaseContext and raises
StartupError on critical failure or RecoverableError on recoverable issues.
"""

import os
import sys
import json
import logging
import traceback

from dataclasses import dataclass, field
from typing import Any
from pathlib import Path

from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


def _get_notification_manager():
    """Lazily import notification manager without creating a static bootstrap->editor dependency."""
    try:
        import importlib

        mod = importlib.import_module("editor.utils.notifications.notification_manager")
        return mod.get_notification_manager()
    except Exception:

        class _Dummy:
            def add_warning(self, *a, **kw):
                pass

            def add_error(self, *a, **kw):
                pass

            def add_success(self, *a, **kw):
                pass

            def add_info(self, *a, **kw):
                pass

        return _Dummy()


def _notify(kind: str, title: str, message: str, source: str = "Startup") -> None:
    """Best-effort notification without failing startup."""
    try:
        mgr = _get_notification_manager()
        getattr(mgr, kind)(title, message, source)
    except Exception:
        pass


class StartupError(Exception):
    """Critical startup failure that prevents the IDE from running."""

    def __init__(self, phase: str, message: str, details: str = "") -> None:
        self.phase = phase
        self.details = details
        super().__init__(f"[{phase}] {message}")


class RecoverableError(Exception):
    """Non-critical failure that should be logged but not fatal."""

    def __init__(self, phase: str, message: str, subsystem: str = "") -> None:
        self.phase = phase
        self.subsystem = subsystem
        super().__init__(f"[{phase}] {message}")


class SolutionPromptCancelled(Exception):
    """Raised when the user closes the solution start window without a choice.

    This is a graceful shutdown signal, not a failure: the IDE quits cleanly
    instead of entering recovery mode.
    """


@dataclass
class PhaseContext:
    """Mutable context passed through startup phases."""

    base_dir: str = ""
    app: Any = None
    registry: Any = None
    config_service: Any = None
    resource_manager: Any = None
    splash: Any = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    workspace_path: str = ""
    pending_scaffold: dict = field(default_factory=dict)


# ------------------------------------------------------------------
# Phase 1: Application startup
# ------------------------------------------------------------------


def phase_application_startup(ctx: PhaseContext) -> None:
    """Configure existing QApplication, set metadata, initialize logging."""
    logger.info("Phase 1: Application startup")
    _configure_logging()

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setApplicationName("DreamStudio")
        app.setStyle("Fusion")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("EXcellent TechStacks")
    ctx.app = app
    logger.info("Phase 1 completed: QApplication ready")


# ------------------------------------------------------------------
# Phase 2: Bootstrap init
# ------------------------------------------------------------------


def phase_bootstrap_init(ctx: PhaseContext) -> None:
    """Initialize BootstrapManager dependencies."""
    logger.info("Phase 2: Bootstrap initialization")

    from bootstrap.registry import ServiceRegistry
    from bootstrap.config import ConfigurationService
    from bootstrap.resources import ResourceManager
    from bootstrap.splash import SplashController

    ctx.registry = ServiceRegistry()
    ctx.config_service = ConfigurationService(ctx.base_dir)
    ctx.resource_manager = ResourceManager(ctx.base_dir)
    if ctx.splash is None:
        ctx.splash = SplashController()

    ctx.registry.register("config_service", ctx.config_service)
    ctx.registry.register("resource_manager", ctx.resource_manager)

    logger.info("Phase 2 completed: Bootstrap services created")


# ------------------------------------------------------------------
# Phase 3: User home directory setup
# ------------------------------------------------------------------


def phase_user_home_setup(ctx: PhaseContext) -> None:
    """Ensure ~/.dreamstudio/ directory structure exists.

    Creates the following structure if missing:
        ~/.dreamstudio/
            remote/
                configs.json
            settings/
                user_settings.json
            plugins/
                (can be empty)

    If any file (except plugins directory) is missing, it will be
    recreated with default values.
    """
    logger.info("Phase 3: User home directory setup")

    home_dir = Path.home()
    dreamstudio_home = home_dir / ".dreamstudio"

    # Directory structure definitions
    directories = {
        "remote": dreamstudio_home / "remote",
        "settings": dreamstudio_home / "settings",
        "plugins": dreamstudio_home / "plugins",
    }

    # Default file contents
    default_files = {
        "remote": {
            "path": directories["remote"] / "configs.json",
            "content": {"version": 1, "connections": []},
        },
        "settings": {
            "path": directories["settings"] / "user_settings.json",
            "content": {
                "version": 1,
                "editor": {"theme": "dark", "font_size": 12},
                "workspace": {"last_directory": ""},
                "solutions": {"recent": []},
            },
        },
    }

    try:
        # Create all directories
        for dir_name, dir_path in directories.items():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug("Ensured directory exists: %s", dir_path)

        # Create config files if missing
        for file_key, file_info in default_files.items():
            file_path = file_info["path"]
            if not file_path.is_file():
                logger.warning("Config file not found, creating default: %s", file_path)
                _notify(
                    "add_warning",
                    "Config Missing",
                    f"Configuration file not found: {file_path.name}. Created with default values.",
                )
                with open(file_path, "w", encoding="utf-8") as fh:
                    json.dump(file_info["content"], fh, indent=4)
            else:
                # Validate file is readable JSON
                try:
                    with open(file_path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    if not isinstance(data, dict):
                        raise ValueError("Config is not a JSON object")
                except (json.JSONDecodeError, ValueError) as exc:
                    logger.warning(
                        "Config file invalid, recreating: %s (%s)", file_path, exc
                    )
                    _notify(
                        "add_warning",
                        "Config Corrupted",
                        f"Configuration file is corrupted: {file_path.name}. Recreated with default values.",
                    )
                    with open(file_path, "w", encoding="utf-8") as fh:
                        json.dump(file_info["content"], fh, indent=4)

        logger.info("Phase 3 completed: User home directory setup")

    except Exception as exc:
        details = traceback.format_exc()
        logger.error("User home directory setup failed: %s\n%s", exc, details)
        _notify(
            "add_error", "Startup Error", "Failed to set up user directory structure."
        )
        raise StartupError(
            "user_home_setup",
            "Failed to create ~/.dreamstudio/ directory structure.",
            details,
        ) from exc


# ------------------------------------------------------------------
# Phase 4: Configuration
# ------------------------------------------------------------------


def phase_configuration(ctx: PhaseContext) -> None:
    """Load, validate, and repair configuration."""
    logger.info("Phase 4: Configuration")

    try:
        cfg = ctx.config_service.load()
        ctx.registry.register("config", cfg)
        logger.info(
            "Phase 4 completed: Configuration loaded (version %s)", cfg.get("version")
        )
    except Exception as exc:
        details = traceback.format_exc()
        logger.error("Configuration load failed: %s\n%s", exc, details)
        raise StartupError(
            "configuration",
            "Configuration cannot be loaded or repaired.",
            details,
        ) from exc


# ------------------------------------------------------------------
# Phase 5: Resources
# ------------------------------------------------------------------


def phase_resources(ctx: PhaseContext) -> None:
    """Load themes, icons, fonts. Use fallbacks for missing items."""
    logger.info("Phase 5: Resource loading")

    theme_name = ctx.config_service.get("editor", {}).get("theme", "dark")
    theme_content = ctx.resource_manager.load_theme(theme_name)
    if not theme_content:
        logger.warning("No theme content loaded, IDE will use Qt defaults")
        ctx.warnings.append("Theme loading produced empty content")
        _notify(
            "add_warning",
            "Theme Missing",
            "Theme could not be loaded. Using default appearance.",
        )

    asset_checks = ctx.resource_manager.verify_assets()
    missing_dirs = [k for k, v in asset_checks.items() if not v]
    if missing_dirs:
        logger.warning("Missing asset directories: %s", missing_dirs)
        ctx.warnings.append(f"Missing asset dirs: {missing_dirs}")
        _notify(
            "add_warning",
            "Assets Missing",
            f"Some UI assets are missing: {', '.join(missing_dirs)}",
        )

    # Register bundled fonts so QFont("Space Mono"), QFont("Montserrat"),
    # etc. resolve to the actual font files rather than system fallbacks.
    try:
        from fonts.font_strapper import Fonts

        Fonts.init()
        logger.info("Bundled fonts registered")
    except Exception as exc:
        logger.warning("Bundled font registration failed: %s", exc)
        ctx.warnings.append(f"Font loading failed: {exc}")
        _notify(
            "add_warning",
            "Fonts Error",
            f"Custom fonts failed to load: {exc}. System fonts will be used.",
        )

    ctx.registry.register("theme_content", theme_content)
    logger.info("Phase 5 completed: Resources loaded")


# ------------------------------------------------------------------
# Phase 6: Core services
# ------------------------------------------------------------------


def phase_core_services(ctx: PhaseContext) -> None:
    """Initialize startup-critical services only."""
    logger.info("Phase 6: Core services")

    ctx.registry.register("base_dir", ctx.base_dir)
    ctx.registry.register("app", ctx.app)

    import importlib

    workspace_type = importlib.import_module("editor.utils.solution.workspace_service")
    workspace = workspace_type.WorkspaceService()
    ctx.registry.register("workspace", workspace)

    logger.info("Phase 6 completed: Core services registered")


# ------------------------------------------------------------------
# Phase 7: Solution prompt
# ------------------------------------------------------------------


def _record_workspace_selection(ctx: PhaseContext, path: str) -> None:
    """Persist a chosen solution path and refresh the config entry.

    Args:
        ctx: The current boot phase context.
        path: Absolute solution path selected by the user.
    """
    try:
        config_service = ctx.registry.get("config_service")
        workspace_cfg = dict(config_service.get("workspace", {}))
        workspace_cfg["last_directory"] = path
        config_service.set("workspace", workspace_cfg)
    except Exception as exc:
        logger.warning("Could not persist workspace.last_directory: %s", exc)


def phase_solution_prompt(ctx: PhaseContext) -> None:
    """Show the solution start window and block until a solution is chosen.

    When a project path was supplied on the command line (``--project``) the
    prompt is skipped. Afterwards ``ctx.workspace_path`` holds the selected
    solution root and ``ctx.pending_scaffold`` describes a created project
    that still needs scaffolding after the main window is revealed.

    Raises:
        SolutionPromptCancelled: When the user closes the start window
            without selecting or creating a solution.
    """
    logger.info("Phase 7: Solution prompt")

    if ctx.workspace_path:
        logger.info("Workspace provided on command line; skipping prompt")
        if ctx.splash:
            try:
                ctx.splash.close()
            except Exception:
                pass
        return

    window = None
    try:
        import importlib

        start_window_mod = importlib.import_module(
            "editor.utils.solution.startup_window"
        )
        window = start_window_mod.SolutionStartWindow(registry=ctx.registry)
        selection, scaffold = _run_start_window(window, ctx)
    except SolutionPromptCancelled:
        raise
    except Exception as exc:
        raise StartupError(
            "solution_prompt",
            "The solution start window could not be opened.",
            traceback.format_exc(),
        ) from exc

    if selection is None:
        raise SolutionPromptCancelled()

    ctx.workspace_path = selection.get("path", "")
    ctx.pending_scaffold = scaffold or {}

    if ctx.workspace_path:
        _record_workspace_selection(ctx, ctx.workspace_path)
        try:
            import importlib

            recent_mod = importlib.import_module("editor.utils.solution.recent")
            recent_mod.add_or_update(
                ctx.workspace_path,
                name=selection.get("name", ""),
                project_type=selection.get("project_type", ""),
            )
        except Exception:
            pass

    logger.info("Solution selected: %s", ctx.workspace_path or "(none)")


def _run_start_window(window, ctx: PhaseContext):
    """Run the start window's nested event loop and return its choice.

    Returns:
        Tuple of ``(selection_dict_or_None, scaffold_dict_or_None)``.
    """
    from PyQt6.QtCore import QEventLoop

    if ctx.splash:
        try:
            ctx.splash.close()
        except Exception:
            pass

    result: dict = {}
    loop = QEventLoop()
    window.solution_selected.connect(
        lambda selection: _complete_selection(result, selection, loop)
    )
    window.prompt_cancelled.connect(loop.quit)
    window.showMaximized()
    window.setEnabled(True)
    loop.exec()
    try:
        window.close()
        window.deleteLater()
    except Exception:
        pass
    selection = result.get("selection")
    scaffold = result.get("scaffold")
    return selection, scaffold


def _complete_selection(result: dict, selection: dict, loop) -> None:
    """Store the pending selection and stop the start-window event loop.

    Args:
        result: Mutable dict shared with the phase's local event loop.
        selection: The chosen solution metadata dict.
        loop: The running ``QEventLoop`` to quit.
    """
    result["selection"] = selection
    result["scaffold"] = (
        selection.get("_scaffold") if isinstance(selection, dict) else None
    )
    loop.quit()


# ------------------------------------------------------------------
# Phase 8: Main window
# ------------------------------------------------------------------


def phase_main_window(ctx: PhaseContext) -> None:
    """Create DreamStudio main window hidden and disabled until boot completes.

    The registry is injected into DreamStudio so that it can obtain its
    startup dependencies (config, theme, resource_manager) from the
    bootstrap kernel rather than locating them independently.
    """
    logger.info("Phase 8: Main window creation")

    if ctx.base_dir not in sys.path:
        sys.path.insert(0, ctx.base_dir)

    from ui_build import DreamStudio

    window = DreamStudio(registry=ctx.registry, current_workspace=ctx.workspace_path)
    window.setEnabled(False)
    window.hide()

    workspace = None
    try:
        workspace = ctx.registry.get("workspace")
        workspace.attach_window(window)
        if ctx.workspace_path:
            workspace.open_workspace(ctx.workspace_path)
    except Exception:
        pass

    ctx.registry.register("main_window", window)

    app = QApplication.instance()
    if app:
        app.processEvents()

    logger.info("Phase 8 completed: DreamStudio window created (hidden, disabled)")


# ------------------------------------------------------------------
# Phase 9: Language plugins
# ------------------------------------------------------------------


def phase_language_plugins(ctx: PhaseContext) -> None:
    """Register language plugins with the LanguageRegistry.

    This phase runs after the main window is created and, crucially, after
    the user has chosen a solution, so plugin/highlighting work is deferred
    until a project is open. Plugin failures are recoverable — they log
    warnings but do not prevent the IDE from starting.
    """
    logger.info("Phase 9: Language plugins")

    try:
        import importlib

        _mod = importlib.import_module("editor.Ironica.plugins.registration")
        warnings = _mod.register_all_languages()
        ctx.warnings.extend(warnings)
    except Exception as exc:
        msg = f"Language plugin registration failed: {exc}"
        logger.warning(msg)
        ctx.warnings.append(msg)

    logger.info("Phase 9 completed: Language plugins")


# ------------------------------------------------------------------
# Phase 10: Finish
# ------------------------------------------------------------------


def phase_finish(ctx: PhaseContext) -> None:
    """Finalize boot. Window stays hidden; caller shows it after run()."""
    logger.info("Phase 10: Finish")

    app = QApplication.instance()
    if app:
        app.processEvents()

    _notify("add_success", "Startup Complete", "DreamStudio is ready.")

    logger.info("Phase 10 completed: DreamStudio ready")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _configure_logging() -> None:
    """Configure root logger for startup output."""
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)

    bootstrap_logger = logging.getLogger("bootstrap")
    bootstrap_logger.setLevel(logging.DEBUG)
