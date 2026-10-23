"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
CMake build-directory discovery and compile-database access.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
import time

logger = logging.getLogger("DreamStudio.CMake.BuildDB")

_SKIP_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        ".env",
        ".idea",
        ".vscode",
        ".vs",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".tox",
        ".ds",
    }
)
_MAX_SEARCH_DEPTH = 4
_MAX_SEARCH_DIRECTORIES = 3000
_MAX_RECONFIGURE_SECONDS = 90
_RECONFIGURE_COOLDOWN = 120.0
_CACHE_SECONDS = 5.0

_build_cache: dict = {}
_entries_cache: dict = {}
_reconfigure_state: dict = {}


def _skip_directory(name: str) -> bool:
    """Return ``True`` when *name* should not be searched."""
    lowered = name.lower()
    return lowered in _SKIP_DIRECTORIES or (
        name.startswith(".") and lowered not in (".build",)
    )


def _cmake_cache_home(cache_path: str) -> str:
    """Read ``CMAKE_HOME_DIRECTORY`` from a ``CMakeCache.txt`` file."""
    try:
        with open(cache_path, encoding="utf-8", errors="replace") as handle:
            for _ in range(400):
                line = handle.readline()
                if not line:
                    break
                if line.startswith("CMAKE_HOME_DIRECTORY:INTERNAL="):
                    value = line.split("=", 1)[1].strip()
                    return os.path.normcase(os.path.abspath(value))
    except OSError:
        return ""
    return ""


def find_build_directory(cmake_root: str) -> str | None:
    """Locate a configured CMake build directory for *cmake_root*.

    Args:
        cmake_root: Directory containing the top-level ``CMakeLists.txt``.

    Returns:
        The best matching build directory, or ``None``.
    """
    try:
        root = os.path.normcase(os.path.abspath(cmake_root))
    except Exception:
        return None
    cached = _build_cache.get(root)
    now = time.monotonic()
    if cached is not None and now - cached[0] < _CACHE_SECONDS:
        return cached[1]

    best: str | None = None
    best_score: tuple[int, int] | None = None
    visited = 0
    base_depth = root.rstrip(os.sep).count(os.sep)
    for current, directories, files in os.walk(cmake_root, followlinks=False):
        visited += 1
        if visited > _MAX_SEARCH_DIRECTORIES:
            break
        depth = current.rstrip(os.sep).count(os.sep) - base_depth
        directories[:] = [name for name in directories if not _skip_directory(name)]
        if depth >= _MAX_SEARCH_DEPTH:
            directories[:] = []
        if "CMakeCache.txt" not in files:
            continue
        cache_path = os.path.join(current, "CMakeCache.txt")
        home = _cmake_cache_home(cache_path)
        if home != root:
            continue
        score = (depth, len(current))
        if best_score is None or score < best_score:
            best = current
            best_score = score
    _build_cache[root] = (now, best)
    return best


def _newest_cmake_mtime(cmake_root: str) -> float:
    """Return the newest ``CMakeLists.txt`` mtime under *cmake_root*."""
    newest = 0.0
    visited = 0
    base_depth = cmake_root.rstrip(os.sep).count(os.sep)
    for current, directories, files in os.walk(cmake_root, followlinks=False):
        visited += 1
        if visited > _MAX_SEARCH_DIRECTORIES:
            break
        if current.rstrip(os.sep).count(os.sep) - base_depth > _MAX_SEARCH_DEPTH:
            directories[:] = []
            continue
        directories[:] = [name for name in directories if not _skip_directory(name)]
        if "CMakeLists.txt" in files:
            try:
                newest = max(
                    newest,
                    os.path.getmtime(os.path.join(current, "CMakeLists.txt")),
                )
            except OSError:
                continue
    return newest


def ensure_compile_commands(cmake_root: str, build_dir: str) -> str | None:
    """Ensure ``build_dir`` has a fresh ``compile_commands.json``.

    Reconfigures the existing build tree with ``CMAKE_EXPORT_COMPILE_COMMANDS``
    when the database is missing or older than the project's CMake scripts.

    Args:
        cmake_root: Directory containing the top-level ``CMakeLists.txt``.
        build_dir: Configured CMake build directory.

    Returns:
        Path to ``compile_commands.json``, or ``None`` when unavailable.
    """
    database = os.path.join(build_dir, "compile_commands.json")
    fresh = False
    if os.path.isfile(database):
        try:
            fresh = os.path.getmtime(database) >= _newest_cmake_mtime(cmake_root)
        except OSError:
            fresh = False
    if fresh:
        return database

    now = time.monotonic()
    last_attempt = _reconfigure_state.get(build_dir, 0.0)
    if now - last_attempt < _RECONFIGURE_COOLDOWN:
        return database if os.path.isfile(database) else None
    _reconfigure_state[build_dir] = now

    cmake = shutil.which("cmake")
    if not cmake:
        return database if os.path.isfile(database) else None
    try:
        result = subprocess.run(
            [
                cmake,
                "-S",
                cmake_root,
                "-B",
                build_dir,
                "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
            ],
            capture_output=True,
            timeout=_MAX_RECONFIGURE_SECONDS,
        )
    except Exception as exc:
        logger.debug("cmake reconfigure failed for %s: %s", build_dir, exc)
        return database if os.path.isfile(database) else None
    if result.returncode != 0:
        logger.debug(
            "cmake reconfigure exited with %d for %s",
            result.returncode,
            build_dir,
        )
        return database if os.path.isfile(database) else None
    return database if os.path.isfile(database) else None


def _load_entries(database: str) -> dict:
    """Load *database* into ``{normalised_source: arguments}`` with caching."""
    try:
        mtime = os.stat(database).st_mtime_ns
    except OSError:
        return {}
    cached = _entries_cache.get(database)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    entries: dict = {}
    try:
        with open(database, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        logger.debug("Could not read compile database %s: %s", database, exc)
        return {}
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        source = entry.get("file")
        directory = entry.get("directory") or os.path.dirname(database)
        if not isinstance(source, str) or not source:
            continue
        arguments = entry.get("arguments")
        if not isinstance(arguments, list):
            command = entry.get("command")
            if not isinstance(command, str):
                continue
            try:
                arguments = shlex.split(command, posix=os.name != "nt")
            except ValueError:
                continue
        full = os.path.normcase(
            os.path.abspath(
                source if os.path.isabs(source) else os.path.join(directory, source)
            )
        )
        entries.setdefault(full, [str(item) for item in arguments])
    _entries_cache[database] = (mtime, entries)
    return entries


def arguments_for_file(database: str, source_path: str) -> list[str]:
    """Return the recorded compiler arguments for *source_path*.

    Args:
        database: Path to a ``compile_commands.json`` file.
        source_path: Source file to look up.

    Returns:
        The full argument vector from the database, or an empty list.
    """
    entries = _load_entries(database)
    if not entries:
        return []
    key = os.path.normcase(os.path.abspath(source_path))
    return list(entries.get(key, []))


__all__ = [
    "arguments_for_file",
    "ensure_compile_commands",
    "find_build_directory",
]
