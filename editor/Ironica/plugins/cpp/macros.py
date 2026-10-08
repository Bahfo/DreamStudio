"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Macro-name collection for guard contexts (``#ifdef`` and family).

A full AST walk visits ~100k cursors through system headers (~2s), so
this walk visits every *top-level* cursor — where libclang surfaces all
macro definitions, including headers' — but recurses only into nodes
located in the main file. Bounded, cached, with a buffer-regex fallback.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

from .models import CppCompletion

logger = logging.getLogger("DreamStudio.Cpp.Macros")

_MAX_VISITED = 5000
_CACHE_BOUND = 16

_DEFINE_LINE = re.compile(r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)",
                          re.MULTILINE)

_macro_cache: Dict[Tuple[str, int], List[str]] = {}


def buffer_macros(source: str) -> List[str]:
    """Return macro names defined by ``#define`` lines in *source*."""
    if not source:
        return []
    seen: set[str] = set()
    ordered: List[str] = []
    for match in _DEFINE_LINE.finditer(source):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def _kind_name(cursor) -> str:
    """Return the cursor-kind name for enum members and int codes."""
    kind = getattr(cursor, "kind", None)
    if kind is None:
        return ""
    name = getattr(kind, "name", None)
    if isinstance(name, str) and name:
        return name
    try:
        from clang.cindex import CursorKind

        return str(CursorKind(int(kind))).split(".")[-1]
    except (TypeError, ValueError):
        return ""


def collect_macros(tu, main_path: Optional[str]) -> List[str]:
    """Collect macro names: buffer-speed walk, headers included.

    Args:
        tu: Parsed translation unit (may be ``None``).
        main_path: Main-file path used for recursion pruning.

    Returns:
        Ordered unique macro names, buffer macros first.
    """
    ordered: List[str] = []
    seen: set[str] = set()
    if tu is None:
        return ordered
    try:
        stack = list(tu.cursor.get_children())
    except Exception as exc:
        logger.debug("macro walk unavailable: %s", exc)
        return ordered
    visited = 0
    while stack and visited < _MAX_VISITED:
        cursor = stack.pop()
        visited += 1
        try:
            kind = _kind_name(cursor)
            location = cursor.location
            file_name = ""
            if location is not None and location.file is not None:
                file_name = str(location.file.name)
            if kind == "MACRO_DEFINITION":
                spelling = cursor.spelling or ""
                if spelling and spelling not in seen:
                    seen.add(spelling)
                    ordered.append(spelling)
            if file_name and main_path and file_name == main_path:
                try:
                    stack.extend(cursor.get_children())
                except Exception:
                    continue
        except Exception:
            continue
    return ordered


def complete_guards(
    prefix: str,
    tu=None,
    main_path: Optional[str] = None,
    source: str = "",
    clang_names: Optional[List[str]] = None,
) -> List[CppCompletion]:
    """Complete macro names for ``#ifdef``-family contexts.

    Args:
        prefix: Partial macro name.
        tu: Cached translation unit for header-macro collection.
        main_path: Main-file path for walk pruning.
        source: Buffer text for the regex fallback path.
        clang_names: Macro names already returned by ``codeComplete``.

    Returns:
        Ranked macro completions starting with *prefix*.
    """
    lowered = (prefix or "").lower()
    cache_key = (main_path or "", hash(source))
    cached = _macro_cache.get(cache_key)
    if cached is None:
        names = collect_macros(tu, main_path)
        for name in buffer_macros(source):
            if name not in names:
                names.append(name)
        if len(_macro_cache) >= _CACHE_BOUND:
            _macro_cache.pop(next(iter(_macro_cache)))
        _macro_cache[cache_key] = names
        cached = names
    merged: List[str] = list(cached)
    for name in clang_names or []:
        if name not in merged:
            merged.append(name)
    out: List[CppCompletion] = []
    for name in merged:
        if lowered and not name.lower().startswith(lowered):
            continue
        out.append(
            CppCompletion(
                text=name,
                insert_text=name,
                kind="macro",
                signature="macro",
            )
        )
    out.sort(key=lambda c: (not c.text.lower().startswith(lowered) if lowered
                            else False, c.text.lower()))
    return out
