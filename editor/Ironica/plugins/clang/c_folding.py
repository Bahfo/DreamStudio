"""
(C) COPYRIGHT 2026 Excellent TechStacks - All Rights Reserved.

C/C++ folding logic for DreamStudio.
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple

from editor import *
from editor.Ironica.utils.folding import FoldRegion

logger = logging.getLogger(__name__)

_RE_INCLUDE = re.compile(r"^\s*#\s*include\s+[<\"].+[>\"]")
_RE_PREPROC_START = re.compile(r"^\s*#\s*(if|ifdef|ifndef)\b")
_RE_PREPROC_END = re.compile(r"^\s*#\s*endif\b")
_RE_SINGLE_COMMENT = re.compile(r"^\s*//")


def _strip_non_code(line: str, in_block_comment: bool) -> Tuple[str, bool]:
    """Return code-only text while preserving block-comment state."""
    output: List[str] = []
    index = 0
    length = len(line)

    while index < length:
        if in_block_comment:
            end = line.find("*/", index)
            if end == -1:
                return "".join(output), True
            index = end + 2
            in_block_comment = False
            continue

        if line.startswith("/*", index):
            in_block_comment = True
            index += 2
            continue
        if line.startswith("//", index):
            break

        char = line[index]
        if char in ('"', "'"):
            quote = char
            index += 1
            while index < length:
                if line[index] == "\\":
                    index += 2
                    continue
                if line[index] == quote:
                    index += 1
                    break
                index += 1
            output.append(" ")
            continue

        output.append(char)
        index += 1

    return "".join(output), in_block_comment


def compute_fold_regions(text: str) -> List[FoldRegion]:
    """Parse C source and return non-overlapping foldable regions."""
    if not text:
        return []

    lines = text.split("\n")
    total = len(lines)
    regions: List[FoldRegion] = []
    in_block_comment = False
    comment_start_line = -1
    brace_stack: List[int] = []
    preproc_stack: List[int] = []

    for index, line in enumerate(lines):
        was_in_block_comment = in_block_comment
        code, in_block_comment = _strip_non_code(line, in_block_comment)
        if was_in_block_comment and not in_block_comment and comment_start_line >= 0:
            if index > comment_start_line:
                regions.append(
                    FoldRegion(
                        start_line=comment_start_line,
                        end_line=index - 1,
                        kind="comment",
                    )
                )
            comment_start_line = -1

        if comment_start_line < 0 and "/*" in line:
            comment_start_line = index
        if in_block_comment:
            continue
        if comment_start_line == index and "*/" in line:
            comment_start_line = -1

        if _RE_PREPROC_START.match(code):
            preproc_stack.append(index)
        elif _RE_PREPROC_END.match(code) and preproc_stack:
            start = preproc_stack.pop()
            if index > start:
                regions.append(
                    FoldRegion(
                        start_line=start,
                        end_line=index - 1,
                        kind="preprocessor",
                    )
                )

        for char in code:
            if char == "{":
                brace_stack.append(index)
            elif char == "}":
                if brace_stack:
                    start = brace_stack.pop()
                    if index > start:
                        regions.append(
                            FoldRegion(
                                start_line=start,
                                end_line=index - 1,
                                kind="block",
                            )
                        )

    index = 0
    while index < total:
        if not _RE_INCLUDE.match(lines[index]):
            index += 1
            continue

        start = index
        end = index
        cursor = index + 1
        while cursor < total:
            line = lines[cursor]
            if _RE_INCLUDE.match(line):
                end = cursor
                cursor += 1
                continue
            if _RE_SINGLE_COMMENT.match(line) or not line.strip():
                cursor += 1
                continue
            break

        if end > start:
            regions.append(FoldRegion(start_line=start, end_line=end, kind="include"))
        index = cursor

    regions.sort(key=lambda region: (region.start_line, region.end_line))
    return regions


def _apply_include_fold_text(editor, regions: List[FoldRegion]) -> None:
    """Configure include fold labels for the current editor theme."""
    setup = getattr(editor, "_setup_folding_display_text", None)
    if setup is not None:
        setup()

    set_text = getattr(editor, "set_custom_import_fold_text", None)
    if set_text is None:
        return

    for region in regions:
        if region.kind == "include":
            set_text(
                region.start_line,
                region.end_line - region.start_line + 1,
                "includes",
            )


def compute_folds_for_editor(editor) -> None:
    """Compute and apply C fold regions for an editor buffer."""
    text = editor.text()
    if not text:
        return

    regions = compute_fold_regions(text)
    fold_manager = getattr(editor, "_fold_manager", None)
    if fold_manager is not None:
        _apply_include_fold_text(editor, regions)
        fold_manager.set_fold_regions(regions)
    else:
        _apply_include_fold_text(editor, regions)
