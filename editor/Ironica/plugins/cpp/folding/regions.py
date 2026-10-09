"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

AST-accurate fold regions for C++ and C buffers.

Regions derive from libclang cursor extents (never indentation): the
same pruned walk used elsewhere visits top-level cursors and recurses
only into main-file nodes. Include runs and conditional blocks come
from a lightweight directive pass. A brace-matching fallback covers
unparseable buffers.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from editor.Ironica.utils.folding import FoldRegion

logger = logging.getLogger("DreamStudio.Cpp.Folding")

_FOLDABLE = frozenset({
    "FUNCTION_DECL", "FUNCTION_TEMPLATE", "CXX_METHOD", "CONSTRUCTOR",
    "CXX_CONSTRUCTOR", "DESTRUCTOR", "CXX_DESTRUCTOR", "CXX_CONVERSION",
    "CLASS_DECL", "STRUCT_DECL", "UNION_DECL", "CLASS_TEMPLATE",
    "CLASS_TEMPLATE_PARTIAL_SPEC", "NAMESPACE", "ENUM_DECL",
})

_KIND_BY_CURSOR = {
    "FUNCTION_DECL": "function",
    "FUNCTION_TEMPLATE": "template",
    "CXX_METHOD": "method",
    "CONSTRUCTOR": "method",
    "CXX_CONSTRUCTOR": "method",
    "DESTRUCTOR": "method",
    "CXX_DESTRUCTOR": "method",
    "CXX_CONVERSION": "method",
    "CLASS_DECL": "class",
    "STRUCT_DECL": "struct",
    "UNION_DECL": "union",
    "CLASS_TEMPLATE": "template",
    "CLASS_TEMPLATE_PARTIAL_SPEC": "template",
    "NAMESPACE": "namespace",
    "ENUM_DECL": "enum",
}

_INCLUDE_LINE = re.compile(r"^\s*#\s*include\s*[<\"]")
_COND_OPEN = re.compile(r"^\s*#\s*(if|ifdef|ifndef)\b")
_COND_CLOSE = re.compile(r"^\s*#\s*endif\b")

_MAX_VISITED = 20000

_SPAN_PRIORITY = {
    "template": 0,
    "class": 1,
    "struct": 1,
    "namespace": 1,
    "enum": 1,
    "union": 1,
    "function": 2,
    "method": 2,
    "conditional": 3,
    "include": 4,
    "block": 5,
}


def _kind_name(cursor) -> str:
    """Return the cursor-kind name for enum members and int codes."""
    kind = getattr(cursor, "kind", None)
    name = getattr(kind, "name", None)
    if isinstance(name, str) and name:
        return name
    try:
        from clang.cindex import CursorKind

        return str(CursorKind(int(kind))).split(".")[-1]
    except (TypeError, ValueError):
        return ""


def _extent_lines(cursor) -> Optional[tuple]:
    """Return ``(start0, end0)`` extent lines, or ``None`` when unusable."""
    try:
        extent = cursor.extent
        start = int(extent.start.line) - 1
        end = int(extent.end.line) - 1
    except Exception:
        return None
    if end <= start or start < 0:
        return None
    return (start, end)


def _span_from_children(cursor, main_path: Optional[str],
                        bound: int = 2000) -> Optional[tuple]:
    """Derive a fold span from descendant extents for broken constructs.

    Unterminated namespaces or classes mid-typing carry invalid extents;
    their children still locate the visible body.
    """
    starts: List[int] = []
    ends: List[int] = []
    try:
        own = cursor.location
        if own is not None and own.line:
            starts.append(int(own.line) - 1)
    except Exception:
        pass
    stack = [cursor]
    visited = 0
    while stack and visited < bound:
        node = stack.pop()
        visited += 1
        try:
            children = node.get_children()
        except Exception:
            continue
        for child in children:
            try:
                extent = child.extent
                start = int(extent.start.line) - 1
                end = int(extent.end.line) - 1
                location = child.location
                name = ""
                if location is not None and location.file is not None:
                    name = str(location.file.name)
            except Exception:
                continue
            if start < 0 or end < start:
                continue
            if main_path and name != main_path:
                continue
            starts.append(start)
            ends.append(end)
            stack.append(child)
    if not starts or not ends or max(ends) <= min(starts):
        return None
    return (min(starts), max(ends))


def _in_main_file(cursor, main_path: Optional[str]) -> bool:
    """Return whether *cursor* is located in the main buffer file."""
    if not main_path:
        return True
    try:
        location = cursor.location
        if location is None or location.file is None:
            return False
        return str(location.file.name) == main_path
    except Exception:
        return False


def _ast_regions(tu, main_path: Optional[str]) -> List[FoldRegion]:
    """Collect fold regions from the translation unit cursor tree."""
    regions: List[FoldRegion] = []
    try:
        stack = list(tu.cursor.get_children())
    except Exception as exc:
        logger.debug("fold AST walk unavailable: %s", exc)
        return regions
    visited = 0
    while stack and visited < _MAX_VISITED:
        cursor = stack.pop()
        visited += 1
        kind = _kind_name(cursor)
        if kind in _FOLDABLE and _in_main_file(cursor, main_path):
            lines = _extent_lines(cursor)
            if lines is None:
                lines = _span_from_children(cursor, main_path)
            if lines is not None:
                regions.append(FoldRegion(
                    start_line=lines[0], end_line=lines[1],
                    kind=_KIND_BY_CURSOR.get(kind, "block")))
        if _in_main_file(cursor, main_path):
            try:
                children = cursor.get_children()
            except Exception:
                continue
            stack.extend(children)
    return regions


def _directive_regions(lines: List[str]) -> List[FoldRegion]:
    """Fold consecutive include runs and conditional blocks."""
    regions: List[FoldRegion] = []
    total = len(lines)
    index = 0
    while index < total:
        if _INCLUDE_LINE.match(lines[index]):
            start = index
            end = index
            index += 1
            while index < total and _INCLUDE_LINE.match(lines[index]):
                end = index
                index += 1
            if end > start:
                regions.append(FoldRegion(start_line=start, end_line=end,
                                          kind="include"))
            continue
        if _COND_OPEN.match(lines[index]):
            start = index
            depth = 0
            index += 1
            while index < total:
                if _COND_OPEN.match(lines[index]):
                    depth += 1
                elif _COND_CLOSE.match(lines[index]):
                    if depth == 0:
                        break
                    depth -= 1
                index += 1
            if index < total and index > start + 1:
                regions.append(FoldRegion(start_line=start, end_line=index,
                                          kind="conditional"))
        index += 1
    return regions


def _brace_fallback(lines: List[str]) -> List[FoldRegion]:
    """Brace-matching fold regions for unparseable buffers."""
    regions: List[FoldRegion] = []
    stack: List[int] = []
    for lineno, line in enumerate(lines):
        stripped = re.sub(r"//[^\n]*", " ", line)
        for char in stripped:
            if char == "{":
                stack.append(lineno)
            elif char == "}" and stack:
                start = stack.pop()
                if lineno > start + 1:
                    regions.append(FoldRegion(start_line=start,
                                              end_line=lineno,
                                              kind="block"))
    return regions


def _dedupe_spans(regions: List[FoldRegion]) -> List[FoldRegion]:
    """Collapse exact-duplicate spans to one region.

    libclang exposes some constructs twice (a typedef with its record,
    a template with its templated declaration). Duplicates double-count
    fold depth, painting markers on lines that own none and corrupting
    nesting. On collision the more specific kind wins.
    """
    best: dict = {}
    for region in regions:
        key = (region.start_line, region.end_line)
        current = best.get(key)
        if current is None or _SPAN_PRIORITY.get(
                region.kind, 9) < _SPAN_PRIORITY.get(current.kind, 9):
            best[key] = region
    return list(best.values())


def compute_fold_regions(source: str, tu=None,
                         main_path: Optional[str] = None) -> List[FoldRegion]:
    """Return fold regions for *source*, AST-first with brace fallback.

    Args:
        source: Full editor buffer content.
        tu: Parsed translation unit, or ``None`` to use the fallback.
        main_path: Main-file path used for walk pruning.

    Returns:
        Regions sorted by start line.
    """
    if not source or not source.strip():
        return []
    lines = source.splitlines()
    regions = _directive_regions(lines)
    if tu is not None:
        try:
            regions.extend(_ast_regions(tu, main_path))
        except Exception as exc:
            logger.debug("AST fold regions failed: %s", exc)
    if not regions:
        regions = _brace_fallback(lines)
    regions = _dedupe_spans(regions)
    regions.sort(key=lambda region: (region.start_line, region.end_line))
    return regions
