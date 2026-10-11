"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Compile-argument resolution for C++ plugin.
"""

from __future__ import annotations

import os
import json
import shlex
import logging
import subprocess
from typing import List, Optional

logger = logging.getLogger("DreamStudio.CPP.Args")
_CPP_EXTS = frozenset({".cpp", ".hpp", ".hh", ".cc", ".cxx", ".c++", ".ixx"})
_DEFAULTS: tuple[str, ...] = ("-x", "c++", "-std=c++20")
_RESOURCE_DIR: Optional[List[str]] = None


def is_cpp(path: str | None, source: str = "") -> bool:
    """
    Checks whether the path is a C++ buffer.
    """
    if path:
        _, ext = os.path.splitext(path)
        if ext.lower() in _CPP_EXTS:
            return True
        if ext.lower() == ".h":
            for tok in ("class ", "template<", "namespace ", "concpet "):
                if tok in source:
                    return True

    return False


def unsaved_name(hint_cpp: bool = True) -> str:
    """
    Placeholder libclang path for unsaved tabs.
    """
    return "unsaved_tab.cpp" if hint_cpp else "unsaved_buffer.c"


def _find_db(start: str) -> str | None:
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
    """Walk upward from *start* looking for a ``.ds/solution.yaml`` marker.

    Args:
        start: File or directory to start searching from.

    Returns:
        Solution root directory, or ``None`` when outside a solution.
    """
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
    """Extract this file's arguments from the compile database at *db_path*.

    Args:
        db_path: Absolute ``compile_commands.json`` path.
        file_path: Absolute source path to match.

    Returns:
        Argument list (possibly empty) — never raises.
    """
    try:
        with open(db_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        for e in raw if isinstance(raw, list) else []:
            full = os.path.normpath(
                os.path.join(
                    e.get("directory", os.path.dirname(db_path)), e.get("file", "")
                )
            )
            if full == os.path.abspath(file_path):
                parts = (
                    e["arguments"][1:]
                    if isinstance(e.get("arguments"), list)
                    else shlex.split(e.get("command", ""))[1:]
                )
                # NOTE: database entries name the source file itself (and
                # the -o object output). Passing either back into
                # libclang's parse args fails the whole TU, so strip them.
                target = os.path.abspath(file_path)
                entry_dir = e.get("directory", os.path.dirname(db_path))
                cleaned = []
                skip_next = False
                for part in parts:
                    if skip_next:
                        skip_next = False
                        continue
                    if part in ("-c", "-o"):
                        skip_next = part == "-o"
                        continue
                    if part.startswith("-MF"):
                        continue
                    candidates = {os.path.abspath(part)}
                    try:
                        candidates.add(
                            os.path.normpath(os.path.join(entry_dir, part))
                        )
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
    """Read bare flags from a ``compile_flags.txt`` file.

    Args:
        flags_path: Absolute flags-file path.

    Returns:
        Flag list (possibly empty) — never raises.
    """
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
    """Expand ``CPATH``-style environment include paths into ``-I`` flags.

    Returns:
        Flag list (possibly empty) — never raises.
    """
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


def resource_args() -> List[str]:
    """Return ``-resource-dir`` flags so libclang finds its builtin headers.

    Without this, every system header fails (``'stddef.h' file not found``)
    and all ``std::`` completion is empty. Result is probed once and cached.
    """
    global _RESOURCE_DIR
    if _RESOURCE_DIR is not None:
        return list(_RESOURCE_DIR)
    found = ""
    try:
        proc = subprocess.run(
            ["clang++", "-print-resource-dir"],
            capture_output=True,
            timeout=5,
        )
        candidate = proc.stdout.decode(errors="replace").strip()
        if candidate and os.path.isdir(candidate):
            found = candidate
    except Exception as exc:
        logger.debug("resource dir probing failed: %s", exc)
    if not found:
        for fallback in (
            "/usr/lib/llvm-18/lib/clang/18",
            "/usr/lib/llvm-17/lib/clang/17",
            "/usr/lib/llvm-16/lib/clang/16",
            "/usr/lib/clang/18",
        ):
            if os.path.isdir(fallback):
                found = fallback
                break
    _RESOURCE_DIR = ["-resource-dir", found] if found else []
    return list(_RESOURCE_DIR)


def args_for_file(
    file_path: str | None,
    source: str = "",
    solution_root: str | None = None,
) -> list[str]:
    """Build deterministic args: defaults + DB overlays + env + ``-I`` roots.

    Lookup order after the defaults: nearest upward
    ``compile_commands.json``, the solution's generated
    ``.ds/cpp/compile_commands.json`` (+ ``compile_flags.txt`` fallback),
    ``CPATH``-style environment includes, then ``-I <buffer-dir>``.

    Args:
        file_path: Source file the TU is built for (``None`` = unsaved).
        source: Buffer content (used for ``.h`` language detection).
        solution_root: Explicit solution root for ``.ds`` lookups; when
            omitted it is discovered via the ``.ds`` marker walk.

    Returns:
        Ordered clang argument list.
    """
    args = list(_DEFAULTS) + resource_args()
    if file_path and os.path.isfile(file_path):
        absolute = os.path.abspath(file_path)
        db = _find_db(os.path.dirname(absolute))
        if db:
            args += _db_args_for_file(db, absolute)
        root = solution_root or _find_solution_root(absolute)
        if root:
            try:
                from editor.utils.solution.paths import (
                    compile_commands_path,
                    compile_flags_path,
                )

                generated_db = compile_commands_path(root)
                if os.path.isfile(generated_db):
                    args += _db_args_for_file(generated_db, absolute)
                else:
                    generated_flags = compile_flags_path(root)
                    if os.path.isfile(generated_flags):
                        args += _flags_file_args(generated_flags)
            except Exception as exc:
                logger.debug("Ignoring generated .ds flags: %s", exc)
        args += _env_include_args()
        d = os.path.dirname(absolute)
        args += ["-I", d]
    return args
