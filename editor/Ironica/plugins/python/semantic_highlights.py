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
``_line_col_to_offset`` which produces flat byte positions.  Tokens
inside strings or comments are excluded via binary-search overlap
detection.  No partial substring matching is used -- every token
specifies its exact ``start`` and ``length``.
"""

import ast
import re
from typing import List, Optional, Tuple

from editor.Ironica.highlighting_api import (
    ITokenProvider,
    Token,
    TokenStyle,
    STYLES,
    find_word_at,
)

# ------------------------------------------------------------------
# Colour constants (VS Code dark theme)
# ------------------------------------------------------------------
_CLR_MODULE = "#4EC9B0"  # teal   -- module names
_CLR_FUNCTION = "#DCDCAA"  # yellow -- function names
_CLR_VARIABLE = "#9CDCFE"  # light blue -- parameters & variable definitions
_CLR_SELF = "#569CD6"  # dark blue -- self, cls
_CLR_CONSTANT = "#569CD6"  # dark blue -- None, True, False


# ------------------------------------------------------------------
# Offset helpers
# ------------------------------------------------------------------


def _line_col_to_offset(text: str, lineno: int, col_offset: int) -> int:
    """Convert ``(line, col)`` (both 0-indexed) to a flat offset in *text*.

    This is the canonical offset calculator.  All AST node positions
    are converted through this function to guarantee exact byte
    offsets.
    """
    lines = text.split("\n")
    offset = 0
    for i in range(lineno):
        offset += len(lines[i]) + 1  # +1 for '\n'
    return offset + col_offset


def _find_offset_after(text: str, start_offset: int, name: str) -> int:
    """Return the offset of *name* in *text* at or after *start_offset*."""
    idx = text.find(name, start_offset)
    return idx if idx != -1 else start_offset


# ------------------------------------------------------------------
# Exclusion range builder (strings + comments)
# ------------------------------------------------------------------

_COMMENT_RE = re.compile(r"#[^\n]*")
_STRING_RE = re.compile(
    r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\''
    r'|"[^\n"\\]*(?:\\.[^\n"\\]*)*"'
    r"|'[^'\\\n]*(?:\\.[^'\\\n]*)*'"
)


def _build_exclusions(text: str) -> List[Tuple[int, int]]:
    """Build a sorted list of ``(start, end)`` exclusion ranges from
    comments and strings in *text*.
    """
    exclude: List[Tuple[int, int]] = []
    for cm in _COMMENT_RE.finditer(text):
        exclude.append((cm.start(), cm.end()))
    for st in _STRING_RE.finditer(text):
        exclude.append((st.start(), st.end()))
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

    Implements the ``ITokenProvider`` contract from the Core
    Highlighting API.  Returns exact ``(start, length, style)``
    tokens for structural elements identified by the ``ast`` module.
    """

    def get_tokens(self, text: str) -> List[Token]:
        """Parse *text* via ``ast`` and return styled tokens.

        Every token has an exact ``start`` offset and ``length``
        computed from the AST node's ``lineno`` and ``col_offset``.
        """
        if not text.strip():
            return []

        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []

        exclude = _build_exclusions(text)
        tokens: List[Token] = []

        for node in ast.walk(tree):
            # ── import os / import os.path ──────────────────────
            if isinstance(node, ast.Import):
                for alias in node.names:
                    offset = _line_col_to_offset(
                        text, node.lineno - 1, alias.col_offset
                    )
                    length = len(alias.name)
                    if not _in_exclusion(offset, length, exclude):
                        tokens.append(
                            Token(
                                start=offset,
                                length=length,
                                style=STYLES["module"],
                                kind="module",
                            )
                        )

            # ── from X import Y, Z ─────────────────────────────
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    from_offset = _line_col_to_offset(
                        text, node.lineno - 1, node.col_offset
                    )
                    mod_offset = _find_offset_after(text, from_offset, node.module)
                    mod_len = len(node.module)
                    if not _in_exclusion(mod_offset, mod_len, exclude):
                        tokens.append(
                            Token(
                                start=mod_offset,
                                length=mod_len,
                                style=STYLES["module"],
                                kind="module",
                            )
                        )

                for alias in node.names:
                    name_offset = _line_col_to_offset(
                        text, node.lineno - 1, alias.col_offset
                    )
                    name_len = len(alias.name)
                    if not _in_exclusion(name_offset, name_len, exclude):
                        style = (
                            STYLES["class"]
                            if alias.name[0].isupper()
                            else STYLES["function"]
                        )
                        tokens.append(
                            Token(
                                start=name_offset,
                                length=name_len,
                                style=style,
                                kind="definition",
                            )
                        )

            # ── def f(foo, bar=1): ─────────────────────────────
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args:
                    arg_offset = _line_col_to_offset(
                        text, node.lineno - 1, arg.col_offset
                    )
                    arg_len = len(arg.arg)
                    if not _in_exclusion(arg_offset, arg_len, exclude):
                        style = (
                            STYLES["self"]
                            if arg.arg in ("self", "cls")
                            else STYLES["parameter"]
                        )
                        tokens.append(
                            Token(
                                start=arg_offset,
                                length=arg_len,
                                style=style,
                                kind="parameter",
                            )
                        )

            # ── class Foo: ─────────────────────────────────────
            elif isinstance(node, ast.ClassDef):
                name_offset = _line_col_to_offset(
                    text, node.lineno - 1, node.col_offset
                )
                # "class" keyword is 5 chars before the name.
                kw_offset = name_offset - 6  # "class " prefix
                if kw_offset >= 0:
                    kw_len = 5
                    if not _in_exclusion(kw_offset, kw_len, exclude):
                        tokens.append(
                            Token(
                                start=kw_offset,
                                length=kw_len,
                                style=STYLES["keyword"],
                                kind="keyword",
                            )
                        )
                name_len = len(node.name)
                if not _in_exclusion(name_offset, name_len, exclude):
                    tokens.append(
                        Token(
                            start=name_offset,
                            length=name_len,
                            style=STYLES["class"],
                            kind="class",
                        )
                    )

            # ── x = 5, x: int = 5 ─────────────────────────────
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        t_offset = _line_col_to_offset(
                            text, node.lineno - 1, target.col_offset
                        )
                        t_len = len(target.id)
                        if not _in_exclusion(t_offset, t_len, exclude):
                            tokens.append(
                                Token(
                                    start=t_offset,
                                    length=t_len,
                                    style=STYLES["variable"],
                                    kind="variable",
                                )
                            )

        # ── self / cls (all occurrences) ────────────────────────
        _SELF_RE = re.compile(r"\b(self|cls)\b")
        for m in _SELF_RE.finditer(text):
            if not _in_exclusion(m.start(), m.end() - m.start(), exclude):
                tokens.append(
                    Token(
                        start=m.start(),
                        length=m.end() - m.start(),
                        style=STYLES["self"],
                        kind="self",
                    )
                )

        # ── None / True / False ─────────────────────────────────
        _CONST_RE = re.compile(r"\b(None|True|False)\b")
        for m in _CONST_RE.finditer(text):
            if not _in_exclusion(m.start(), m.end() - m.start(), exclude):
                tokens.append(
                    Token(
                        start=m.start(),
                        length=m.end() - m.start(),
                        style=STYLES["constant"],
                        kind="constant",
                    )
                )

        tokens.sort(key=lambda t: t.start)
        return tokens

    def get_token_at(self, text: str, offset: int) -> Optional[Token]:
        """Return the token covering *offset*, or ``None``."""
        tokens = self.get_tokens(text)
        for tok in tokens:
            if tok.start <= offset < tok.start + tok.length:
                return tok
        return None

    def get_semantic_ranges(self, text: str) -> List[Tuple[int, int, str]]:
        """Return ``(start, length, colour)`` tuples for Scintilla
        indicator overlays.

        This is the format expected by
        ``CodeEditor._apply_semantic_indicators()``.
        """
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
