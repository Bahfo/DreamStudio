"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
GUI-thread snapshot of modified editor buffers for C++ navigation.

The C++ navigation worker parses translation units off the GUI thread, so it
must never read live editor widgets.  This module captures the buffer contents
once, on the GUI thread, and returns immutable tuples the worker can consume.
"""

from __future__ import annotations

import logging
import os

from PyQt6.QtCore import QObject

logger = logging.getLogger("DreamStudio.Cpp.NavigationBuffers")


def collect_modified_buffers(
    tab_editor: QObject | None,
) -> tuple[tuple[str, str], ...]:
    """
    Return ``(path, text)`` pairs for every modified open editor buffer.

    This reads live widget state and must be called on the GUI thread.

    Args:
        tab_editor: Tab container that owns the open editor widgets. When
            ``None`` or unsupported, an empty tuple is returned.

    Returns:
        Absolute paths paired with their in-memory contents, in tab order and
        de-duplicated by path. Editors without a file path are skipped because
        libclang cannot associate an in-memory buffer with them.
    """
    if tab_editor is None:
        return ()

    try:
        count = int(tab_editor.count())
    except (AttributeError, TypeError, RuntimeError):
        return ()

    buffers: dict[str, str] = {}
    for index in range(count):
        try:
            widget = tab_editor.widget(index)
        except RuntimeError:
            continue
        editor = _inner_editor(widget)
        if editor is None or not _is_modified(editor):
            continue
        path = getattr(editor, "current_file_path", None)
        if not path:
            continue
        try:
            source = editor.text()
        except RuntimeError:
            continue
        if not isinstance(source, str):
            continue
        buffers[_normalise(path)] = source
    return tuple(buffers.items())


def _inner_editor(widget: QObject | None):
    """Return the ``CodeEditor`` inside *widget*, or ``None``."""
    if widget is None:
        return None
    try:
        from editor.Ironica.utils.minimap import ensure_inner

        return ensure_inner(widget)
    except RuntimeError:
        return None


def _is_modified(editor) -> bool:
    """Return ``True`` when *editor* holds unsaved changes."""
    for name in ("is_dirty", "isModified"):
        probe = getattr(editor, name, None)
        if not callable(probe):
            continue
        try:
            return bool(probe())
        except RuntimeError:
            return False
    return False


def _normalise(path: str) -> str:
    """Return an absolute, canonical path for *path*."""
    try:
        return os.path.normcase(
            os.path.normpath(os.path.realpath(os.fspath(path)))
        )
    except (OSError, TypeError, ValueError):
        return str(path)


__all__ = ["collect_modified_buffers"]
