"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Ironica Lexer — combined keyword + bracket pair colorization + number/operator lexer for DreamStudio.
"""

from __future__ import annotations

from editor import *

from editor.Ironica.retheme import resolve_colour

logger = logging.getLogger(__name__)

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

_RE_IDENTIFIER = re.compile(r"\w+")
_RE_IDENTIFIER_B = re.compile(rb"\w+")

_RE_STATE_SCAN = re.compile(rb"""\"\"\"|\'\'\'|\"|\'|#|/|\*|\n|[()\[\]{}]""")

_OPEN_PARENS = frozenset("({[")
_CLOSE_PARENS = frozenset(")}]")
_BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}"}

_BRACKET_REGEX = re.compile(r"[()\[\]{}]")

COLOR_REGEX = re.compile(
    r"(#(?:[0-9a-fA-F]{3,4}){1,2}\b|"
    r"rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*(?:0?\.\d+|\d+(?:\.\d+)?)\s*)?\))"
)

_ST_DEFAULT = 0
_ST_SINGLE = 1
_ST_DOUBLE = 2
_ST_TRIPLE_S = 3
_ST_TRIPLE_D = 4
_ST_COMMENT = 5
_ST_BLOCK_COMMENT = 6


class IronicaLexer(QsciLexerCustom):
    """Combined keyword + bracket-depth + number + operator lexer."""

    _CHECKPOINT_EVERY = 8192

    _CHECKPOINT_LIMIT = 2048

    def __init__(self, parent, config: dict) -> None:
        super().__init__(parent)
        self.config = config
        comment_style = str(config.get("comment_style", "hash")).lower()
        self._supports_c_comments = comment_style == "c"
        self._bracket_cache: Optional[list] = None
        self._state_checkpoints: list = []
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


    def _setup_from_config(self) -> None:
        """Read colours from *config* and register all styles."""
        styles = self.config.get("styles", {})
        palette = self.config.get("palette", {}) or {}
        keywords = self.config.get("keywords", {})

        keyword_keys: Set[str] = set()
        for style_name, kw_list in keywords.items():
            if kw_list and style_name in styles:
                keyword_keys.add(style_name)

        idx = 1
        keyword_style_ids: Dict[str, int] = {}
        for style_name in styles:
            if style_name in keyword_keys:
                colour = resolve_colour(styles[style_name], palette, "#D4D4D4")
                self.setColor(QColor(colour), idx)
                keyword_style_ids[style_name] = idx
                self._keyword_style_names[idx] = style_name
                idx += 1

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

        self._paren_offset = idx
        self._bracket_offset = idx + 3
        self._brace_offset = idx + 6
        self._number_style = idx + 9
        self._operator_style = idx + 10
        self._string_style = idx + 11
        self._comment_style = idx + 12

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
        """Re-colour the lexer from a (resolved) *config*."""
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


    def _bracket_style(self, char: str, depth: int) -> int:
        cycle = (depth - 1) % 3
        if char in "()":
            return self._paren_offset + cycle
        if char in "[]":
            return self._bracket_offset + cycle
        if char in "{}":
            return self._brace_offset + cycle
        return 0


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

    def _scan_state(
        self, data: bytes, state: int, depth_stack: List[str], start: int, stop: int
    ) -> int:
        """Advance *depth_stack* + *state* over ``data[start:stop]``."""
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
                elif ch == 0x23 and not self._supports_c_comments:
                    state = _ST_COMMENT
                elif self._supports_c_comments and ch == 0x2F:
                    marker = data[at + 1 : at + 2]
                    if marker == b"/":
                        state = _ST_COMMENT
                    elif marker == b"*":
                        state = _ST_BLOCK_COMMENT
                elif ch in b"([{":
                    depth_stack.append(chr(ch))
                elif ch in b")]}":
                    c = chr(ch)
                    if depth_stack and _BRACKET_PAIRS.get(depth_stack[-1]) == c:
                        depth_stack.pop()
            elif state in (_ST_SINGLE, _ST_DOUBLE):
                expected = 0x27 if state == _ST_SINGLE else 0x22
                if ch == expected and not self._is_escaped(data, at):
                    state = _ST_DEFAULT
            elif state in (_ST_TRIPLE_S, _ST_TRIPLE_D):
                delim = b"'''" if state == _ST_TRIPLE_S else b'"""'
                if data[at : at + 3] == delim and not self._is_escaped(data, at):
                    state = _ST_DEFAULT
            elif state == _ST_COMMENT:
                if ch == 0x0A:
                    state = _ST_DEFAULT
            elif state == _ST_BLOCK_COMMENT:
                if ch == 0x2A and data[at + 1 : at + 2] == b"/":
                    state = _ST_DEFAULT

            pos = at + 1
        return state

    def _checkpoints_before(self, start: int) -> tuple:
        wave = self._state_checkpoints
        while wave and wave[-1][0] > start:
            wave.pop()
        if wave:
            latest = wave[-1]
            return latest[0], latest[1], latest[2]
        return 0, [], _ST_DEFAULT

    def _commit_state(
        self, offset: int, depth_stack: List[str], state: int
    ) -> None:
        self._bracket_cache = [offset, depth_stack, state]
        wave = self._state_checkpoints
        if wave and wave[-1][0] == offset:
            wave[-1] = [offset, list(depth_stack), state]
            return
        wave.append([offset, list(depth_stack), state])
        if len(wave) > self._CHECKPOINT_LIMIT:
            del wave[::2]


    def styleText(self, start: int, end: int) -> None:
        editor = self.editor()
        if editor is None:
            return

        doc_len = editor.SendScintilla(QsciScintilla.SCI_GETLENGTH)
        if start >= doc_len:
            return

        end = min(end, doc_len)

        base_offset, base_stack, base_state = self._checkpoints_before(start)
        depth_stack = list(base_stack)
        state = base_state
        if start > base_offset:
            delta = self._get_range(editor, base_offset, start)
            if delta:
                state = self._scan_state(delta, state, depth_stack, 0, len(delta))
        checkpoint_at = base_offset

        data = self._get_range(editor, start, end)
        if not data:
            self._commit_state(end, depth_stack, state)
            return

        self.startStyling(start)

        i = 0
        length = len(data)

        if state == _ST_SINGLE:
            j = self._find_unescaped(data, i, 0x27)
            if j == -1:
                self.setStyling(length - i, self._string_style)
                self._commit_state(end, depth_stack, _ST_SINGLE)
                return
            self.setStyling(j - i + 1, self._string_style)
            i = j + 1
            state = _ST_DEFAULT
        elif state == _ST_DOUBLE:
            j = self._find_unescaped(data, i, 0x22)
            if j == -1:
                self.setStyling(length - i, self._string_style)
                self._commit_state(end, depth_stack, _ST_DOUBLE)
                return
            self.setStyling(j - i + 1, self._string_style)
            i = j + 1
            state = _ST_DEFAULT
        elif state in (_ST_TRIPLE_S, _ST_TRIPLE_D):
            delim = b"'''" if state == _ST_TRIPLE_S else b'"""'
            j = self._find_unescaped_triple(data, i, delim)
            if j == -1:
                self.setStyling(length - i, self._string_style)
                self._commit_state(end, depth_stack, state)
                return
            self.setStyling(j - i + 3, self._string_style)
            i = j + 3
            state = _ST_DEFAULT
        elif state == _ST_COMMENT:
            j = data.find(b"\n", i)
            if j == -1:
                self.setStyling(length - i, self._comment_style)
                self._commit_state(end, depth_stack, _ST_COMMENT)
                return
            self.setStyling(j - i, self._comment_style)
            i = j
            state = _ST_DEFAULT
        elif state == _ST_BLOCK_COMMENT:
            j = data.find(b"*/", i)
            if j == -1:
                self.setStyling(length - i, self._comment_style)
                self._commit_state(end, depth_stack, _ST_BLOCK_COMMENT)
                return
            span = j + 2 - i
            self.setStyling(span, self._comment_style)
            i += span
            state = _ST_DEFAULT

        check_every = self._CHECKPOINT_EVERY
        while i < length:
            absolute = start + i
            if absolute - checkpoint_at >= check_every:
                self._commit_state(absolute, depth_stack, state)
                checkpoint_at = absolute
            ch = data[i]

            if ch in b" \t\r\n":
                self.setStyling(1, 0)
                i += 1
                continue

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

            if ch == 0x23 and not self._supports_c_comments:
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

            if self._supports_c_comments and ch == 0x2F:
                marker = data[i + 1 : i + 2]
                if marker == b"/":
                    eol = data.find(b"\n", i)
                    if eol == -1:
                        span = length - i
                    else:
                        span = eol - i
                    self.setStyling(span, self._comment_style)
                    i += span
                    state = _ST_COMMENT
                    continue
                if marker == b"*":
                    end_comment = data.find(b"*/", i + 2)
                    if end_comment == -1:
                        span = length - i
                        self.setStyling(span, self._comment_style)
                        i += span
                        state = _ST_BLOCK_COMMENT
                        continue
                    span = end_comment + 2 - i
                    self.setStyling(span, self._comment_style)
                    i += span
                    continue

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

            m = _RE_NUMBER_B.match(data, i)
            if m:
                span = m.end() - i
                self.setStyling(span, self._number_style)
                i += span
                continue

            m = _RE_OPERATOR_B.match(data, i)
            if m:
                span = m.end() - i
                self.setStyling(span, self._operator_style)
                i += span
                continue

            m = _RE_IDENTIFIER_B.match(data, i)
            if m:
                word = data[i : m.end()].decode("ascii", "ignore")
                span = m.end() - i
                style_idx = self._keyword_map.get(word, 0)
                self.setStyling(span, style_idx)
                i += span
                continue

            self.setStyling(1, 0)
            i += 1

        self._commit_state(end, depth_stack, state)

    @staticmethod
    def _get_range(editor, start: int, end: int) -> bytes:
        """Fetch the UTF-8 bytes of ``[start, end)`` without copying the doc."""
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
        """Update *depth_stack* with the bracket balance of text[begin:stop]."""
        for m in _BRACKET_REGEX.finditer(text, begin, stop):
            ch = m.group(0)
            if ch in _OPEN_PARENS:
                depth_stack.append(ch)
            elif ch in _CLOSE_PARENS:
                if depth_stack and _BRACKET_PAIRS.get(depth_stack[-1]) == ch:
                    depth_stack.pop()
