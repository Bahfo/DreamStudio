"""
BootstrapManager: startup orchestrator for DreamStudio.

Coordinates all startup phases, handles errors at the appropriate
severity level, and decides whether to proceed normally or enter
recovery mode.
"""

import os
import sys
import logging
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

from bootstrap.phases import (
    PhaseContext,
    StartupError,
    RecoverableError,
    phase_application_startup,
    phase_bootstrap_init,
    phase_configuration,
    phase_resources,
    phase_core_services,
    phase_main_window,
    phase_language_plugins,
    phase_finish,
)

logger = logging.getLogger(__name__)


@dataclass
class StartupResult:
    """Outcome of a bootstrap attempt."""
    success: bool = False
    window: Any = None
    app: Any = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    failed_phase: str = ""


class BootstrapManager:
    """
    Orchestrates the startup pipeline.

    Phases execute in strict order. A critical failure at any phase
    stops the pipeline and routes to RecoveryWindow. Recoverable failures
    are logged and appended to warnings without halting startup.
    """

    # Default phase pipeline in execution order.
    _DEFAULT_PHASES: list[tuple[str, Callable]] = [
        ("application_startup", phase_application_startup),
        ("bootstrap_init", phase_bootstrap_init),
        ("configuration", phase_configuration),
        ("resources", phase_resources),
        ("core_services", phase_core_services),
        ("main_window", phase_main_window),
        ("language_plugins", phase_language_plugins),
        ("finish", phase_finish),
    ]

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self._phases = list(self._DEFAULT_PHASES)
        self._custom_phases: list[tuple[str, Callable]] = []
        self._ctx = PhaseContext(base_dir=self._base_dir)
        logger.info("BootstrapManager created (base_dir=%s)", self._base_dir)

    # ------------------------------------------------------------------
    # Phase registration (extensibility)
    # ------------------------------------------------------------------

    def add_phase(self, name: str, phase_fn: Callable, after: str | None = None) -> None:
        """Insert a custom phase into the pipeline.

        If *after* is given, the phase is placed immediately after the
        named phase. Otherwise it is appended before the 'finish' phase.
        """
        entry = (name, phase_fn)
        if after is None:
            insert_idx = len(self._phases) - 1
            self._phases.insert(insert_idx, entry)
        else:
            for i, (pname, _) in enumerate(self._phases):
                if pname == after:
                    self._phases.insert(i + 1, entry)
                    break
            else:
                logger.warning("Phase '%s' not found, appending '%s'", after, name)
                self._phases.insert(len(self._phases) - 1, entry)
        self._custom_phases.append(entry)
        logger.info("Custom phase registered: %s (after=%s)", name, after)

    # ------------------------------------------------------------------
    # Startup execution
    # ------------------------------------------------------------------

    def run(self, splash: Any = None) -> StartupResult:
        """Execute the full startup pipeline.

        Returns a StartupResult indicating success or failure.
        """
        result = StartupResult()
        self._ctx.splash = splash

        total = len(self._phases)
        if splash:
            splash.set_step_count(total)

        for idx, (name, phase_fn) in enumerate(self._phases):
            if splash and splash.is_visible:
                splash.update_status(f"Running: {name}", step=idx)

            logger.info("=== Phase %d/%d: %s ===", idx + 1, total, name)
            try:
                phase_fn(self._ctx)
                logger.info("Phase %s completed", name)
            except StartupError as exc:
                logger.critical("Critical failure in phase '%s': %s", name, exc)
                result.failed_phase = name
                result.errors.append(str(exc))
                if self._ctx.errors:
                    result.errors.extend(self._ctx.errors)
                self._enter_recovery(str(exc), exc.details, splash)
                return result
            except RecoverableError as exc:
                logger.warning("Recoverable error in phase '%s': %s", name, exc)
                result.warnings.append(str(exc))
            except Exception as exc:
                logger.critical(
                    "Unhandled exception in phase '%s':\n%s",
                    name,
                    traceback.format_exc(),
                )
                result.failed_phase = name
                result.errors.append(f"{name}: {exc}")
                self._enter_recovery(str(exc), traceback.format_exc(), splash)
                return result

        result.success = True
        if self._ctx.registry and self._ctx.registry.has("main_window"):
            result.window = self._ctx.registry.get("main_window")
        else:
            result.window = None
        result.app = self._ctx.app
        result.warnings.extend(self._ctx.warnings)
        logger.info("Startup completed successfully (%d warnings)", len(result.warnings))
        return result

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def _enter_recovery(self, message: str, details: str, splash: Any = None) -> None:
        """Close splash and show RecoveryWindow."""
        if splash and splash.is_visible:
            splash.close()

        from bootstrap.recovery import RecoveryWindow

        window = RecoveryWindow(
            message=message,
            details=details,
            recovery_actions=[("retry", self._retry)],
        )
        window.show()

    def _retry(self) -> None:
        """Attempt startup again from scratch."""
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app:
            for w in app.topLevelWidgets():
                w.close()

        self._ctx = PhaseContext(base_dir=self._base_dir)
        self.run()

    # ------------------------------------------------------------------
    # Context access (for testing / introspection)
    # ------------------------------------------------------------------

    @property
    def context(self) -> PhaseContext:
        return self._ctx

    @property
    def phases(self) -> list[str]:
        return [name for name, _ in self._phases]
