"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Completion context classifier for C++ plugin.
"""

from __future__ import annotations

import re
from typing import Tuple

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
        ``(kind, prefix)`` where kind is one of ``none``, ``identifier``,
        ``member``, ``preprocessor``, or ``comment``.
    """

    before = line_text[: max(0, col)]
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
    match = _IDENT.search(before)
    if not match:
        return ("none", "")
    return ("identifier", match.group(0))
