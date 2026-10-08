"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Completion context classifier for C++ plugin.
"""

from __future__ import annotations

import re
from typing import Tuple

_INCLUDE = re.compile(r"#\s*include\s*[<\"]([^>\"<>]*)$")
_GUARD = re.compile(
    r"#\s*(ifdef|ifndef|elifdef|elifndef|undef)\s+([A-Za-z_]\w*)?$"
)
_DIRECTIVE = re.compile(r"#\s*([A-Za-z_]\w*)?$")
_TEMPLATE_PREFIX = re.compile(r"<\s*([A-Za-z_]\w*)?$")
_CONSTRUCTION = re.compile(r"\bnew\s+[A-Za-z_]\w*$")
_CALL_PREFIX = re.compile(r"\(\s*([A-Za-z_]\w*)?$")
_MEMBER_COLONS = re.compile(r"::\s*[A-Za-z_]\w*$")
_MEMBER_ARROW = re.compile(r"->\s*[A-Za-z_]\w*$")
_MEMBER_DOT = re.compile(r"\.\s*[A-Za-z_]\w*$")
_MEMBER_EMPTY = re.compile(r"(::|->|\.)\s*$")
_IDENT = re.compile(r"[A-Za-z_]\w*$")


def classify(line_text: str, col: int) -> Tuple[str, str]:
    """
    Classify the completion context at *col* on *line_text*.

    Args:
        line_text: Full text of the current line.
        col: Zero-indexed cursor column.

    Returns:
        ``(kind, prefix)`` where kind is one of ``none``,
        ``identifier``, ``member``, ``construction``, ``call``,
        ``template_args``, ``include``, ``directive``, ``macro_guard``,
        ``preprocessor``, or ``comment``.
    """

    before = line_text[: max(0, col)]
    include_match = _INCLUDE.search(before)
    if include_match:
        return ("include", include_match.group(1))
    guard_match = _GUARD.search(before)
    if guard_match:
        return ("macro_guard", guard_match.group(2) or "")
    directive_match = _DIRECTIVE.search(before)
    if directive_match and before.lstrip().startswith("#"):
        return ("directive", directive_match.group(1) or "")
    if before.lstrip().startswith("#"):
        return ("preprocessor", "")
    comment_at = line_text.find("//")
    if comment_at != -1 and comment_at < max(0, col):
        return ("comment", "")
    for pattern in (_MEMBER_COLONS, _MEMBER_ARROW, _MEMBER_DOT):
        match = pattern.search(before)
        if match:
            tail = match.group(0)
            ident = _IDENT.search(tail)
            return ("member", ident.group(0) if ident else "")
    if _MEMBER_EMPTY.search(before):
        return ("member", "")
    if _CONSTRUCTION.search(before):
        ident = _IDENT.search(before)
        return ("construction", ident.group(0) if ident else "")
    if _TEMPLATE_PREFIX.search(before) and "<" in before:
        ident = _IDENT.search(before)
        tail = ident.group(0) if ident else ""
        return ("template_args", tail)
    call_match = _CALL_PREFIX.search(before)
    if call_match and "(" in before:
        return ("call", call_match.group(1) or "")
    match = _IDENT.search(before)
    if not match:
        return ("none", "")
    return ("identifier", match.group(0))
