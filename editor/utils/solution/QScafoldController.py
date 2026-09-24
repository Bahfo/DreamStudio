"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""

import logging
import os

from PyQt6.QtWidgets import QMessageBox

from editor import *
from editor.init.project_bootstrap import ProjectBootstrap
from editor.utils.solution.manifests_scanner import load_manifest
from editor.utils.solution.theme import center_on_screen, inherit_theme
from editor.utils.solution.theme import center_on_screen_show, inherit_theme

logger = logging.getLogger(__name__)


class ScaffoldController:
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


class QScaffoldProgressDialog(QDialog):
    def __init__(
        self,
        parent=None,
        title="Creating Project",
        description="",
    ) -> None:
        super().__init__(parent)
        self.success = False
        self.cancelled = False
        self.failed = False

        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        heading = QLabel(description)
        heading.setObjectName("ScaffoldHeading")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        self._step_label = QLabel("Initializing...")
        self._step_label.setObjectName("ScaffoldStep")
        self._step_label.setWordWrap(True)
        layout.addWidget(self._step_label)

        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress.setFixedHeight(8)
        layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("ScaffoldProgress")
        self._progress_label.setWordWrap(True)
        layout.addWidget(self._progress_label)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._request_cancel)
        layout.addWidget(self._cancel_btn, 0, Qt.AlignmentFlag.AlignRight)

        styled = inherit_theme(self)
        if not styled:
            self._apply_style()

    def showEvent(self, event) -> None:
        """Center the dialog on the screen each time it is shown."""
        center_on_screen_show(self, event)

    def bind(self, bootstrap) -> None:
        """Connect a ProjectBootstrap instance's signals to the dialog.

        Args:
            bootstrap: The scaffold-running ProjectBootstrap instance.
        """
        bootstrap.step_changed.connect(self._on_step_changed)
        bootstrap.step_progress.connect(self._on_step_progress)
        bootstrap.step_failed.connect(self._on_step_failed)
        bootstrap.cancelled.connect(self._on_cancelled)
        bootstrap.finished.connect(self._on_finished)
        self._cancel_btn.clicked.connect(bootstrap.request_cancel)

    def _on_step_changed(self, _name: str, description: str) -> None:
        self._step_label.setText(description)

    def _on_step_progress(self, text: str) -> None:
        self._progress_label.setText(text)
        self._progress.setValue((self._progress.value() + 1) % 1000)

    def _on_step_failed(self, _step: str, _error: str) -> None:
        self.failed = True
        self._step_label.setText("Scaffolding failed — rolling back changes...")

    def _on_cancelled(self) -> None:
        self.cancelled = True
        self._step_label.setText("Cancelled — keeping the created structure as-is.")
        self._cancel_btn.setEnabled(False)

    def _on_finished(self, success: bool) -> None:
        self.success = success
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        if not self.cancelled:
            self._cancel_btn.setEnabled(False)
        self.accept()

    def _request_cancel(self) -> None:
        """Allow the cancel button to trigger the worker's safe stop."""
        self.cancel_clicked = True
        self._cancel_btn.setEnabled(False)
        self._step_label.setText("Stopping after the current step...")
