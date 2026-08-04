"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Ironica Lexer — combined keyword + bracket pair colorization + number/operator
lexer for DreamStudio.

Reads all colours from the language JSON config (keywords/*.json), making the
JSON files the **single source of truth** for highlighting colours.

Style index layout (per language config):
   0          DEFAULT
   1..N       keyword styles  (from config["styles"] keys that appear in config["keywords"])
   N+1..N+3   parenthesis depth 1-3
   N+4..N+6   square bracket depth 1-3
   N+7..N+9   curly brace depth 1-3
   N+10       number
   N+11       operator
   N+12       string
   N+13       comment
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Set, Tuple

from PyQt6.QtGui import QColor
from PyQt6.Qsci import QsciLexerCustom

from editor.Ironica.retheme import resolve_colour

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Compiled regex patterns (module-level for speed)
# ------------------------------------------------------------------
_RE_NUMBER = re.compile(
    r"""
    (?:
        0[xX][0-9a-fA-F]+           # hex
      | 0[bB][01]+                   # binary
      | 0[oO][0-7]+                  # octal
      | [0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?  # decimal / float / sci
      | \.[0-9]+(?:[eE][+-]?[0-9]+)?              # .NNN form
    )
    """,
    re.VERBOSE,
)

_RE_OPERATOR = re.compile(
    r"""
    (?:
        \*\*?=?     # **, **=
      | //=?        # //, //=
      | [+\-*/%]=?  # +, -, *, /, % and +=, -=, *=, /=, %=
      | <<=?        # <<, <<=
      | >>=?        # >>, >>=
      | <=?         # <, <=
      | >=?         # >, >=
      | ==?         # =, !=
      | [~^&|]=?    # ~, ^, &, | and compound assigns
      | @=?         # @, @= (matmul)
    )
    """,
    re.VERBOSE,
)

# Identifier token pattern (compiled for `pos` argument support)
_RE_IDENTIFIER = re.compile(r"\w+")

# Single-character bracket tokens
_OPEN_PARENS = frozenset("({[")
_CLOSE_PARENS = frozenset(")}]")
_BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}"}


class IronicaLexer(QsciLexerCustom):
    """Combined keyword + bracket-depth + number + operator lexer.

    All colours are read from the language JSON configuration, making the
    JSON file the single source of truth.

    Usage::

        config = LanguageRegistry.get_config("python")
        lexer = IronicaLexer(editor, config)
        editor.setLexer(lexer)
    """

    def __init__(self, parent, config: dict) -> None:
        super().__init__(parent)
        self.config = config
        self._keyword_map: Dict[str, int] = {}
        self._keyword_style_names: Dict[int, str] = {}
        self._paren_offset: int = 0
        self._bracket_offset: int = 0
        self._brace_offset: int = 0
        self._number_style: int = 0
        self._operator_style: int = 0
        self._string_style: int = 0
        self._comment_style: int = 0
        self._setup_from_config()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _setup_from_config(self) -> None:
        """Read colours from *config* and register all styles."""
        styles = self.config.get("styles", {})
        palette = self.config.get("palette", {}) or {}
        keywords = self.config.get("keywords", {})

        # Determine which style keys are actually used for keywords.
        keyword_keys: Set[str] = set()
        for style_name, kw_list in keywords.items():
            if kw_list and style_name in styles:
                keyword_keys.add(style_name)

        # Assign style indices.
        idx = 1  # style 0 = DEFAULT
        keyword_style_ids: Dict[str, int] = {}
        for style_name in styles:
            if style_name in keyword_keys:
                colour = resolve_colour(styles[style_name], palette, "#D4D4D4")
                self.setColor(QColor(colour), idx)
                keyword_style_ids[style_name] = idx
                self._keyword_style_names[idx] = style_name
                idx += 1

        # Build keyword → style map (first-match wins, no duplicates).
        self._keyword_map.clear()
        for style_name, kw_list in keywords.items():
            sid = keyword_style_ids.get(style_name, 0)
            for kw in kw_list:
                if kw in self._keyword_map:
                    logger.debug(
                        "Keyword %r appears in multiple lists (%r and %r); keeping first",
                        kw, self._keyword_style_names.get(self._keyword_map[kw], "?"), style_name,
                    )
                    continue
                self._keyword_map[kw] = sid

        # Bracket/operator/number offsets.
        self._paren_offset = idx
        self._bracket_offset = idx + 3
        self._brace_offset = idx + 6
        self._number_style = idx + 9
        self._operator_style = idx + 10
        self._string_style = idx + 11
        self._comment_style = idx + 12

        # Register bracket/number/operator colours.
        paren_colours = (
            resolve_colour(styles.get("bracket", "#FFD700"), palette, "#FFD700"),
            resolve_colour(styles.get("bracket_2", "#C678DD"), palette, "#C678DD"),
            resolve_colour(styles.get("bracket_3", "#61AFEF"), palette, "#61AFEF"),
        )
        bracket_colours = (
            resolve_colour(styles.get("bracket", "#E06C75"), palette, "#E06C75"),
            resolve_colour(styles.get("bracket_2", "#D19A66"), palette, "#D19A66"),
            resolve_colour(styles.get("bracket_3", "#56B6C2"), palette, "#56B6C2"),
        )
        brace_colours = (
            resolve_colour(styles.get("bracket", "#98C379"), palette, "#98C379"),
            resolve_colour(styles.get("bracket_2", "#E5C07B"), palette, "#E5C07B"),
            resolve_colour(styles.get("bracket_3", "#C678DD"), palette, "#C678DD"),
        )
        number_colour = resolve_colour(styles.get("number", "#B5CEA8"), palette, "#B5CEA8")
        operator_colour = resolve_colour(styles.get("operator", "#D4D4D4"), palette, "#D4D4D4")

        for offset, triple in (
            (self._paren_offset, paren_colours),
            (self._bracket_offset, bracket_colours),
            (self._brace_offset, brace_colours),
        ):
            for i, col in enumerate(triple):
                self.setColor(QColor(col), offset + i)

        self.setColor(QColor(number_colour), self._number_style)
        self.setColor(QColor(operator_colour), self._operator_style)

        string_colour = resolve_colour(styles.get("string", "#CE9178"), palette, "#CE9178")
        comment_colour = resolve_colour(styles.get("comment", "#6A9955"), palette, "#6A9955")
        self.setColor(QColor(string_colour), self._string_style)
        self.setColor(QColor(comment_colour), self._comment_style)

    def retheme(self, config: dict, bg=None, fg=None) -> None:
        """Re-colour the lexer from a (resolved) *config*.

        Style indices are derived from the order of the ``"styles"``
        keys and the keyword lists, which a resolved config preserves,
        so existing style ids stay valid.  When *bg* / *fg* ``QColor``
        values are given the DEFAULT style (0) is updated as well, which
        keeps the document background and text in sync with the IDE
        theme even while a lexer is attached.  The visible document is
        recoloured immediately via ``SCI_COLOURISE``.
        """
        from PyQt6.Qsci import QsciScintilla

        self.config = config
        self._setup_from_config()
        if bg is not None:
            self.setDefaultPaper(bg)
            self.setPaper(bg, 0)
            for style in range(self._comment_style + 1):
                self.setPaper(bg, style)
        if fg is not None:
            self.setDefaultColor(fg)
            self.setColor(fg, 0)
        editor = self.editor()
        if editor is not None:
            try:
                editor.SendScintilla(QsciScintilla.SCI_COLOURISE, 0, -1)
            except Exception:
                pass

    def description(self, style: int) -> str:
        if style == 0:
            return "Default"
        name = self._keyword_style_names.get(style)
        if name:
            return name
        off = style - self._paren_offset
        if 0 <= off < 3:
            return f"Parenthesis (depth {off + 1})"
        off = style - self._bracket_offset
        if 0 <= off < 3:
            return f"Bracket (depth {off + 1})"
        off = style - self._brace_offset
        if 0 <= off < 3:
            return f"Brace (depth {off + 1})"
        if style == self._number_style:
            return "Numeric literal"
        if style == self._operator_style:
            return "Operator"
        if style == self._string_style:
            return "String"
        if style == self._comment_style:
            return "Comment"
        return ""

    # ------------------------------------------------------------------
    # Bracket colour helpers
    # ------------------------------------------------------------------

    def _bracket_style(self, char: str, depth: int) -> int:
        cycle = (depth - 1) % 3
        if char in "()}":
            return self._paren_offset + cycle
        if char in "[]":
            return self._bracket_offset + cycle
        if char in "{}":
            return self._brace_offset + cycle
        return 0

    # ------------------------------------------------------------------
    # Core lexer entry point
    # ------------------------------------------------------------------

    def styleText(self, start: int, end: int) -> None:
        editor = self.editor()
        if editor is None:
            return

        full_text = editor.text()
        if not full_text:
            return

        total_len = len(full_text)
        if start >= total_len:
            return

        end = min(end, total_len)
        self.startStyling(start)

        # ── Rebuild bracket depth stack from document start ────────
        depth_stack: List[str] = []
        for i in range(start):
            ch = full_text[i]
            if ch in _OPEN_PARENS:
                depth_stack.append(ch)
            elif ch in _CLOSE_PARENS:
                if depth_stack and _BRACKET_PAIRS.get(depth_stack[-1]) == ch:
                    depth_stack.pop()

        # ── Scan the target range ──────────────────────────────────
        text_slice = full_text[start:end]
        i = 0
        text_len = len(text_slice)

        while i < text_len:
            ch = text_slice[i]

            # ── Skip whitespace ────────────────────────────────────
            if ch in " \t\r\n":
                self.setStyling(1, 0)
                i += 1
                continue

            # ── Strings (single/double/triple quoted) ──────────────
            if ch in ('"', "'"):
                quote = ch
                if text_slice[i : i + 3] in ('"""', "'''"):
                    triple = text_slice[i : i + 3]
                    end_triple = text_slice.find(triple, i + 3)
                    if end_triple == -1:
                        span = text_len - i
                    else:
                        span = end_triple + 3 - i
                    self.setStyling(span, self._string_style)
                    i += span
                    continue
                else:
                    j = i + 1
                    while j < text_len:
                        if text_slice[j] == "\\" and j + 1 < text_len:
                            j += 2
                            continue
                        if text_slice[j] == quote:
                            j += 1
                            break
                        j += 1
                    span = j - i
                    self.setStyling(span, self._string_style)
                    i += span
                    continue

            # ── Comments ───────────────────────────────────────────
            if ch == "#":
                eol = text_slice.find("\n", i)
                if eol == -1:
                    span = text_len - i
                else:
                    span = eol - i
                self.setStyling(span, self._comment_style)
                i += span
                continue

            # ── Bracket pair colourization ─────────────────────────
            if ch in _OPEN_PARENS:
                depth_stack.append(ch)
                depth = len(depth_stack)
                style = self._bracket_style(ch, depth)
                self.setStyling(1, style)
                i += 1
                continue

            if ch in _CLOSE_PARENS:
                if depth_stack and _BRACKET_PAIRS.get(depth_stack[-1]) == ch:
                    depth = len(depth_stack)
                    depth_stack.pop()
                else:
                    depth = 1
                style = self._bracket_style(ch, depth)
                self.setStyling(1, style)
                i += 1
                continue

            # ── Numeric literals ───────────────────────────────────
            m = _RE_NUMBER.match(text_slice, i)
            if m:
                span = m.end() - i
                self.setStyling(span, self._number_style)
                i += span
                continue

            # ── Operators ──────────────────────────────────────────
            m = _RE_OPERATOR.match(text_slice, i)
            if m:
                span = m.end() - i
                self.setStyling(span, self._operator_style)
                i += span
                continue

            # ── Keywords / identifiers ─────────────────────────────
            m = _RE_IDENTIFIER.match(text_slice, i)
            if m:
                word = m.group(0)
                span = m.end() - i
                style_idx = self._keyword_map.get(word, 0)
                self.setStyling(span, style_idx)
                i += span
                continue

            # ── Default: anything else (dots, etc.) ────────────────
            self.setStyling(1, 0)
            i += 1


# ------------------------------------------------------------------
# Public factory (kept for backward compatibility)
# ------------------------------------------------------------------


def create_bracket_lexer(editor, config: Optional[dict] = None) -> IronicaLexer:
    """Create and return an ``IronicaLexer`` attached to *editor*.

    If *config* is ``None``, uses an empty config (no keyword highlighting,
    default colours for brackets).
    """
    return IronicaLexer(editor, config or {})
