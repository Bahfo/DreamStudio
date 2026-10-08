"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Compile-argument resolution for C++ plugin.
"""

from __future__ import annotations

import os
import json
import shlex
import logging

logger = logging.getLogger("DreamStudio.CPP.Args")
_CPP_EXTS = frozenset({".cpp", ".hpp", ".hh", ".cc", ".cxx", ".c++", ".ixx"})
_DEFAULTS: tuple[str, ...] = ("-x", "c++", "-std=c++20")


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


def args_for_file(file_path: str | None, source: str = "") -> list[str]:
    """
    Build deterministic args: defaults + DB overlay + -I roots.
    """
    args = list(_DEFAULTS)
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
