"""
AST-based semantic highlighting for the Python plugin.

Analyses source code and returns colour ranges for:

- Module names in import statements  (``import os`` → ``os`` is a module)
- Function parameters                 (``def f(foo)`` → ``foo`` is a parameter)
- Variable definitions                (``x = 5``      → ``x`` is a variable)

No Qt / Scintilla imports — pure Python, safe to test without a GUI.
"""

import ast
import re
from typing import List, Tuple

# VSCode dark-theme colour palette (hex strings).
_CLR_MODULE   = "#4EC9B0"   # teal   — module names
_CLR_FUNCTION = "#DCDCAA"   # yellow — function names
_CLR_VARIABLE = "#9CDCFE"   # light blue — parameters & variable definitions
_CLR_SELF     = "#569CD6"   # dark blue — self, cls


def _line_col_to_offset(text: str, lineno: int, col_offset: int) -> int:
    """Convert ``(line, col)`` (both 0-indexed) to a flat offset in *text*."""
    lines = text.split("\n")
    offset = 0
    for i in range(lineno):
        offset += len(lines[i]) + 1   # +1 for '\n'
    return offset + col_offset


def _find_offset_after(text: str, start_offset: int, name: str) -> int:
    """Return the offset of *name* in *text* at or after *start_offset*."""
    idx = text.find(name, start_offset)
    return idx if idx != -1 else start_offset


def get_semantic_highlights(
    text: str,
) -> List[Tuple[int, int, str]]:
    """Return ``[(start, length, colour), …]`` for semantic tokens.

    Uses the ``ast`` module for structurally reliable detection of
    imports, function parameters, and variable assignments.
    """
    if not text.strip():
        return []

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    highlights: List[Tuple[int, int, str]] = []

    for node in ast.walk(tree):
        # ── import os / import os.path ──────────────────────────
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_offset = _line_col_to_offset(
                    text, node.lineno - 1, alias.col_offset
                )
                highlights.append(
                    (mod_offset, len(alias.name), _CLR_MODULE)
                )

        # ── from X import Y, Z ─────────────────────────────────
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                from_offset = _line_col_to_offset(
                    text, node.lineno - 1, node.col_offset
                )
                mod_offset = _find_offset_after(
                    text, from_offset, node.module
                )
                highlights.append(
                    (mod_offset, len(node.module), _CLR_MODULE)
                )

            for alias in node.names:
                name_offset = _line_col_to_offset(
                    text, node.lineno - 1, alias.col_offset
                )
                colour = (
                    _CLR_MODULE if alias.name[0].isupper()
                    else _CLR_FUNCTION
                )
                highlights.append(
                    (name_offset, len(alias.name), colour)
                )

        # ── def f(foo, bar=1): ─────────────────────────────────
        elif isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                arg_offset = _line_col_to_offset(
                    text, node.lineno - 1, arg.col_offset
                )
                colour = (
                    _CLR_SELF if arg.arg in ("self", "cls")
                    else _CLR_VARIABLE
                )
                highlights.append(
                    (arg_offset, len(arg.arg), colour)
                )

        # ── x = 5, x: int = 5 ─────────────────────────────────
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    t_offset = _line_col_to_offset(
                        text, node.lineno - 1, target.col_offset
                    )
                    highlights.append(
                        (t_offset, len(target.id), _CLR_VARIABLE)
                    )

    # ── self / cls (all occurrences, not just function args) ────
    _SELF_RE = re.compile(r"\b(self|cls)\b")
    for m in _SELF_RE.finditer(text):
        highlights.append(
            (m.start(), m.end() - m.start(), _CLR_SELF)
        )

    # ── filter out anything that lands inside a comment or string ──
    _COMMENT_RE = re.compile(r"#[^\n]*")
    _STRING_RE = re.compile(
        r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\''
        r'|"[^\n"\\]*(?:\\.[^\n"\\]*)*"'
        r"|'[^'\\\n]*(?:\\.[^'\\\n]*)*'"
    )
    # Build exclusion ranges from comments and strings
    exclude = []
    for cm in _COMMENT_RE.finditer(text):
        exclude.append((cm.start(), cm.end()))
    for st in _STRING_RE.finditer(text):
        exclude.append((st.start(), st.end()))
    exclude.sort()

    def _in_exclusion(pos: int, length: int) -> bool:
        """Binary search: does [pos, pos+length) overlap any exclusion range?"""
        lo, hi = 0, len(exclude) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            e_start, e_end = exclude[mid]
            if pos >= e_end:
                lo = mid + 1
            elif pos + length <= e_start:
                hi = mid - 1
            else:
                return True
        return False

    highlights = [
        (s, l, c) for s, l, c in highlights
        if not _in_exclusion(s, l)
    ]

    return highlights
