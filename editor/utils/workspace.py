"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Single authority for workspace-directory resolution and re-point protocol.
"""

import os
from typing import Protocol, runtime_checkable


def get_workspace_dir(widget_or_window=None) -> str:
    """Return validated workspace root or empty string.

    Args:
        widget_or_window: Main window or any child widget. For widgets
            the top-level window's ``currentDirectory`` is used.

    Returns:
        Absolute workspace path, or ``""`` when unset. Never process CWD.
    """
    candidate = ""
    try:
        target = widget_or_window
        window_fn = getattr(target, "window", None)
        if callable(window_fn):
            try:
                top = window_fn()
            except Exception:
                top = None
            if top is not None:
                target = top
        candidate = getattr(target, "currentDirectory", "") or ""
    except Exception:
        candidate = ""
    if candidate and os.path.isdir(str(candidate)):
        return os.path.abspath(str(candidate))
    return ""


@runtime_checkable
class WorkspaceAware(Protocol):
    """Uniform re-point protocol for path-dependent panels."""

    def set_workspace(self, path: str) -> None:
        """Re-point the component at workspace root *path*."""
        ...
