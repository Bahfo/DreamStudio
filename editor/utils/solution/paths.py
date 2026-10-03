"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Central workspace-metadata paths for the ``.ds`` footprint.
"""

import os

DS_DIR = ".ds"
SOLUTION_FILE = "solution.yaml"
RUN_SUBDIR = "run"
PROJECT_INFO_FILE = "project_info.yaml"
PROPERTIES_FILE = "properties.json"
METADATA_FILE = "metadata.txt"

DEFAULT_EXCLUDES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        ".env",
        "env",
        ".ds",
        "__pycache__",
        "node_modules",
        "build",
        "dist",
        ".idea",
        ".vscode",
        ".vs",
        ".tox",
        ".pytest_cache",
        ".hg",
        ".svn",
    }
)


def ds_dir(root: str) -> str:
    """Return absolute ``.ds`` directory for workspace *root*."""
    return os.path.join(os.path.abspath(root), DS_DIR)


def marker_path(root: str) -> str:
    """Return absolute solution-marker path for workspace *root*."""
    return os.path.join(ds_dir(root), SOLUTION_FILE)


def run_dir(root: str, ensure: bool = False) -> str:
    """Return absolute per-workspace run-config directory."""
    directory = os.path.join(ds_dir(root), RUN_SUBDIR)
    if ensure:
        os.makedirs(directory, exist_ok=True)
    return directory


def is_solution(root: str) -> bool:
    """Check whether *root* carries a solution marker file."""
    try:
        return os.path.isfile(marker_path(root))
    except Exception:
        return False
