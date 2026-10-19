"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Missing-header resolution for the C++ plugin.
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
    """Return the best search anchor for *file_path*."""
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
    """Search system roots for directories holding *header*."""
    return _find_in_dirs(header, _system_roots())


def _find_in_dirs(header: str, dirs: list) -> list:
    """Search explicit *dirs* (plus one level) for *header*."""
    found: list = []
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
                if subdir not in found:
                    found.append(subdir)
                break
    return found


def _find_in_project(header: str, anchor: str) -> list:
    """Walk the project tree under *anchor* for *header* (bounded)."""
    name = os.path.basename(header)
    if not name or not anchor or not os.path.isdir(anchor):
        return []
    found: list = []
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
        if name in files and current not in found:
            found.append(current)
            if len(found) >= 4:
                break
    return found


def locate_header(header: str, search_dirs: list, anchor: str) -> list:
    """Locate *header* across known dirs, system roots and the project."""
    try:
        name = str(header).strip()
        if not name:
            return []
        found = _find_in_dirs(name, search_dirs)
        if not found:
            found = _find_in_system(name)
        if not found:
            found = _find_in_project(name, anchor)
        return found
    except Exception as exc:
        logger.debug("header locate failed: %s", exc)
        return []


def extra_flags_for(file_path: str | None) -> list:
    """Return previously resolved ``-I`` flags for *file_path*'s project."""
    try:
        if not file_path:
            return []
        return list(_resolved.get(_project_root_for(file_path), []))
    except Exception:
        return []


def resolve_missing(
    missing: list, file_path: str | None, compile_args: list | None = None
) -> bool:
    """Locate missing headers and cache their ``-I`` dirs for the project."""
    try:
        headers = [str(item).strip() for item in missing or [] if str(item).strip()]
        if not headers or not file_path:
            return False
        anchor = _project_root_for(file_path)
        known = set(_resolved.get(anchor, []))
        search_dirs = _known_include_dirs(compile_args or [])
        grown = False
        for header in headers:
            for directory in locate_header(header, search_dirs, anchor):
                flag = f"-I{directory}"
                if flag not in known:
                    known.add(flag)
                    grown = True
        if grown:
            _resolved[anchor] = sorted(known)
        return grown
    except Exception as exc:
        logger.debug("header resolution failed: %s", exc)
        return False
