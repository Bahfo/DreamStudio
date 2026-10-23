"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Compile-argument resolution for C++ plugin.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
from typing import List, Optional

logger = logging.getLogger("DreamStudio.CPP.Args")
_DEFAULTS: tuple[str, ...] = ("-x", "c++", "-std=c++20")
_RESOURCE_DIR: Optional[List[str]] = None
_MODEL_CACHE: dict = {}


def unsaved_name(hint_cpp: bool = True) -> str:
    """
    Placeholder libclang path for unsaved tabs.
    """
    return "unsaved_tab.cpp" if hint_cpp else "unsaved_buffer.c"


def _find_db(start: str) -> str | None:
    """Walk upward from *start* looking for a ``compile_commands.json``."""
    cur = os.path.abspath(start)
    while True:
        cand = os.path.join(cur, "compile_commands.json")
        if os.path.isfile(cand):
            return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def _find_solution_root(start: str) -> str | None:
    """Walk upward from *start* looking for a ``.ds/solution.yaml`` marker."""
    try:
        from editor.utils.solution.paths import is_solution
    except Exception:
        return None
    cur = os.path.abspath(start)
    if os.path.isfile(cur):
        cur = os.path.dirname(cur)
    while True:
        if is_solution(cur):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def _db_args_for_file(db_path: str, file_path: str) -> list[str]:
    """Extract this file's arguments from the compile database at *db_path*."""
    try:
        with open(db_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        target = os.path.abspath(file_path)
        for entry in raw if isinstance(raw, list) else []:
            if not isinstance(entry, dict):
                continue
            entry_dir = entry.get("directory") or os.path.dirname(db_path)
            source = entry.get("file") or ""
            full = os.path.normpath(
                source if os.path.isabs(source) else os.path.join(entry_dir, source)
            )
            if full != target:
                continue
            parts = (
                entry["arguments"][1:]
                if isinstance(entry.get("arguments"), list)
                else shlex.split(entry.get("command", ""))[1:]
            )
            cleaned: list = []
            skip_next = False
            for part in parts:
                if skip_next:
                    skip_next = False
                    continue
                if part in ("-c", "-o"):
                    skip_next = part == "-o"
                    continue
                if part.startswith("-MF") or part.startswith("-MT"):
                    continue
                if part.startswith("-MQ") or part.startswith("-MJ"):
                    continue
                candidates = {os.path.abspath(part)}
                try:
                    candidates.add(os.path.normpath(os.path.join(entry_dir, part)))
                except Exception:
                    pass
                if target in candidates:
                    continue
                cleaned.append(part)
            return cleaned
    except Exception as exc:
        logger.debug("Ignoring compile DB %s: %s", db_path, exc)
    return []


def _flags_file_args(flags_path: str) -> list[str]:
    """Read bare flags from a ``compile_flags.txt`` file."""
    try:
        with open(flags_path, encoding="utf-8") as fh:
            return [
                line.strip()
                for line in fh.read().splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
    except OSError as exc:
        logger.debug("Ignoring flags file %s: %s", flags_path, exc)
        return []


def _env_include_args() -> list[str]:
    """Expand ``CPATH``-style environment include paths into ``-I`` flags."""
    args: list[str] = []
    for variable in ("CPATH", "CPLUS_INCLUDE_PATH", "C_INCLUDE_PATH", "INCLUDE"):
        raw = os.environ.get(variable, "")
        if not raw:
            continue
        for part in raw.split(";" if os.name == "nt" else ":"):
            directory = part.strip().strip('"')
            if directory and os.path.isdir(directory):
                args += ["-I", directory]
    return args


def _resource_dir_from_libclang() -> str:
    """Derive the clang resource directory from the loaded libclang library."""
    try:
        from clang.cindex import conf
    except Exception:
        return ""
    try:
        library = conf.get_filename()
    except Exception:
        library = ""
    if not library:
        return ""
    library_dir = os.path.dirname(os.path.abspath(str(library)))
    candidates = [
        os.path.join(library_dir, "clang"),
        os.path.join(os.path.dirname(library_dir), "lib", "clang"),
        os.path.join(os.path.dirname(library_dir), "lib64", "clang"),
    ]
    for base in candidates:
        if not os.path.isdir(base):
            continue
        try:
            children = sorted(
                (name for name in os.listdir(base)
                 if os.path.isdir(os.path.join(base, name)) and name[:1].isdigit()),
                reverse=True,
            )
        except OSError:
            continue
        for child in children:
            resource = os.path.join(base, child)
            if os.path.isdir(os.path.join(resource, "include")):
                return resource
    return ""


def resource_args() -> List[str]:
    """Return ``-resource-dir`` flags so libclang finds its builtin headers."""
    global _RESOURCE_DIR
    if _RESOURCE_DIR is not None:
        return list(_RESOURCE_DIR)
    found = ""
    for driver in ("clang++", "clang"):
        try:
            proc = subprocess.run(
                [driver, "-print-resource-dir"],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            continue
        candidate = proc.stdout.decode(errors="replace").strip()
        if candidate and os.path.isdir(candidate):
            found = candidate
            break
    if not found:
        found = _resource_dir_from_libclang()
    _RESOURCE_DIR = ["-resource-dir", found] if found else []
    return list(_RESOURCE_DIR)


def _system_include_args() -> list[str]:
    """Return compiler-probed system include flags for libclang."""
    args: list[str] = []
    try:
        from ..autocompletion.includes import system_include_dirs

        for directory in system_include_dirs():
            if directory and os.path.isdir(directory):
                args += ["-isystem", directory]
    except Exception as exc:
        logger.debug("system include probing failed: %s", exc)
    return args


def _dedupe_flags(flags: list) -> list:
    """Remove repeated flags while preserving order (``-I`` pairs included)."""
    result: list = []
    seen: set = set()
    index = 0
    while index < len(flags):
        if flags[index] in ("-I", "-isystem") and index + 1 < len(flags):
            pair = (flags[index], flags[index + 1])
            index += 2
            if pair in seen:
                continue
            seen.add(pair)
            result.extend(pair)
            continue
        value = flags[index]
        index += 1
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _model_signature(model) -> tuple:
    """Return a stable signature for cache invalidation of *model*."""
    signature: list = []
    for path in getattr(model, "cmake_files", []) or []:
        try:
            signature.append((path, os.stat(path).st_mtime_ns))
        except OSError:
            signature.append((path, 0))
    return tuple(signature)


def _cmake_model(root: str):
    """Return a cached :class:`CmakeModel` for *root*, rescanning on edits."""
    cached = _MODEL_CACHE.get(root)
    if cached is not None:
        signature, model = cached
        if _model_signature(model) == signature:
            return model
    try:
        from editor.Ironica.plugins.cmake.cmake.scanner import scan_project
    except Exception as exc:
        logger.debug("cmake scanner unavailable: %s", exc)
        return None
    model = scan_project(root)
    _MODEL_CACHE[root] = (_model_signature(model), model)
    return model


def _target_for_source(model, absolute: str):
    """Return the CMake target that owns *absolute*, or ``None``."""
    normalized = os.path.normcase(os.path.abspath(absolute))
    for target in model.targets:
        for source in target.sources:
            if os.path.normcase(os.path.abspath(source)) == normalized:
                return target
    source_dir = os.path.dirname(normalized)
    for target in model.targets:
        for source in target.sources:
            if os.path.dirname(os.path.normcase(os.path.abspath(source))) == source_dir:
                return target
    return None


def _flags_from_model(model, absolute: str) -> list[str]:
    """Build ``-I``/``-D``/``-std`` flags from a scanned CMake *model*."""
    includes: list = []
    definitions: list = []
    options: list = []
    standard = (getattr(model, "cxx_standard", "") or "").strip()
    if standard and standard[0].isdigit():
        options.append(f"-std=c++{standard}")
    for directory in getattr(model, "include_dirs", []) or []:
        if directory and os.path.isdir(directory):
            includes += ["-I", directory]
    definitions += list(getattr(model, "definitions", []) or [])
    options += list(getattr(model, "compile_options", []) or [])
    target = _target_for_source(model, absolute)
    if target is not None:
        for directory in target.include_dirs:
            if directory and os.path.isdir(directory):
                includes += ["-I", directory]
        definitions += list(target.definitions)
        options += list(target.compile_options)
    else:
        for candidate in model.targets:
            for directory in candidate.public_include_dirs:
                if directory and os.path.isdir(directory):
                    includes += ["-I", directory]
            definitions += list(candidate.public_definitions)
    return _dedupe_flags(includes + definitions + options)


def _build_db_args(cmake_root: str, absolute: str) -> list[str]:
    """Return flags from a configured CMake build tree, when available."""
    try:
        from editor.Ironica.plugins.cmake.cmake import builddb
    except Exception as exc:
        logger.debug("cmake build database helper unavailable: %s", exc)
        return []
    try:
        build_dir = builddb.find_build_directory(cmake_root)
        if not build_dir:
            return []
        database = os.path.join(build_dir, "compile_commands.json")
        if not os.path.isfile(database):
            return []
        arguments = builddb.arguments_for_file(database, absolute)
        if not arguments:
            return []
        return arguments
    except Exception as exc:
        logger.debug("cmake build database lookup failed: %s", exc)
        return []


def _cmake_args_for_file(absolute: str) -> list[str]:
    """Derive compile flags for *absolute* from the surrounding CMake project."""
    try:
        from editor.Ironica.plugins.cmake.cmake.scanner import find_cmake_root
    except Exception as exc:
        logger.debug("cmake scanner unavailable: %s", exc)
        return []
    root = find_cmake_root(absolute)
    if not root:
        return []
    flags = _build_db_args(root, absolute)
    if flags:
        return flags
    model = _cmake_model(root)
    if model is None:
        return []
    return _flags_from_model(model, absolute)


def _database_args(absolute: str, solution_root: str | None) -> tuple[list[str], bool]:
    """Return ``(flags, found_entry)`` from every known compile database."""
    databases: list[str] = []
    nearest = _find_db(os.path.dirname(absolute))
    if nearest:
        databases.append(nearest)
    if solution_root:
        try:
            from editor.utils.solution.paths import (
                compile_commands_path,
                compile_flags_path,
            )

            generated = compile_commands_path(solution_root)
            if os.path.isfile(generated):
                databases.append(generated)
            else:
                flags_path = compile_flags_path(solution_root)
                if os.path.isfile(flags_path):
                    return _flags_file_args(flags_path), True
        except Exception as exc:
            logger.debug("Ignoring generated .ds flags: %s", exc)
    flags: list[str] = []
    found = False
    for database in databases:
        entry = _db_args_for_file(database, absolute)
        if entry:
            flags += entry
            found = True
    return flags, found


def _resolved_header_args(absolute: str) -> list[str]:
    """Return include flags for headers discovered by the C++ resolver."""
    try:
        from . import headers as header_resolution

        return list(header_resolution.extra_flags_for(absolute))
    except Exception:
        return []


def args_for_file(
    file_path: str | None,
    source: str = "",
    solution_root: str | None = None,
) -> list[str]:
    """Build deterministic libclang arguments for *file_path*.

    Args:
        file_path: Source or header path being parsed.
        source: Current buffer content (owned by the caller).
        solution_root: Optional explicit solution root.

    Returns:
        A list of compiler arguments suitable for ``clang.cindex``.
    """
    _ = source
    args = list(_DEFAULTS) + resource_args() + _system_include_args()
    if not file_path or not os.path.isfile(file_path):
        return _dedupe_flags(args)

    absolute = os.path.abspath(file_path)
    root = solution_root or _find_solution_root(absolute)
    database_flags, found_entry = _database_args(absolute, root)
    args += database_flags
    if not found_entry:
        args += _cmake_args_for_file(absolute)
    args += _env_include_args()
    args += ["-I", os.path.dirname(absolute)]
    args += _resolved_header_args(absolute)
    try:
        from . import pch as pch_support

        args += pch_support.include_args(root)
    except Exception as exc:
        logger.debug("Ignoring pch flags: %s", exc)
    return _dedupe_flags(args)


__all__ = ["args_for_file", "resource_args", "unsaved_name"]
