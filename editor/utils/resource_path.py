"""Centralized resource path resolution for development and frozen builds."""

import os
import sys

# In development, resources live under the project root (parent of editor/).
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def resource_path(relative_path: str) -> str:
    """Resolve a project-relative resource path for the current runtime.

    Development builds resolve relative to the repository root.
    PyInstaller frozen builds resolve relative to ``sys._MEIPASS``
    (the runtime bundle directory).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = _PROJECT_ROOT
    return os.path.join(base, relative_path)