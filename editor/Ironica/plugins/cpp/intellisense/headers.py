"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Missing-header resolution for the C++ plugin.

When a translation unit reports ``'X' file not found``, the header is
located empirically: the compiler's own include list, the enclosing
project tree, and the ``-I`` flags already in effect are searched for
that exact filename.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("DreamStudio.Cpp.Headers")

_MAX_PROJECT_DEPTH = 6
_MAX_PROJECT_FILES = 20000
_MAX_SYSTEM_SUBDIRS = 400

_resolved: dict = {}


def _project_root_for(file_path: str | None) -> str:
    """Return the best search anchor for *file_path*.

    Prefers the nearest ancestor holding a ``CMakeLists.txt``, else the
    file's own directory. Never raises.
    """
    if not file_path:
        try:
            return os.path.abspath(os.sep)
        except Exception:
            return ""
    current = os.path.abspath(file_path)
    if os.path.isfile(current):
        current = os.path.dirname(current)
    while True:
        if os.path.isfile(os.path.join(current, "CMakeLists.txt")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.dirname(os.path.abspath(file_path))


def _system_roots() -> list:
    """Return compiler system include dirs, cached by the provider."""
    try:
        from ..autocompletion.includes import system_include_dirs

        return system_include_dirs()
    except Exception:
        return []


def _known_include_dirs(compile_args: list) -> list:
    """Extract existing ``-I`` directories from *compile_args*."""
    dirs: list = []
    args = list(compile_args or [])
    index = 0
    while index < len(args):
        value = ""
        if args[index] == "-I" and index + 1 < len(args):
            value = args[index + 1]
            index += 2
        elif args[index].startswith("-I"):
            value = args[index][2:]
            index += 1
        else:
            index += 1
            continue
        if value and os.path.isdir(value) and value not in dirs:
            dirs.append(value)
    return dirs


def _find_in_system(header: str) -> list:
    """Search system roots for *header*, including one subdir level.

    The extra level covers ``<pkg>/<header>`` layouts (e.g. a header
    living in an immediate subdirectory of an include root) without
    assuming any package name.

    Args:
        header: Header filename or qualified path (``a/b.h``).

    Returns:
        ``-I`` flags (possibly empty).
    """
    flags: list = []
    for root in _system_roots():
        if os.path.isfile(os.path.join(root, header)):
            continue
        try:
            subdirs = sorted(
                entry.path
                for entry in os.scandir(root)
                if entry.is_dir(follow_symlinks=False)
            )
        except OSError:
            continue
        for subdir in subdirs[:_MAX_SYSTEM_SUBDIRS]:
            if os.path.isfile(os.path.join(subdir, header)):
                flag = f"-I{subdir}"
                if flag not in flags:
                    flags.append(flag)
                break
    return flags


def _find_in_dirs(header: str, dirs: list) -> list:
    """Search explicit *dirs* (plus one level) for *header*.

    Args:
        header: Header filename or qualified path.
        dirs: Directories already on the include path.

    Returns:
        ``-I`` flags (possibly empty).
    """
    flags: list = []
    for root in dirs:
        if os.path.isfile(os.path.join(root, header)):
            continue
        try:
            subdirs = sorted(
                entry.path
                for entry in os.scandir(root)
                if entry.is_dir(follow_symlinks=False)
            )
        except OSError:
            continue
        for subdir in subdirs[:_MAX_SYSTEM_SUBDIRS]:
            if os.path.isfile(os.path.join(subdir, header)):
                flag = f"-I{subdir}"
                if flag not in flags:
                    flags.append(flag)
                break
    return flags


def _find_in_project(header: str, anchor: str) -> list:
    """Walk the project tree under *anchor* for *header* (bounded).

    Args:
        header: Header filename (basename match).
        anchor: Project root to walk.

    Returns:
        ``-I`` flags (possibly empty).
    """
    name = os.path.basename(header)
    if not name or not anchor or not os.path.isdir(anchor):
        return []
    flags: list = []
    visited = 0
    base_depth = anchor.rstrip(os.sep).count(os.sep)
    for current, directories, files in os.walk(anchor, followlinks=False):
        directories[:] = [
            item
            for item in directories
            if not item.startswith(".") and item not in ("build", "out")
        ]
        if current.count(os.sep) - base_depth > _MAX_PROJECT_DEPTH:
            directories[:] = []
            continue
        visited += len(files)
        if visited > _MAX_PROJECT_FILES:
            break
        if name in files:
            flag = f"-I{current}"
            if flag not in flags:
                flags.append(flag)
            if len(flags) >= 4:
                break
    return flags


def extra_flags_for(file_path: str | None) -> list:
    """Return previously resolved ``-I`` flags for *file_path*'s project.

    Args:
        file_path: Source file requesting completion.

    Returns:
        Cached flags (possibly empty) — never raises.
    """
    try:
        if not file_path:
            return []
        return list(_resolved.get(_project_root_for(file_path), []))
    except Exception:
        return []


def resolve_missing(
    missing: list, file_path: str | None, compile_args: list | None = None
) -> bool:
    """Locate missing headers and cache their ``-I`` dirs for the project.

    Args:
        missing: Header names from TU ``file not found`` diagnostics.
        file_path: Source file requesting completion.
        compile_args: Flags already in effect (their ``-I`` dirs are
            searched first, so nested third-party trees resolve).

    Returns:
        ``True`` when at least one new flag was cached — never raises.
    """
    try:
        headers = [str(item).strip() for item in missing or [] if str(item).strip()]
        if not headers or not file_path:
            return False
        anchor = _project_root_for(file_path)
        known = set(_resolved.get(anchor, []))
        search_dirs = _known_include_dirs(compile_args or [])
        grown = False
        for header in headers:
            found = _find_in_dirs(header, search_dirs)
            if not found:
                found = _find_in_system(header)
            if not found:
                found = _find_in_project(header, anchor)
            for flag in found:
                if flag not in known:
                    known.add(flag)
                    grown = True
        if grown:
            _resolved[anchor] = sorted(known)
        return grown
    except Exception as exc:
        logger.debug("header resolution failed: %s", exc)
        return False
