"""Centralized resource path resolution for development and frozen builds."""

import os
import sys

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def resource_path(relative_path: str) -> str:
    """Resolve a project-relative resource path for the current runtime."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = _PROJECT_ROOT
    return os.path.join(base, relative_path)