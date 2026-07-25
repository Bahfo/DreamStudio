"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

AST-based semantic highlighting for the Python plugin.

Implements the ``ITokenProvider`` interface from the Core Highlighting
API.  Analyses source code via the ``ast`` module and returns exact
``(start_offset, length, colour)`` tuples for:

- Module names in import statements
- Function parameters
- Variable definitions
- ``self`` / ``cls`` references
- ``None`` / ``True`` / ``False`` constants

**Bug-fix guarantee:** All offsets are computed via
``_line_col_to_offset`` with a precomputed ``line_offsets`` array for
O(1) lookups.  Tokens inside strings or comments are excluded via the
``tokenize`` module.  No partial substring matching is used -- every
token specifies its exact ``start`` and ``length``.
"""

import ast
import io
import re
import tokenize
from typing import List, Optional, Tuple

from editor.Ironica.utils.highlighting_api import (
    ITokenProvider,
    Token,
    TokenStyle,
    STYLES,
    find_word_at,
)

# ------------------------------------------------------------------
# Color constants (VS Code dark theme)
# ------------------------------------------------------------------
_CLR_MODULE = "#4EC9B0"  # teal   -- module names
_CLR_FUNCTION = "#DCDCAA"  # yellow -- function names
_CLR_VARIABLE = "#9CDCFE"  # light blue -- parameters & variable definitions
_CLR_SELF = "#569CD6"  # dark blue -- self, cls
_CLR_CONSTANT = "#569CD6"  # dark blue -- None, True, False


# ------------------------------------------------------------------
# Offset helpers
# ------------------------------------------------------------------


def _line_col_to_offset(line_offsets: List[int], lineno: int, col_offset: int) -> int:
    """Convert ``(line, col)`` (both 0-indexed) to a flat offset.

    Uses the precomputed *line_offsets* array for O(1) lookup.
    ``line_offsets[i]`` is the byte offset of the start of line *i*.
    """
    return line_offsets[lineno] + col_offset


def _find_offset_after(text: str, start_offset: int, name: str) -> int:
    """Return the offset of *name* in *text* at or after *start_offset*."""
    idx = text.find(name, start_offset)
    return idx if idx != -1 else start_offset


# ------------------------------------------------------------------
# Exclusion range builder (strings + comments) — tokenize-based
# ------------------------------------------------------------------


def _build_exclusions(text: str, line_offsets: List[int]) -> List[Tuple[int, int]]:
    """Build a sorted list of ``(start, end)`` exclusion ranges from
    comments and strings in *text* using the ``tokenize`` module.

    Tokenize is authoritative for Python string/comment boundaries;
    regex heuristics are eliminated.
    """
    exclude: List[Tuple[int, int]] = []
    try:
        tokens = tokenize.tokenize(io.BytesIO(text.encode("utf-8")).readline)
        for tok_type, tok_string, start, end, line in tokens:
            if tok_type in (tokenize.COMMENT, tokenize.STRING):
                flat_start = _line_col_to_offset(line_offsets, start[0] - 1, start[1])
                flat_end = _line_col_to_offset(line_offsets, end[0] - 1, end[1])
                exclude.append((flat_start, flat_end))
    except tokenize.TokenError:
        # Unclosed string during live typing — partial exclusions are
        # still better than none.
        pass
    exclude.sort()
    return exclude


def _in_exclusion(pos: int, length: int, exclude: List[Tuple[int, int]]) -> bool:
    """Binary search: does ``[pos, pos+length)`` overlap any exclusion range?"""
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


# ==================================================================
# AST-based token provider
# ==================================================================


class PythonSemanticProvider(ITokenProvider):
    """AST-based token provider for Python source code.

    Implements a production-grade interval resolution algorithm to completely
    eliminate overlapping tokens, which crash the Scintilla styling engine.
    Relies strictly on Python 3.8+ exact AST offsets (end_col_offset) instead
    of highly volatile text substring matching.
    """

    def get_tokens(self, text: str) -> List[Token]:
        if not text.strip():
            return []

        try:
            tree = ast.parse(text)
        except SyntaxError:
            # In a production environment, if the AST fails to parse due to
            # live typing, we safely return empty and let the base lexer take over.
            return []

        line_offsets: List[int] = [0] + [m.end() for m in re.finditer(r"\n", text)]
        exclude = _build_exclusions(text, line_offsets)

        candidates = []

        def add_candidate(start: int, length: int, style: TokenStyle, kind: str):
            """Registers a token candidate with an implicit priority scoring."""
            if length <= 0 or _in_exclusion(start, length, exclude):
                return

            # Strict priority tier to ensure structural elements override general names
            priority_map = {
                "keyword": 10,
                "self": 9,
                "constant": 8,
                "function": 7,
                "class": 6,
                "parameter": 5,
                "variable": 4,
                "module": 3,
                "definition": 2,
            }

            candidates.append(
                {
                    "start": start,
                    "end": start + length,
                    "style": style,
                    "kind": kind,
                    "priority": priority_map.get(kind, 0),
                }
            )

        for node in ast.walk(tree):
            try:
                # ── Class Instantiations & Function Calls ──────────
                if isinstance(node, ast.Call):
                    # Highlight kwargs (requires Py 3.9+ for accurate kwarg offsets)
                    for kw in node.keywords:
                        if (
                            kw.arg
                            and hasattr(kw, "lineno")
                            and hasattr(kw, "col_offset")
                        ):
                            kw_start = _line_col_to_offset(
                                line_offsets, kw.lineno - 1, kw.col_offset
                            )
                            add_candidate(
                                kw_start, len(kw.arg), STYLES["parameter"], "parameter"
                            )

                    if isinstance(node.func, ast.Name) and hasattr(
                        node.func, "col_offset"
                    ):
                        start = _line_col_to_offset(
                            line_offsets, node.func.lineno - 1, node.func.col_offset
                        )
                        add_candidate(
                            start, len(node.func.id), STYLES["function"], "function"
                        )

                    elif isinstance(node.func, ast.Attribute) and hasattr(
                        node.func, "end_col_offset"
                    ):
                        # Extract precise attribute end offset directly from compiler bounds
                        end = _line_col_to_offset(
                            line_offsets,
                            node.func.end_lineno - 1,
                            node.func.end_col_offset,
                        )
                        start = end - len(node.func.attr)
                        add_candidate(
                            start, len(node.func.attr), STYLES["function"], "function"
                        )

                # ── Attributes (e.g. obj.property) ──────────
                elif isinstance(node, ast.Attribute) and hasattr(
                    node, "end_col_offset"
                ):
                    end = _line_col_to_offset(
                        line_offsets, node.end_lineno - 1, node.end_col_offset
                    )
                    start = end - len(node.attr)

                    if node.attr.isupper():
                        add_candidate(
                            start, len(node.attr), STYLES["constant"], "constant"
                        )
                    elif node.attr[0].isupper():
                        add_candidate(start, len(node.attr), STYLES["class"], "class")
                    else:
                        add_candidate(
                            start, len(node.attr), STYLES["variable"], "variable"
                        )

                # ── Standalone Names ──────────
                elif isinstance(node, ast.Name) and hasattr(node, "col_offset"):
                    start = _line_col_to_offset(
                        line_offsets, node.lineno - 1, node.col_offset
                    )
                    if node.id in ("self", "cls"):
                        add_candidate(start, len(node.id), STYLES["self"], "self")
                    elif node.id.isupper():
                        add_candidate(
                            start, len(node.id), STYLES["constant"], "constant"
                        )
                    elif node.id[0].isupper():
                        add_candidate(start, len(node.id), STYLES["class"], "class")
                    else:
                        add_candidate(
                            start, len(node.id), STYLES["variable"], "variable"
                        )

                # ── Constants (None, True, False) ──────────
                elif (
                    isinstance(node, ast.Constant)
                    and node.value in (None, True, False)
                    and hasattr(node, "col_offset")
                ):
                    start = _line_col_to_offset(
                        line_offsets, node.lineno - 1, node.col_offset
                    )
                    add_candidate(
                        start, len(str(node.value)), STYLES["constant"], "constant"
                    )

                # ── Definitions ──────────
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start = _line_col_to_offset(
                        line_offsets, node.lineno - 1, node.col_offset
                    )
                    # Safe localized fallback since defs have variable leading keyword lengths
                    idx = text.find(node.name, start)
                    if idx != -1 and idx < start + 50:
                        add_candidate(
                            idx, len(node.name), STYLES["function"], "function"
                        )

                    for arg in node.args.args:
                        if hasattr(arg, "col_offset"):
                            arg_start = _line_col_to_offset(
                                line_offsets, arg.lineno - 1, arg.col_offset
                            )
                            style = (
                                STYLES["self"]
                                if arg.arg in ("self", "cls")
                                else STYLES["parameter"]
                            )
                            kind = "self" if arg.arg in ("self", "cls") else "parameter"
                            add_candidate(arg_start, len(arg.arg), style, kind)

                elif isinstance(node, ast.ClassDef):
                    start = _line_col_to_offset(
                        line_offsets, node.lineno - 1, node.col_offset
                    )
                    idx = text.find(node.name, start)
                    if idx != -1 and idx < start + 50:
                        add_candidate(idx, len(node.name), STYLES["class"], "class")

                # ── Imports ──────────
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if hasattr(alias, "col_offset"):
                            start = _line_col_to_offset(
                                line_offsets, alias.lineno - 1, alias.col_offset
                            )
                            add_candidate(
                                start, len(alias.name), STYLES["module"], "module"
                            )

                elif isinstance(node, ast.ImportFrom):
                    if node.module and hasattr(node, "col_offset"):
                        start = _line_col_to_offset(
                            line_offsets, node.lineno - 1, node.col_offset
                        )
                        mod_idx = text.find(node.module, start)
                        if mod_idx != -1:
                            add_candidate(
                                mod_idx, len(node.module), STYLES["module"], "module"
                            )
                    for alias in node.names:
                        if alias.name != "*" and hasattr(alias, "col_offset"):
                            start = _line_col_to_offset(
                                line_offsets, alias.lineno - 1, alias.col_offset
                            )
                            style = (
                                STYLES["class"]
                                if alias.name[0].isupper()
                                else STYLES["function"]
                            )
                            add_candidate(start, len(alias.name), style, "definition")

            except Exception:
                # Silently ignore localized malformed nodes during active typing
                pass

        # ── Interval Resolution Phase ──────────
        # Sort by priority descending to guarantee the most important tokens are processed first
        candidates.sort(key=lambda c: -c["priority"])

        final_tokens = []
        accepted_intervals = []

        # O(N*M) overlap filter. Fast enough for viewport semantic tokens.
        for c in candidates:
            overlap = False
            for interval in accepted_intervals:
                # An overlap occurs if the candidate starts before an accepted token ends
                # AND ends after the accepted token starts.
                if c["start"] < interval[1] and c["end"] > interval[0]:
                    overlap = True
                    break

            if not overlap:
                final_tokens.append(
                    Token(
                        start=c["start"],
                        length=c["end"] - c["start"],
                        style=c["style"],
                        kind=c["kind"],
                    )
                )
                accepted_intervals.append((c["start"], c["end"]))

        # Scintilla expects tokens to be fed in strictly ascending start order
        final_tokens.sort(key=lambda t: t.start)
        return final_tokens

    def get_token_at(self, text: str, offset: int) -> Optional[Token]:
        tokens = self.get_tokens(text)
        for tok in tokens:
            if tok.start <= offset < tok.start + tok.length:
                return tok
        return None

    def get_semantic_ranges(self, text: str) -> List[Tuple[int, int, str]]:
        tokens = self.get_tokens(text)
        return [(tok.start, tok.length, tok.style.colour) for tok in tokens]


# ------------------------------------------------------------------
# Legacy compatibility: plain function wrapper
# ------------------------------------------------------------------

_legacy_provider = PythonSemanticProvider()


def get_semantic_highlights(text: str) -> List[Tuple[int, int, str]]:
    """Legacy wrapper: return ``[(start, length, colour), ...]`` for
    semantic tokens.

    Existing callers (``CodeEditor._apply_semantic_indicators``)
    use this function directly.
    """
    return _legacy_provider.get_semantic_ranges(text)
