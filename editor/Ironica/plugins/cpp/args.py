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


def args_for_file(file_path: str | None, source: str = "") -> list[str]:
    """
    Build deterministic args: defaults + DB overlay + -I roots.
    """
    args = list(_DEFAULTS) + resource_args()
    if file_path and os.path.isfile(file_path):
        db = _find_db(os.path.dirname(os.path.abspath(file_path)))
        if db:
            try:
                with open(db, encoding="utf-8") as fh:
                    raw = json.load(fh)
                for e in raw if isinstance(raw, list) else []:
                    full = os.path.normpath(
                        os.path.join(
                            e.get("directory", os.path.dirname(db)), e.get("file", "")
                        )
                    )
                    if full == os.path.abspath(file_path):
                        parts = (
                            e["arguments"][1:]
                            if isinstance(e.get("arguments"), list)
                            else shlex.split(e.get("command", ""))[1:]
                        )
                        for p in parts:
                            if p in ("-c", "-o") or p.startswith("-MF"):
                                continue
                            args.append(p)
                        break
            except Exception as exc:
                logger.debug("Ignoring compile DB: %s", exc)
        d = os.path.dirname(os.path.abspath(file_path))
        args += ["-I", d]
    return args
