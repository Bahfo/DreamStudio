"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Header-path completion for `#include` lines (project + system headers).
"""

from __future__ import annotations

import os
import re
import logging
import subprocess
from typing import List, Optional, Tuple

# Local Imports
from ..models import CppCompletion

logger = logging.getLogger("DreamStudio.Cpp.Includes")

_INCLUDE_LINE = re.compile(r"#\s*include\s*(?P<open>[<\"])(?P<partial>[^>\"]*)$")
_HEADER_EXTS = frozenset(
    {
        ".h",
        ".hh",
        ".hpp",
        ".hxx",
        ".ixx",
        ".ccm",
        ".inl",
        ".ipp",
        ".tpp",
        ".cppm",
    }
)

_PLAIN_HEADER_NAME = re.compile(r"[A-Za-z_][\w+.\-]*$")
_MAX_HEADERS = 100
_SYSTEM_DIRS: Optional[List[str]] = None


def parse_include(line_text: str, col: int) -> Optional[Tuple[str, str]]:
    """
    Parse an `#include` line up to *col*.

    Returns:
        ``(open_char, partial)`` where open char is `<` or `"`, or
        ``None`` when the cursor is not inside an include path.
    """
    match = _INCLUDE_LINE.search(line_text[: max(0, col)])
    if not match:
        return None
    return (match.group("open"), match.group("partial"))


def project_include_dirs(
    file_path: Optional[str],
    compile_args: Optional[List[str]] = None,
) -> List[str]:
    """
    Return project search dirs: buffer dir plus `-I` flag values.
    """
    dirs: List[str] = []
    if file_path:
        buffer_dir = os.path.dirname(os.path.abspath(file_path))
        if os.path.isdir(buffer_dir):
            dirs.append(buffer_dir)
    for index, flag in enumerate(compile_args or []):
        value = ""
        if flag == "-I" and index + 1 < len(compile_args or []):
            value = (compile_args or [])[index + 1]
        elif flag.startswith("-I"):
            value = flag[2:]
        if value and os.path.isdir(value) and value not in dirs:
            dirs.append(value)
    return dirs


def system_include_dirs() -> List[str]:
    """
    Return cached system include dirs (libstdc++/libc++ + fallback).
    """
    global _SYSTEM_DIRS
    if _SYSTEM_DIRS is not None:
        return list(_SYSTEM_DIRS)
    found: List[str] = []
    try:
        proc = subprocess.run(
            ["clang++", "-E", "-x", "c++", "-", "-v"],
            input=b"",
            capture_output=True,
            timeout=5,
        )
        capture = False
        for line in proc.stderr.decode(errors="replace").splitlines():
            stripped = line.strip()
            if "search starts here" in stripped:
                capture = True
                continue
            if "End of search list" in stripped:
                break
            if capture and os.path.isdir(stripped) and stripped not in found:
                found.append(stripped)
    except Exception as exc:
        logger.debug("system include probing failed: %s", exc)
    for fallback in ("/usr/include/c++", "/usr/include", "/usr/local/include"):
        if os.path.isdir(fallback) and fallback not in found:
            found.append(fallback)
    _SYSTEM_DIRS = found
    return list(found)


def complete_include(
    partial: str,
    open_char: str,
    file_path: Optional[str] = None,
    compile_args: Optional[List[str]] = None,
) -> List[CppCompletion]:
    """
    List headers matching *partial* for quote (`"`) or bracket (`<`).
    """
    if '"' in partial or ">" in partial:
        return []
    if open_char == '"':
        search_dirs = project_include_dirs(file_path, compile_args)
    else:
        search_dirs = project_include_dirs(file_path, compile_args)
        search_dirs.extend(d for d in system_include_dirs() if d not in search_dirs)
    head, _, base = partial.rpartition("/")
    seen: set[str] = set()
    out: List[CppCompletion] = []
    for root in search_dirs:
        target = os.path.join(root, head) if head else root
        if not os.path.isdir(target):
            continue
        try:
            entries = sorted(os.listdir(target))
        except OSError:
            continue
        for entry in entries:
            if not entry.lower().startswith(base.lower()):
                continue
            full = os.path.join(target, entry)
            display = f"{head}/{entry}" if head else entry
            if display in seen:
                continue
            if os.path.isdir(full):
                seen.add(display)
                out.append(
                    CppCompletion(
                        text=display + "/",
                        insert_text=display + "/",
                        kind="path",
                        signature="directory",
                    )
                )
                continue
            ext = os.path.splitext(entry)[1].lower()
            if ext in _HEADER_EXTS or (not ext and _PLAIN_HEADER_NAME.match(entry)):
                seen.add(display)
                out.append(
                    CppCompletion(
                        text=display,
                        insert_text=display,
                        kind="path",
                        signature="header",
                    )
                )
            if len(out) >= _MAX_HEADERS:
                return out
    return out
