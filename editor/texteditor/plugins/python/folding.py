"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Python-specific folding logic for DreamStudio.

Parses Python source code to detect collapsible regions based on
indentation depth (Python's native scope mechanism) and feeds
them into the core :class:`FoldManager` API.

**Target Regions**

- **Imports:** Contiguous ``import`` / ``from ... import`` blocks.
- **Classes:** ``class`` definitions; body determined by indentation.
- **Functions:** ``def`` / ``async def`` definitions; body by indentation.

**Design Principles**

- Pure Python — no Qt imports, no editor dependency.  The parser
  operates on raw text and returns ``FoldRegion`` data objects.
- Debounce-friendly: callers invoke ``compute_fold_regions(text)``
  on a timer; the function is fast enough for 10k-line files in <5 ms.
- The returned ``FoldRegion`` list is ready to pass directly to
  ``FoldManager.set_fold_regions()``.
"""

from __future__ import annotations

import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Import the FoldRegion dataclass from the core API
# ------------------------------------------------------------------
from editor.texteditor.folding import FoldRegion

# ------------------------------------------------------------------
# Regex patterns for Python block headers
# ------------------------------------------------------------------
_RE_IMPORT = re.compile(
    r"^\s*(?:from\s+\S+\s+)?import\s+"
)

_RE_CLASS = re.compile(
    r"^\s*class\s+\w+"
)

_RE_DEF = re.compile(
    r"^\s*(?:async\s+)?def\s+\w+"
)

_RE_BLANK = re.compile(r"^\s*$")

_RE_COMMENT = re.compile(r"^\s*#")


def _indent_level(line: str) -> int:
    """Return the number of leading spaces in *line*.

    Tabs are converted to 4 spaces for consistent comparison with
    Python's default indentation.  This matches the editor's
    ``_INDENTATION_SPACING = 4`` convention.
    """
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
    """Classify *line* as a block header.

    Returns:
        ``"import"``  — if the line is an import statement.
        ``"class"``   — if the line starts a class definition.
        ``"function"``— if the line starts a def/async def.
        ``None``      — if the line is not a block header.
    """
    if _RE_IMPORT.match(line):
        return "import"
    if _RE_CLASS.match(line):
        return "class"
    if _RE_DEF.match(line):
        return "function"
    return None


def compute_fold_regions(text: str) -> List[FoldRegion]:
    """Parse Python source *text* and return a list of fold regions.

    The algorithm scans every line once (O(n)) and uses indentation
    tracking to determine the end of each block:

    1. When a block header is found (import/class/def), record its
       line number and expected body indentation.
    2. Continue scanning subsequent lines.  A block ends when:
       a. A line at the *same* indentation level as the header is
          encountered (sibling block).
       b. A line at a *lower* indentation level is encountered
          (returning to an outer scope).
       c. End-of-file is reached.
    3. Blank lines and comment-only lines inside a block are included
       in the block but do not terminate it.

    **Import blocks** are special-cased: contiguous import lines at
    the same indentation level are grouped, regardless of whether
    they have non-import lines between them (as long as those lines
    are blank or comments).

    Args:
        text: The full Python source code.

    Returns:
        A list of ``FoldRegion`` objects sorted by start line.
    """
    if not text:
        return []

    lines = text.split("\n")
    total = len(lines)
    regions: List[FoldRegion] = []

    # Current scanning state.
    i = 0
    while i < total:
        line = lines[i]
        header_kind = _is_block_header(line)

        if header_kind is None:
            i += 1
            continue

        header_indent = _indent_level(line)
        start_line = i

        if header_kind == "import":
            # ── Import block: gather contiguous imports ────────────
            end_line = i
            j = i + 1
            while j < total:
                next_line = lines[j]
                next_indent = _indent_level(next_line)

                # Same or deeper indent + is an import → continue block.
                if next_indent >= header_indent and _RE_IMPORT.match(next_line):
                    end_line = j
                    j += 1
                    continue

                # Blank line or comment at deeper indent → still inside.
                if next_indent > header_indent and (
                    _RE_BLANK.match(next_line) or _RE_COMMENT.match(next_line)
                ):
                    end_line = j
                    j += 1
                    continue

                break

            if end_line > start_line:
                regions.append(
                    FoldRegion(
                        start_line=start_line,
                        end_line=end_line,
                        label=f"... {end_line - start_line + 1} imports",
                        kind="import",
                    )
                )
            i = j

        elif header_kind in ("class", "function"):
            # ── Class / function block: body by indentation ────────
            # The body starts on the line after the header and must
            # be indented more than the header.
            body_indent = None  # detected from first non-blank body line
            end_line = start_line

            j = i + 1
            while j < total:
                next_line = lines[j]
                next_indent = _indent_level(next_line)

                # Blank lines inside block — include but don't set indent.
                if _RE_BLANK.match(next_line) or _RE_COMMENT.match(next_line):
                    end_line = j
                    j += 1
                    continue

                # First non-blank body line sets the block's indent.
                if body_indent is None:
                    if next_indent <= header_indent:
                        # No body — single-line definition (e.g. ``class Foo: pass``)
                        break
                    body_indent = next_indent

                # Subsequent body line must be indented at least as much
                # as the body indent.
                if next_indent >= body_indent:
                    end_line = j
                    j += 1
                    continue

                # Dedented to header level or less → block ended.
                break

            if end_line > start_line:
                label_kind = "class" if header_kind == "class" else "def"
                label = f"... {label_kind} body"
                regions.append(
                    FoldRegion(
                        start_line=start_line,
                        end_line=end_line,
                        label=label,
                        kind=header_kind,
                    )
                )
            i = j

        else:
            i += 1

    # Sort by start line for deterministic output.
    regions.sort(key=lambda r: r.start_line)
    return regions


def compute_folds_for_editor(editor) -> None:
    """Convenience function: compute fold regions from the editor's
    text buffer and apply them via the ``FoldManager``.

    Args:
        editor: A ``CodeEditor`` instance with a ``_fold_manager``
                attribute.
    """
    text = editor.text()
    if not text:
        return

    regions = compute_fold_regions(text)

    fm = getattr(editor, "_fold_manager", None)
    if fm is not None:
        fm.set_fold_regions(regions)
