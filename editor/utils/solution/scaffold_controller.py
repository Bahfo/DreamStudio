"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Controller that turns a created solution's pending-scaffold spec into an
actual scaffolded project. Flow: confirm with the user (listing the packages
about to be installed), run the ProjectBootstrapWorker in a background
thread, and reflect progress in a blocking modal dialog over the IDE.
On cancel, scaffolding stops at the current step and the partial structure is
kept (no rollback) so the IDE opens with whatever was already created.
"""

import logging
import os

from PyQt6.QtWidgets import QMessageBox

from editor import *
from editor.init.project_bootstrap import ProjectBootstrap
from editor.utils.solution.manifest_scan import load_manifest
from editor.utils.solution.scaffold_dialog import QScaffoldProgressDialog
from editor.utils.solution.theme import center_on_screen, inherit_theme

logger = logging.getLogger(__name__)


class ScaffoldController:
    """Runs the post-creation scaffolding for a brand-new solution.

    Attributes:
        finished_ok (bool): True when the worker reported success.
        user_cancelled (bool): True when the user requested a safe cancel.
    """

    def __init__(self, window, scaffold: dict) -> None:
        """Build the controller.

        Args:
            window: The revealed DreamStudio main window.
            scaffold: Pending-scaffold dict emitted by the solution prompt
                with ``target``, ``name``, ``project_type`` and
                ``manifest_path`` keys.
        """
        self._window = window
        self._scaffold = scaffold
        self.finished_ok = False
        self.user_cancelled = False

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run_blocking(self) -> None:
        """Confirm, scaffold, and refresh the IDE — all blocking on the GUI thread."""
        manifest_path = self._scaffold.get("manifest_path", "")
        if not manifest_path or not os.path.isfile(manifest_path):
            logger.warning("Scaffolding skipped: no manifest at %r", manifest_path)
            return

        try:
            manifest = load_manifest(manifest_path)
        except Exception:
            logger.warning(
                "Scaffolding skipped: manifest unreadable at %r", manifest_path
            )
            return

        packages = self._collect_packages(manifest)
        if not self._confirm(packages):
            return

        bootstrap = ProjectBootstrap(
            manifest_path=manifest_path,
            target_path=self._scaffold["target"],
            requested_project_type=self._scaffold.get("project_type", ""),
            interpreter_location=None,
        )

        description = self._scaffold.get("name", "Project")
        dialog = QScaffoldProgressDialog(
            self._window, description=f"Creating {description}..."
        )
        dialog.bind(bootstrap)
        bootstrap.start()
        dialog.exec()

        self.finished_ok = dialog.success and not dialog.cancelled and not dialog.failed
        self.user_cancelled = dialog.cancelled

        self._refresh_ide()
        self._summarize_after_close()

    # ------------------------------------------------------------------
    # Pre-prompt
    # ------------------------------------------------------------------

    def _collect_packages(self, manifest: dict) -> list[str]:
        """Extract dependency names from the manifest's requirements template.

        Args:
            manifest: The raw YAML manifest dict.

        Returns:
            List of package requirement lines (e.g. ``PyQt6>=6.6.0``).
        """
        packages: list[str] = []
        templates = (manifest.get("initialization") or {}).get("templates") or []
        for template in templates:
            if not isinstance(template, dict):
                continue
            target = template.get("target", "")
            contents = template.get("contents", "")
            if os.path.basename(target) == "requirements.txt" and isinstance(
                contents, str
            ):
                packages = self._parse_requirements(contents)
                break
        return packages

    def _parse_requirements(self, contents: str) -> list[str]:
        """Return non-comment, non-blank lines from a requirements.txt body."""
        lines = []
        for line in contents.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(stripped)
        return lines

    def _confirm(self, packages: list[str]) -> bool:
        """Ask the user to agree before heavy work (venv + pip install) begins.

        Args:
            packages: Package requirement lines to display.

        Returns:
            True when the user agrees, False to abort creation.
        """
        name = self._scaffold.get("name", "Project")
        body = f"DreamStudio is about to scaffold '{name}'.\n"
        if packages:
            body += "\nPackages that will be installed:\n"
            body += "\n".join(f"  • {pkg}" for pkg in packages)
        body += "\n\nThis may take a while. Continue?"

        box = QMessageBox(self._window)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Create Solution")
        box.setText(body)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        inherit_theme(box)
        center_on_screen(box)
        reply = box.exec()
        return reply == QMessageBox.StandardButton.Yes

    # ------------------------------------------------------------------
    # Post-run
    # ------------------------------------------------------------------

    def _refresh_ide(self) -> None:
        """Re-point path-dependent panels at the scaffolded solution root."""
        window = self._window
        target = self._scaffold.get("target", "")
        if not target:
            return
        workspace = getattr(window, "currentDirectory", "") or target
        try:
            window.currentDirectory = target
        except AttributeError:
            pass

        try:
            hero = window.hero_window
            explorer = hero._solution_explorer
            if hasattr(explorer, "set_root_path"):
                explorer.set_root_path(target)
            if hasattr(hero._source_control, "set_workspace"):
                hero._source_control.set_workspace(target)
        except AttributeError:
            pass

        try:
            hero = window.hero_window
            problems = hero._lower_widget.problems_window
            problems.run_workspace_analysis(target)
        except AttributeError:
            pass

    def _summarize_after_close(self) -> None:
        """Notify the user of the final scaffolding outcome."""
        name = self._scaffold.get("name", "Project")
        if self.finished_ok:
            self._notify(
                "add_success",
                "Solution Created",
                f"'{name}' was scaffolded successfully.",
            )
        elif self.user_cancelled:
            self._notify(
                "add_warning",
                "Creation Cancelled",
                f"Stopped after the current step. '{name}' keeps its partial structure.",
            )
        else:
            self._notify(
                "add_error",
                "Creation Failed",
                f"'{name}' could not be scaffolded. Created resources were rolled back.",
            )

    def _notify(self, kind: str, title: str, message: str) -> None:
        """Route a notification through the IDE's notification manager."""
        try:
            manager = get_notification_manager()
            if manager:
                method = getattr(manager, kind, None) or getattr(manager, "add_info")
                method(title, message)
        except Exception:
            logger.info("%s: %s — %s", title, message, kind)
