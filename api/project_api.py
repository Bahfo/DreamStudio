"""
ProjectAPI - Wraps project bootstrap and management.

Provides access to project creation, bootstrapping, and environment setup.
"""

from typing import Optional


class ProjectAPI:
    """API for project management."""

    def __init__(self, main_window):
        self._main = main_window

    def bootstrapProject(self, manifest_path: str, target_path: str,
                         project_type: str) -> None:
        """Bootstrap a new project from a manifest file."""
        self._main.bootstrap_project(manifest_path, target_path, project_type)

    def refreshProjectEnvironment(self, path: str) -> None:
        """Refresh the project environment (e.g., venv)."""
        self._main.refresh_project_environment(path)

    def getCurrentDirectory(self) -> str:
        """Get the current project directory."""
        return getattr(self._main, "currentDirectory", "")

    def setCurrentDirectory(self, path: str) -> None:
        """Set the current project directory."""
        self._main.currentDirectory = path

    def openDirectory(self) -> None:
        """Open the directory chooser dialog."""
        self._main.open_directory()

    def findIdeRoot(self) -> str:
        """Find the IDE root directory."""
        return self._main._find_ide_root()

    def updateJediVenv(self, project_path: Optional[str] = None) -> None:
        """Update the Jedi worker virtual environment."""
        self._main._update_jedi_venv(project_path)
