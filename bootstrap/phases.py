"""
Startup phases for DreamStudio bootstrap.

Each phase is a callable that receives a PhaseContext and raises
StartupError on critical failure or RecoverableError on recoverable issues.
"""

import sys
import logging
import traceback

from dataclasses import dataclass, field
from typing import Any

from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


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
    ctx.splash = SplashController()

    ctx.registry.register("config_service", ctx.config_service)
    ctx.registry.register("resource_manager", ctx.resource_manager)

    logger.info("Phase 2 completed: Bootstrap services created")


# ------------------------------------------------------------------
# Phase 3: Configuration
# ------------------------------------------------------------------


def phase_configuration(ctx: PhaseContext) -> None:
    """Load, validate, and repair configuration."""
    logger.info("Phase 3: Configuration")

    try:
        cfg = ctx.config_service.load()
        ctx.registry.register("config", cfg)
        logger.info(
            "Phase 3 completed: Configuration loaded (version %s)", cfg.get("version")
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
# Phase 4: Resources
# ------------------------------------------------------------------


def phase_resources(ctx: PhaseContext) -> None:
    """Load themes, icons, fonts. Use fallbacks for missing items."""
    logger.info("Phase 4: Resource loading")

    theme_name = ctx.config_service.get("editor", {}).get("theme", "dark")
    theme_content = ctx.resource_manager.load_theme(theme_name)
    if not theme_content:
        logger.warning("No theme content loaded, IDE will use Qt defaults")
        ctx.warnings.append("Theme loading produced empty content")

    asset_checks = ctx.resource_manager.verify_assets()
    missing_dirs = [k for k, v in asset_checks.items() if not v]
    if missing_dirs:
        logger.warning("Missing asset directories: %s", missing_dirs)
        ctx.warnings.append(f"Missing asset dirs: {missing_dirs}")

    ctx.registry.register("theme_content", theme_content)
    logger.info("Phase 4 completed: Resources loaded")


# ------------------------------------------------------------------
# Phase 5: Core services
# ------------------------------------------------------------------


def phase_core_services(ctx: PhaseContext) -> None:
    """Initialize startup-critical services only."""
    logger.info("Phase 5: Core services")

    ctx.registry.register("base_dir", ctx.base_dir)
    ctx.registry.register("app", ctx.app)

    logger.info("Phase 5 completed: Core services registered")


# ------------------------------------------------------------------
# Phase 6: Main window
# ------------------------------------------------------------------


def phase_main_window(ctx: PhaseContext) -> None:
    """Create DreamStudio main window hidden and disabled until boot completes.

    The registry is injected into DreamStudio so that it can obtain its
    startup dependencies (config, theme, resource_manager) from the
    bootstrap kernel rather than locating them independently.
    """
    logger.info("Phase 6: Main window creation")

    sys.path.insert(0, ctx.base_dir)

    from ui_build import DreamStudio

    window = DreamStudio(registry=ctx.registry)
    window.setEnabled(False)
    window.hide()
    ctx.registry.register("main_window", window)

    app = QApplication.instance()
    if app:
        app.processEvents()

    logger.info("Phase 6 completed: DreamStudio window created (hidden, disabled)")


# ------------------------------------------------------------------
# Phase 7: Language plugins
# ------------------------------------------------------------------


def phase_language_plugins(ctx: PhaseContext) -> None:
    """Register language plugins with the LanguageRegistry.

    This phase runs after the main window is created (so that
    ``base_dir`` is on ``sys.path``) and before the final finish phase.
    Plugin failures are recoverable — they log warnings but do not
    prevent the IDE from starting.
    """
    logger.info("Phase 7: Language plugins")

    try:
        from editor.texteditor.plugins.registration import register_python_language

        success = register_python_language()
        if success:
            logger.info("Phase 7 completed: Python language plugin registered")
        else:
            msg = "Python language plugin registration returned False"
            logger.warning(msg)
            ctx.warnings.append(msg)
    except Exception as exc:
        msg = f"Python language plugin registration failed: {exc}"
        logger.warning(msg)
        ctx.warnings.append(msg)

    logger.info("Phase 7 completed: Language plugins")


# ------------------------------------------------------------------
# Phase 8: Finish
# ------------------------------------------------------------------


def phase_finish(ctx: PhaseContext) -> None:
    """Finalize boot. Window stays hidden; caller shows it after run()."""
    logger.info("Phase 8: Finish")

    app = QApplication.instance()
    if app:
        app.processEvents()

    logger.info("Phase 8 completed: DreamStudio ready")


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
