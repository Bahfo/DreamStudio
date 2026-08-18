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
from PyQt6.Qsci import QsciLexerCustom, QsciScintilla

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

# Byte-compiled twins — QScintilla hands us UTF-8 byte offsets, so the
# incremental scanner works on raw bytes to stay perfectly aligned with
# the document even when it contains multi-byte characters.
_RE_NUMBER_B = re.compile(
    rb"""
    (?:
        0[xX][0-9a-fA-F]+
      | 0[bB][01]+
      | 0[oO][0-7]+
      | [0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?
      | \.[0-9]+(?:[eE][+-]?[0-9]+)?
    )
    """,
    re.VERBOSE,
)

_RE_OPERATOR_B = re.compile(
    rb"""
    (?:
        \*\*?=?
      | //=?
      | [+\-*/%]=?
      | <<=?
      | >>=?
      | <=?
      | >=?
      | ==?
      | [~^&|]=?
      | @=?
    )
    """,
    re.VERBOSE,
)

# Identifier token pattern (compiled for `pos` argument support)
_RE_IDENTIFIER = re.compile(r"\w+")
_RE_IDENTIFIER_B = re.compile(rb"\w+")

# C-compiled scan that only visits state-relevant bytes (quotes,
# comment marker, newline, brackets).  Order matters: triple quotes are
# matched before their single-quote prefix.
_RE_STATE_SCAN = re.compile(rb"""\"\"\"|\'\'\'|\"|\'|#|\n|[()\[\]{}]""")

# Single-character bracket tokens
_OPEN_PARENS = frozenset("({[")
_CLOSE_PARENS = frozenset(")}]")
_BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}"}

# C-compiled scan that only visits bracket characters (order-preserving);
# ~6-10x faster than a per-char Python loop over large prefixes.
_BRACKET_REGEX = re.compile(r"[()\[\]{}]")

# Colors
COLOR_REGEX = re.compile(
    r"(#(?:[0-9a-fA-F]{3,4}){1,2}\b|"
    r"rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*(?:0?\.\d+|\d+(?:\.\d+)?)\s*)?\))"
)

# ------------------------------------------------------------------
# Incremental scanner states (carried across styleText calls)
# ------------------------------------------------------------------
_ST_DEFAULT = 0  # plain code
_ST_SINGLE = 1  # inside a '...' string
_ST_DOUBLE = 2  # inside a "..." string
_ST_TRIPLE_S = 3  # inside a '''...''' string
_ST_TRIPLE_D = 4  # inside a """...""" string
_ST_COMMENT = 5  # inside a # comment (until end of line)


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
        self._bracket_cache: Optional[list] = None
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
                        kw,
                        self._keyword_style_names.get(self._keyword_map[kw], "?"),
                        style_name,
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
        number_colour = resolve_colour(
            styles.get("number", "#B5CEA8"), palette, "#B5CEA8"
        )
        operator_colour = resolve_colour(
            styles.get("operator", "#D4D4D4"), palette, "#D4D4D4"
        )

        for offset, triple in (
            (self._paren_offset, paren_colours),
            (self._bracket_offset, bracket_colours),
            (self._brace_offset, brace_colours),
        ):
            for i, col in enumerate(triple):
                self.setColor(QColor(col), offset + i)

        self.setColor(QColor(number_colour), self._number_style)
        self.setColor(QColor(operator_colour), self._operator_style)

        string_colour = resolve_colour(
            styles.get("string", "#CE9178"), palette, "#CE9178"
        )
        comment_colour = resolve_colour(
            styles.get("comment", "#6A9955"), palette, "#6A9955"
        )
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
        if char in "()":
            return self._paren_offset + cycle
        if char in "[]":
            return self._bracket_offset + cycle
        if char in "{}":
            return self._brace_offset + cycle
        return 0

    # ------------------------------------------------------------------
    # Incremental state helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_escaped(data: bytes, pos: int) -> bool:
        """True when ``data[pos]`` is escaped by an odd run of backslashes."""
        backslashes = 0
        pos -= 1
        while pos >= 0 and data[pos] == 0x5C:
            backslashes += 1
            pos -= 1
        return backslashes % 2 == 1

    @classmethod
    def _find_unescaped(cls, data: bytes, start: int, quote: int) -> int:
        """Byte offset of the first unescaped *quote* byte at/after *start*."""
        i = start
        while True:
            j = data.find(quote, i)
            if j == -1 or not cls._is_escaped(data, j):
                return j
            i = j + 1

    @classmethod
    def _find_unescaped_triple(cls, data: bytes, start: int, delim: bytes) -> int:
        """Byte offset of the first unescaped *delim* run at/after *start*."""
        i = start
        while True:
            j = data.find(delim, i)
            if j == -1 or not cls._is_escaped(data, j):
                return j
            i = j + 1

    @classmethod
    def _scan_state(
        cls, data: bytes, state: int, depth_stack: List[str], start: int, stop: int
    ) -> int:
        """Advance *depth_stack* + *state* over ``data[start:stop]``.

        Unlike the simple regex-only ``_scan_bracket_depth`` this respects
        string literals and comments, so brackets inside them never skew
        the depth used for colour cycling.
        """
        pos = start
        while pos < stop:
            m = _RE_STATE_SCAN.search(data, pos, stop)
            if m is None:
                break
            at = m.start()
            ch = data[at]

            if state == _ST_DEFAULT:
                if ch == 0x22 or ch == 0x27:
                    if data[at : at + 3] == b'"""' or data[at : at + 3] == b"'''":
                        state = _ST_TRIPLE_D if ch == 0x22 else _ST_TRIPLE_S
                    else:
                        state = _ST_DOUBLE if ch == 0x22 else _ST_SINGLE
                elif ch == 0x23:  # '#'
                    state = _ST_COMMENT
                elif ch in b"([{":
                    depth_stack.append(chr(ch))
                elif ch in b")]}":
                    c = chr(ch)
                    if depth_stack and _BRACKET_PAIRS.get(depth_stack[-1]) == c:
                        depth_stack.pop()
            elif state in (_ST_SINGLE, _ST_DOUBLE):
                expected = 0x27 if state == _ST_SINGLE else 0x22
                if ch == expected and not cls._is_escaped(data, at):
                    state = _ST_DEFAULT
            elif state in (_ST_TRIPLE_S, _ST_TRIPLE_D):
                delim = b"'''" if state == _ST_TRIPLE_S else b'"""'
                if data[at : at + 3] == delim and not cls._is_escaped(data, at):
                    state = _ST_DEFAULT
            elif state == _ST_COMMENT:
                if ch == 0x0A:
                    state = _ST_DEFAULT

            pos = at + 1
        return state

    # ------------------------------------------------------------------
    # Core lexer entry point
    # ------------------------------------------------------------------

    def styleText(self, start: int, end: int) -> None:
        editor = self.editor()
        if editor is None:
            return

        doc_len = editor.SendScintilla(QsciScintilla.SCI_GETLENGTH)
        if start >= doc_len:
            return

        end = min(end, doc_len)

        # ── Resolve the lexical state + bracket depth before *start* ──
        # QScintilla restyles from the edit position, so when the new
        # start is at/after the previous style end only the delta needs
        # re-scanning (fast path); an edit before the cache point falls
        # back to a full rebuild.
        cached = self._bracket_cache
        if cached is not None and start >= cached[0]:
            depth_stack = cached[1]
            state = cached[2] if len(cached) > 2 else _ST_DEFAULT
            if start > cached[0]:
                delta = self._get_range(editor, cached[0], start)
                if delta:
                    state = self._scan_state(delta, state, depth_stack, 0, len(delta))
        else:
            depth_stack = []
            state = _ST_DEFAULT
            if start > 0:
                prefix = self._get_range(editor, 0, start)
                if prefix:
                    state = self._scan_state(prefix, state, depth_stack, 0, len(prefix))

        data = self._get_range(editor, start, end)
        if not data:
            self._bracket_cache = [end, depth_stack, state]
            return

        self.startStyling(start)

        i = 0
        length = len(data)

        # ── Continuation of a string/comment opened before this range ──
        if state == _ST_SINGLE:
            j = self._find_unescaped(data, i, 0x27)
            if j == -1:
                self.setStyling(length - i, self._string_style)
                self._bracket_cache = [end, depth_stack, _ST_SINGLE]
                return
            self.setStyling(j - i + 1, self._string_style)
            i = j + 1
            state = _ST_DEFAULT
        elif state == _ST_DOUBLE:
            j = self._find_unescaped(data, i, 0x22)
            if j == -1:
                self.setStyling(length - i, self._string_style)
                self._bracket_cache = [end, depth_stack, _ST_DOUBLE]
                return
            self.setStyling(j - i + 1, self._string_style)
            i = j + 1
            state = _ST_DEFAULT
        elif state in (_ST_TRIPLE_S, _ST_TRIPLE_D):
            delim = b"'''" if state == _ST_TRIPLE_S else b'"""'
            j = self._find_unescaped_triple(data, i, delim)
            if j == -1:
                self.setStyling(length - i, self._string_style)
                self._bracket_cache = [end, depth_stack, state]
                return
            self.setStyling(j - i + 3, self._string_style)
            i = j + 3
            state = _ST_DEFAULT
        elif state == _ST_COMMENT:
            j = data.find(b"\n", i)
            if j == -1:
                self.setStyling(length - i, self._comment_style)
                self._bracket_cache = [end, depth_stack, _ST_COMMENT]
                return
            self.setStyling(j - i, self._comment_style)
            i = j
            state = _ST_DEFAULT

        while i < length:
            ch = data[i]

            # ── Skip whitespace ────────────────────────────────────
            if ch in b" \t\r\n":
                self.setStyling(1, 0)
                i += 1
                continue

            # ── Strings (single/double/triple quoted) ──────────────
            if ch == 0x22 or ch == 0x27:
                if data[i : i + 3] in (b'"""', b"'''"):
                    delim = data[i : i + 3]
                    state = _ST_TRIPLE_D if ch == 0x22 else _ST_TRIPLE_S
                    j = self._find_unescaped_triple(data, i + 3, delim)
                    if j == -1:
                        span = length - i
                        self.setStyling(span, self._string_style)
                        i += span
                        continue
                    span = j + 3 - i
                    self.setStyling(span, self._string_style)
                    i += span
                    state = _ST_DEFAULT
                    continue
                quote = 0x27 if ch == 0x27 else 0x22
                state = _ST_SINGLE if ch == 0x27 else _ST_DOUBLE
                j = self._find_unescaped(data, i + 1, quote)
                if j == -1:
                    span = length - i
                    self.setStyling(span, self._string_style)
                    i += span
                    continue
                span = j + 1 - i
                self.setStyling(span, self._string_style)
                i += span
                state = _ST_DEFAULT
                continue

            # ── Comments ───────────────────────────────────────────
            if ch == 0x23:  # '#'
                eol = data.find(b"\n", i)
                if eol == -1:
                    span = length - i
                    self.setStyling(span, self._comment_style)
                    i += span
                    state = _ST_COMMENT
                    continue
                span = eol - i
                self.setStyling(span, self._comment_style)
                i += span
                continue

            # ── Bracket pair colourization ─────────────────────────
            if ch in b"({[":
                depth_stack.append(chr(ch))
                depth = len(depth_stack)
                style = self._bracket_style(chr(ch), depth)
                self.setStyling(1, style)
                i += 1
                continue

            if ch in b")}]":
                c = chr(ch)
                if depth_stack and _BRACKET_PAIRS.get(depth_stack[-1]) == c:
                    depth = len(depth_stack)
                    depth_stack.pop()
                else:
                    depth = 1
                style = self._bracket_style(c, depth)
                self.setStyling(1, style)
                i += 1
                continue

            # ── Numeric literals ───────────────────────────────────
            m = _RE_NUMBER_B.match(data, i)
            if m:
                span = m.end() - i
                self.setStyling(span, self._number_style)
                i += span
                continue

            # ── Operators ──────────────────────────────────────────
            m = _RE_OPERATOR_B.match(data, i)
            if m:
                span = m.end() - i
                self.setStyling(span, self._operator_style)
                i += span
                continue

            # ── Keywords / identifiers ─────────────────────────────
            m = _RE_IDENTIFIER_B.match(data, i)
            if m:
                word = data[i : m.end()].decode("ascii", "ignore")
                span = m.end() - i
                style_idx = self._keyword_map.get(word, 0)
                self.setStyling(span, style_idx)
                i += span
                continue

            # ── Default: anything else (dots, multi-byte chars, …) ─
            self.setStyling(1, 0)
            i += 1

        self._bracket_cache = [end, depth_stack, state]

    @staticmethod
    def _get_range(editor, start: int, end: int) -> bytes:
        """Fetch the UTF-8 bytes of ``[start, end)`` without copying the doc.

        Returns an empty ``bytes`` object when the range is empty.
        """
        if end <= start:
            return b""
        buffer = bytearray(end - start + 1)
        written = editor.SendScintilla(
            QsciScintilla.SCI_GETTEXTRANGE, start, end, buffer
        )
        return bytes(buffer[:written])

    @staticmethod
    def _scan_bracket_depth(
        text: str, begin: int, stop: int, depth_stack: List[str]
    ) -> None:
        """Update *depth_stack* with the bracket balance of text[begin:stop].

        Args:
            text: The full document text.
            begin: Start position to scan (exclusive of the stack state).
            stop: End position to scan.
            depth_stack: Mutable stack updated in place.
        """
        for m in _BRACKET_REGEX.finditer(text, begin, stop):
            ch = m.group(0)
            if ch in _OPEN_PARENS:
                depth_stack.append(ch)
            elif ch in _CLOSE_PARENS:
                if depth_stack and _BRACKET_PAIRS.get(depth_stack[-1]) == ch:
                    depth_stack.pop()


# ------------------------------------------------------------------
# Public factory (kept for backward compatibility)
# ------------------------------------------------------------------


def create_bracket_lexer(editor, config: Optional[dict] = None) -> IronicaLexer:
    """Create and return an ``IronicaLexer`` attached to *editor*.

    If *config* is ``None``, uses an empty config (no keyword highlighting,
    default colours for brackets).
    """
    return IronicaLexer(editor, config or {})
