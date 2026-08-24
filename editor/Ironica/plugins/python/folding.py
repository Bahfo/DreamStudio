"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Python-specific folding logic for DreamStudio.

Parses Python source code to detect collapsible regions based on
indentation depth (Python's native scope mechanism) and feeds
them into the core :class:`FoldManager` API.
"""

from __future__ import annotations

from editor import *

logger = logging.getLogger(__name__)

from editor.Ironica.utils.folding import FoldRegion

# ------------------------------------------------------------------
# Regex patterns for Python block headers
# ------------------------------------------------------------------
_RE_IMPORT = re.compile(r"^\s*(?:from\s+\S+\s+)?import\s+")
_RE_CLASS = re.compile(r"^\s*class\s+\w+")
_RE_DEF = re.compile(r"^\s*(?:async\s+)?def\s+\w+")
_RE_DECORATOR = re.compile(r"^\s*@\w+")
_RE_BLANK = re.compile(r"^\s*$")
_RE_COMMENT = re.compile(r"^\s*#")


def _indent_level(line: str) -> int:
    """Return the number of leading spaces in *line*."""
    count = 0
    for ch in line:
        if ch == " ":
            count += 1
        elif ch == "\t":
            count += 4
        else:
            break
    return count


def _is_block_header(line: str) -> str | None:
    """Classify *line* as a block header."""
    if _RE_IMPORT.match(line):
        return "import"
    if _RE_CLASS.match(line):
        return "class"
    if _RE_DEF.match(line):
        return "function"
    return None


def compute_fold_regions(text: str) -> List[FoldRegion]:
    """Parse Python source *text* and return a list of fold regions."""
    if not text:
        return []

    lines = text.split("\n")
    total = len(lines)
    regions: List[FoldRegion] = []

    # ── Step 1: Pre-calculate lines located within multi-line triple-quotes ──
    is_inside_string = [False] * total
    in_triple_double = False
    in_triple_single = False

    for idx, line in enumerate(lines):
        # Disregard comments when calculating triple-quote entry boundaries
        line_code = (
            line if (in_triple_double or in_triple_single) else line.split("#")[0]
        )

        if in_triple_double:
            is_inside_string[idx] = True
            if '"""' in line_code:
                in_triple_double = False
        elif in_triple_single:
            is_inside_string[idx] = True
            if "'''" in line_code:
                in_triple_single = False
        else:
            td_pos = line_code.find('"""')
            ts_pos = line_code.find("'''")
            if td_pos != -1 and (ts_pos == -1 or td_pos < ts_pos):
                if line_code.count('"""') % 2 != 0:
                    in_triple_double = True
            elif ts_pos != -1 and (td_pos == -1 or ts_pos < td_pos):
                if line_code.count("'''") % 2 != 0:
                    in_triple_single = True

    # ── Step 2: Scan through layout and compute regions ──
    i = 0
    while i < total:
        if is_inside_string[i]:
            i += 1
            continue

        line = lines[i]
        header_kind = _is_block_header(line)

        if header_kind is None:
            i += 1
            continue

        # Check for decorators preceding def/class blocks
        decorator_start = i
        k = i - 1
        while k >= 0:
            if is_inside_string[k]:
                break
            prev_line = lines[k]
            if _RE_DECORATOR.match(prev_line):
                decorator_start = k
                k -= 1
            elif _RE_BLANK.match(prev_line) or _RE_COMMENT.match(prev_line):
                k -= 1
            else:
                break

        header_indent = _indent_level(line)
        start_line = decorator_start

        if header_kind == "import":
            end_line = i
            j = i + 1
            while j < total:
                if is_inside_string[j]:
                    break
                next_line = lines[j]
                next_indent = _indent_level(next_line)

                if next_indent >= header_indent and _RE_IMPORT.match(next_line):
                    end_line = j
                    j += 1
                    continue

                if next_indent > header_indent and (
                    _RE_BLANK.match(next_line) or _RE_COMMENT.match(next_line)
                ):
                    end_line = j
                    j += 1
                    continue
                break

            if end_line > start_line:
                regions.append(
                    FoldRegion(start_line=start_line, end_line=end_line, kind="import")
                )
            i = j

        elif header_kind in ("class", "function"):
            # Robust scan forward across multi-line method signatures targeting trailing colon
            colon_line = i
            for idx in range(i, total):
                if is_inside_string[idx]:
                    colon_line = idx
                    continue
                l_no_comment = lines[idx].split("#")[0].rstrip()
                if l_no_comment.endswith(":"):
                    colon_line = idx
                    break
                if ":" in l_no_comment:
                    colon_line = idx

            body_search_start = colon_line + 1
            end_line = start_line

            j = body_search_start
            while j < total:
                if is_inside_string[j]:
                    end_line = j
                    j += 1
                    continue

                next_line = lines[j]
                next_indent = _indent_level(next_line)

                # Lines containing nested code matching scope limits
                if next_indent > header_indent:
                    end_line = j
                    j += 1
                    continue

                # Empty whitespace structural evaluation check
                if _RE_BLANK.match(next_line) or _RE_COMMENT.match(next_line):
                    has_more_body = False
                    for k in range(j + 1, total):
                        if is_inside_string[k]:
                            has_more_body = True
                            break
                        nk_line = lines[k]
                        if _RE_BLANK.match(nk_line) or _RE_COMMENT.match(nk_line):
                            continue
                        if _indent_level(nk_line) > header_indent:
                            has_more_body = True
                        break
                    if has_more_body:
                        end_line = j
                        j += 1
                        continue
                break

            if end_line > start_line:
                regions.append(
                    FoldRegion(
                        start_line=start_line, end_line=end_line, kind=header_kind
                    )
                )
            i = i + 1
        else:
            i += 1

    regions.sort(key=lambda r: r.start_line)
    return regions


def _apply_import_fold_text(editor, regions: List[FoldRegion]) -> None:
    """Enable the fold display-text feature and tag import folds with a count.

    Uses the ``CodeEditor`` APIs ``_setup_folding_display_text`` and
    ``set_custom_import_fold_text`` so a collapsed import block renders a
    gray ``( ... +N imports)`` label beside its header line.
    """
    setup = getattr(editor, "_setup_folding_display_text", None)
    if setup is not None:
        setup()

    set_text = getattr(editor, "set_custom_import_fold_text", None)
    if set_text is None:
        return

    for region in regions:
        if region.kind != "import":
            continue
        import_count = region.end_line - region.start_line + 1
        set_text(region.start_line, import_count)


def compute_folds_for_editor(editor) -> None:
    """Compute fold regions from editor buffer and update FoldManager."""
    text = editor.text()
    if not text:
        return

    regions = compute_fold_regions(text)
    fm = getattr(editor, "_fold_manager", None)
    if fm is not None:
        # Display text first (fast without active fold levels), then levels.
        _apply_import_fold_text(editor, regions)
        fm.set_fold_regions(regions)
    else:
        _apply_import_fold_text(editor, regions)
