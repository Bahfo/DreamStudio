"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Compile-argument resolution for C/C++ buffers.

Detects the source language from the file extension, applies sane
built-in defaults, and overlays per-file flags from the nearest
``compile_commands.json`` (searched upward from the buffer path).
Results are cached by database path + mtime so large-file typing
never re-reads the build database.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("DreamStudio.CSupport.CompileDB")

_CPP_EXTENSIONS = frozenset({".cpp", ".cxx", ".cc", ".c++", ".hh", ".hpp", ".hxx"})
_C_EXTENSIONS = frozenset({".c", ".h"})

_DEFAULT_C_ARGS: Tuple[str, ...] = ("-x", "c", "-std=c11")
_DEFAULT_CPP_ARGS: Tuple[str, ...] = ("-x", "c++", "-std=c++17")

_DB_CACHE: Dict[str, Tuple[float, dict]] = {}


def language_for_path(file_path: Optional[str]) -> str:
    """Return ``"c++"`` or ``"c"`` based on the file extension.

    Args:
        file_path: Buffer path; ``None`` means an unsaved C buffer.

    Returns:
        ``"c++"`` for C++ extensions, ``"c"`` otherwise.
    """
    if file_path:
        _, ext = os.path.splitext(file_path)
        if ext.lower() in _CPP_EXTENSIONS:
            return "c++"
    return "c"


def default_args_for_path(file_path: Optional[str]) -> List[str]:
    """Return built-in libclang args for the language of *file_path*.

    Args:
        file_path: Buffer path used for language detection.

    Returns:
        Mutable list of default compiler arguments.
    """
    if language_for_path(file_path) == "c++":
        return list(_DEFAULT_CPP_ARGS)
    return list(_DEFAULT_C_ARGS)


def unsaved_name_for_path(file_path: Optional[str]) -> str:
    """Return the placeholder name used for buffers without a path.

    Args:
        file_path: Buffer path, possibly ``None``.

    Returns:
        The original path, or a language-appropriate unsaved name.
    """
    if file_path:
        return file_path
    return "unsaved_buffer.c"


def _find_database(start_dir: str) -> Optional[str]:
    """Search upward from *start_dir* for ``compile_commands.json``.

    Args:
        start_dir: Directory where the search starts.

    Returns:
        Database path or ``None`` when no database was found.
    """
    current = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(current, "compile_commands.json")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _load_database(db_path: str) -> dict:
    """Load and cache the compilation database at *db_path*.

    Args:
        db_path: Path to ``compile_commands.json``.

    Returns:
        Mapping of absolute file path to its entry dict.
    """
    try:
        mtime = os.path.getmtime(db_path)
    except OSError:
        return {}
    cached = _DB_CACHE.get(db_path)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    try:
        with open(db_path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError) as exc:
        logger.debug("Ignoring unreadable compile DB %s: %s", db_path, exc)
        return {}
    entries: dict = {}
    if isinstance(raw, list):
        base = os.path.dirname(db_path)
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = item.get("file")
            if not name:
                continue
            directory = item.get("directory", base)
            full = os.path.normpath(
                name if os.path.isabs(name) else os.path.join(directory, name)
            )
            entries[full] = item
    _DB_CACHE[db_path] = (mtime, entries)
    return entries


def _entry_args(entry: dict) -> List[str]:
    """Extract compiler flags from one database entry.

    Args:
        entry: Single ``compile_commands.json`` entry.

    Returns:
        Flag list without the compiler executable and output/input parts.
    """
    if isinstance(entry.get("arguments"), list):
        parts = [str(p) for p in entry["arguments"][1:]]
    else:
        command = str(entry.get("command", ""))
        parts = _split_command(command)[1:]
    cleaned: List[str] = []
    skip_next = False
    for part in parts:
        if skip_next:
            skip_next = False
            continue
        if part in ("-o", "-MF", "-MT", "-MQ"):
            skip_next = True
            continue
        if part == "-c":
            continue
        if not part.startswith("-") and (
            part.endswith(".c") or part.endswith(".cpp") or part.endswith(".cc")
        ):
            continue
        cleaned.append(part)
    return cleaned


def _split_command(command: str) -> List[str]:
    """Split a shell command line respecting simple quoting.

    Args:
        command: Raw ``command`` string from the database.

    Returns:
        Token list; falls back to whitespace split on parse failure.
    """
    import shlex

    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def args_for_file(
    file_path: Optional[str], extra_args: Optional[List[str]] = None
) -> List[str]:
    """Resolve effective libclang args for a buffer.

    Args:
        file_path: Buffer path; ``None`` yields built-in C defaults.
        extra_args: Caller-provided flags appended last (highest priority).

    Returns:
        Full argument list: defaults, then database flags, then extras.
    """
    args = default_args_for_path(file_path)
    if file_path:
        db_path = _find_database(os.path.dirname(os.path.abspath(file_path)))
        if db_path:
            entries = _load_database(db_path)
            key = os.path.normpath(os.path.abspath(file_path))
            entry = entries.get(key)
            if entry is not None:
                try:
                    args.extend(_entry_args(entry))
                except Exception as exc:
                    logger.debug("Ignoring malformed DB entry: %s", exc)
    if extra_args:
        args.extend(extra_args)
    return args


def clear_cache() -> None:
    """Drop cached compilation databases (tests and project switches)."""
    _DB_CACHE.clear()
