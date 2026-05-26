import re
import json
import logging
from typing import Optional, Dict, Set, Tuple
from collections import deque

import jedi
from PyQt6.Qsci import QsciLexerCustom
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import (
    QThread,
    QMutex,
    QWaitCondition,
    QTimer,
    pyqtSignal,
)

_STATE_NORMAL = 0
_STATE_ML_DQUOTE = 1
_STATE_ML_SQUOTE = 2

_TRIPLE_DOUBLE = '"""'
_TRIPLE_SINGLE = "'''"

logger = logging.getLogger(__name__)

_HIGHLIGHTS_PATH = "editor/texteditor/keywords/python_highlights.json"

_STYLE_IDS = {
    "default": 0,
    "keyword": 1,
    "keyword_operator": 2,
    "builtin": 3,
    "builtin_type": 4,
    "string": 5,
    "string_doc": 6,
    "string_fstring": 7,
    "comment": 8,
    "comment_doc": 9,
    "number": 10,
    "number_float": 11,
    "function": 12,
    "function_call": 13,
    "class": 14,
    "decorator": 15,
    "self": 16,
    "variable": 17,
    "parameter": 18,
    "constant": 19,
    "module": 20,
    "import_keyword": 21,
    "exception": 22,
    "operator": 23,
    "punctuation": 24,
    "attribute": 25,
    "annotation": 26,
    "type": 27,
    "meta": 28,
    "escape": 29,
}

_ID_TO_NAME = {v: k for k, v in _STYLE_IDS.items()}

_STR_PREFIX = r"(?:[rR](?:[bBfF])?|[bB][rR]?|[fF][rR]?|[uU])"

_ESCAPE_RE = re.compile(r"\\(x[\da-fA-F]{1,2}|u[\da-fA-F]{4}|U[\da-fA-F]{8}|N\{\w+\}|[0-7]{1,3}|.)")

_COMMENT_TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK|NOTE|BUG|OPTIMIZE)\b")

_DUNDER_RE = re.compile(r"__\w+__")

_CAPITAL_WORD_RE = re.compile(r"\b[A-Z][A-Z0-9_]*\b")

_TOKEN_RE = re.compile(
    r"(?P<decorator>@(?:\w+(?:\.\w+)*(?:\s*\([^()]*(?:\([^()]*\)[^()]*)*\))?))|"
    r"(?P<string3>"
    + _STR_PREFIX
    + r'?"""(?:[^"\\]|\\.|"(?!""))*"""|'
    + _STR_PREFIX
    + r"?"
    + r"'''(?:[^'\\]|\\.|'(?!''))*''')|"
    r"(?P<fstring>"
    r'(?:[fF][rR]|[rR][fF]|[fF])"(?:[^"\\]|\\.|{{|}})*"|'
    r"(?:[fF][rR]|[rR][fF]|[fF])'(?:[^\'\\]|\\.|{{|}})*')|"
    r"(?P<string>"
    r'(?:[rR][bB]|[bB][rR]|[rRbBuU])?"(?:[^"\\]|\\.)*"|'
    r"(?:[rR][bB]|[bB][rR]|[rRbBuU])?'(?:[^\'\\]|\\.)*')|"
    r"(?P<comment>#.*)|"
    r"(?P<ellipsis>\.\.\.)|"
    r"(?P<number_float>"
    r"\b\d(_?\d)*\.\d(_?\d)*(?:[eE][+-]?\d(_?\d)*)?[jJ]?\b|"
    r"\b\d(_?\d)*\.(?:[jJ])?(?=\W|$)|"
    r"(?<!\w)\.\d(_?\d)*(?:[eE][+-]?\d(_?\d)*)?[jJ]?\b|"
    r"\b\d(_?\d)*[eE][+-]?\d(_?\d)*[jJ]?\b"
    r")|"
    r"(?P<number>"
    r"\b0[xX][\da-fA-F](_?[\da-fA-F])*\b|"
    r"\b0[bB][01](_?[01])*\b|"
    r"\b0[oO][0-7](_?[0-7])*\b|"
    r"\b\d(_?\d)*[jJ]?\b"
    r")|"
    r"(?P<operator>"
    r":==?|"
    r"\*\*=|//=|<<=|>>=|->|:=|\.\.\.|"
    r"\*\*|//|<<|>>|==|!=|<=|>=|"
    r"[-+*/%&|^~<>!]=?|@=?|="
    r")|"
    r"(?P<punctuation>[;,.:()\[\]{}])|"
    r"(?P<word>\b[^\W\d]\w*\b)|"
    r"(?P<ws>\s+)|"
    r"(?P<other>.)"
)


def _styling_escape(editor, raw_text, base_style, start_byte=0):
    text = raw_text[start_byte:]
    if not text:
        return
    has_escape = "\\" in text
    if not has_escape:
        editor.SendScintilla(
            editor.SCI_SETSTYLING, len(text.encode("utf-8")), base_style
        )
        return
    pos = 0
    for m in _ESCAPE_RE.finditer(text):
        if m.start() > pos:
            editor.SendScintilla(
                editor.SCI_SETSTYLING,
                len(text[pos:m.start()].encode("utf-8")),
                base_style,
            )
        esc_text = m.group()
        editor.SendScintilla(
            editor.SCI_SETSTYLING,
            len(esc_text.encode("utf-8")),
            _STYLE_IDS["escape"],
        )
        pos = m.end()
    if pos < len(text):
        editor.SendScintilla(
            editor.SCI_SETSTYLING,
            len(text[pos:].encode("utf-8")),
            base_style,
        )


class _JediAnalyzer(QThread):
    analysis_complete = pyqtSignal(int)
    analysis_failed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mutex = QMutex()
        self._cond = QWaitCondition()
        self._queue: deque = deque()
        self._running = True
        self.cache: Dict[Tuple[int, int, str], str] = {}
        self._cache_mutex = QMutex()
        self.call_cache: Set[Tuple[int, int, str]] = set()
        self._call_cache_mutex = QMutex()

    def request_analysis(
        self,
        source: str,
        path: Optional[str],
        env_path: Optional[str],
        request_id: int,
    ) -> None:
        self._mutex.lock()
        while len(self._queue) >= 20:
            self._queue.popleft()
        self._queue.append((source, path, env_path, request_id))
        self._cond.wakeOne()
        self._mutex.unlock()

    def get_name_type(self, line: int, col: int, name: str) -> Optional[str]:
        self._cache_mutex.lock()
        result = self.cache.get((line, col, name))
        self._cache_mutex.unlock()
        return result

    def is_call_site(self, line: int, col: int, name: str) -> bool:
        self._call_cache_mutex.lock()
        result = (line, col, name) in self.call_cache
        self._call_cache_mutex.unlock()
        return result

    def clear_cache(self) -> None:
        self._cache_mutex.lock()
        self.cache.clear()
        self._cache_mutex.unlock()
        self._call_cache_mutex.lock()
        self.call_cache.clear()
        self._call_cache_mutex.unlock()

    def run(self) -> None:
        while self._running:
            self._mutex.lock()
            while self._running and not self._queue:
                self._cond.wait(self._mutex, 100)
            if not self._running:
                self._mutex.unlock()
                break
            if not self._queue:
                self._mutex.unlock()
                continue
            source, path, env_path, request_id = self._queue.popleft()
            while self._queue:
                self._queue.popleft()
            self._mutex.unlock()

            try:
                env = jedi.get_default_environment()
                if env_path:
                    try:
                        env = jedi.create_environment(env_path)
                    except Exception:
                        env = jedi.get_default_environment()
                script = jedi.Script(code=source, path=path, environment=env)
                names = script.get_names(all_scopes=True)
                new_cache: Dict[Tuple[int, int, str], str] = {}
                new_call_cache: Set[Tuple[int, int, str]] = set()
                source_lines = source.split("\n")
                for n in names:
                    key = (n.line - 1, n.column, n.name)
                    ntype = n.type
                    if ntype in ("function", "class", "module", "param", "instance", "statement", "property"):
                        new_cache[key] = ntype
                for line_idx, line in enumerate(source_lines):
                    for match in re.finditer(r"\b[^\W\d]\w*\b", line):
                        word = match.group()
                        col = match.start()
                        after_word = line[col + len(word) :].lstrip()
                        if after_word.startswith("("):
                            new_call_cache.add((line_idx, col, word))
                self._cache_mutex.lock()
                self.cache = new_cache
                self._cache_mutex.unlock()
                self._call_cache_mutex.lock()
                self.call_cache = new_call_cache
                self._call_cache_mutex.unlock()
                self.analysis_complete.emit(request_id)
            except Exception:
                logger.exception("Jedi analysis failed")
                self.analysis_failed.emit(request_id)

    def shutdown(self) -> None:
        self._running = False
        self._cond.wakeOne()
        self.wait(2000)


class PythonJediHighlighter(QsciLexerCustom):
    def __init__(self, parent, json_data: Optional[dict] = None) -> None:
        super().__init__(parent)
        self.json_data = json_data or self._load_defaults()
        self._editor = parent
        self._analyzer: Optional[_JediAnalyzer] = None
        self._current_env_path: Optional[str] = None
        self._last_analysis_key: Optional[Tuple[str, Optional[str], Optional[str]]] = (
            None
        )
        self._restyling = False
        self._request_counter = 0
        self._latest_request_id = -1

        self._default_font = QFont("JetBrains Mono", 11)
        self.setDefaultFont(self._default_font)
        self.setDefaultPaper(QColor("#1E1E1E"))
        self.setDefaultColor(QColor("#D4D4D4"))

        self._style_colors: Dict[str, str] = dict(self.json_data.get("styles", {}))

        self._keyword_map: Dict[str, str] = dict(self.json_data.get("keyword_map", {}))

        self._builtins: Set[str] = set(self.json_data.get("builtins", []))
        self._builtin_types: Set[str] = set(self.json_data.get("builtin_types", []))

        self._jedi_type_map: Dict[str, str] = dict(
            self.json_data.get("jedi_type_map", {})
        )

        self._analysis_timer = QTimer(self)
        self._analysis_timer.setSingleShot(True)
        self._analysis_timer.setInterval(300)
        self._analysis_timer.timeout.connect(self._do_analysis)

        self._last_styled_start = 0
        self._last_styled_end = 0
        self._lexer_state = _STATE_NORMAL

        self._init_styles()

    def _load_defaults(self) -> dict:
        try:
            with open(_HIGHLIGHTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.warning(
                "Failed to load %s, using fallback defaults", _HIGHLIGHTS_PATH
            )
            return {
                "styles": {"default": "#D4D4D4"},
                "keyword_map": {},
                "builtins": [],
                "builtin_types": [],
                "jedi_type_map": {},
                "color_theme_keys": {},
            }

    def _init_styles(self) -> None:
        colors = self._style_colors
        for style_name, style_id in _STYLE_IDS.items():
            hex_color = colors.get(style_name, "#D4D4D4")
            self.setColor(QColor(hex_color), style_id)
            self.setPaper(QColor("#1E1E1E"), style_id)
            self.setFont(self._default_font, style_id)

    def language(self) -> str:
        return "PythonJedi"

    def description(self, style: int) -> str:
        name = _ID_TO_NAME.get(style, "unknown")
        return f"Python_{name}"

    def _ensure_analyzer(self) -> None:
        if self._analyzer is None:
            self._analyzer = _JediAnalyzer(self)
            self._analyzer.analysis_complete.connect(self._on_analysis_complete)
            self._analyzer.analysis_failed.connect(self._on_analysis_failed)
            self._analyzer.start()
            self.destroyed.connect(self.shutdown)

    def set_environment(self, venv_path: Optional[str]) -> None:
        self._current_env_path = venv_path

    def schedule_analysis(self) -> None:
        if self._editor is None or self._restyling:
            return
        self._analysis_timer.start()

    def _do_analysis(self) -> None:
        if self._editor is None or self._restyling:
            return
        source = self._editor.text()
        path = getattr(self._editor, "current_file_path", None)
        env = self._current_env_path
        key = (source, path, env)
        if key == self._last_analysis_key:
            return
        self._last_analysis_key = key

        self._request_counter += 1
        request_id = self._request_counter
        self._latest_request_id = request_id

        self._ensure_analyzer()
        self._analyzer.request_analysis(source, path, env, request_id)

    def _safe_recolourise(self) -> None:
        if self._editor is None or self._restyling:
            return
        self._restyling = True
        try:
            first_visible = self._editor.SendScintilla(
                self._editor.SCI_GETFIRSTVISIBLELINE
            )
            lines_on_screen = self._editor.SendScintilla(
                self._editor.SCI_LINESONSCREEN
            )
            total_lines = self._editor.SendScintilla(
                self._editor.SCI_GETLINECOUNT
            )
            buffer_lines = 50
            start_line = max(0, first_visible - buffer_lines)
            end_line = min(total_lines - 1, first_visible + lines_on_screen + buffer_lines)
            start_pos = self._editor.SendScintilla(
                self._editor.SCI_POSITIONFROMLINE, start_line
            )
            end_pos = self._editor.SendScintilla(
                self._editor.SCI_GETLINEENDPOSITION, end_line
            )
            if end_pos > start_pos:
                self._editor.SendScintilla(
                    self._editor.SCI_COLOURISE, start_pos, end_pos
                )
        except Exception:
            total = self._editor.SendScintilla(self._editor.SCI_GETTEXTLENGTH)
            if total > 0:
                self._editor.SendScintilla(self._editor.SCI_COLOURISE, 0, total)
        finally:
            self._restyling = False

    def _on_analysis_complete(self, request_id: int) -> None:
        if request_id != self._latest_request_id:
            return
        self._safe_recolourise()

    def _on_analysis_failed(self, request_id: int) -> None:
        if request_id != self._latest_request_id:
            return
        if self._analyzer is not None:
            self._analyzer.clear_cache()
        self._safe_recolourise()

    def _get_jedi_type(self, line: int, col: int, name: str) -> Optional[str]:
        if self._analyzer is None:
            return None
        jedi_type = self._analyzer.get_name_type(line, col, name)
        if jedi_type is None:
            return None
        return self._jedi_type_map.get(jedi_type)

    def _is_call_site(self, line: int, col: int, name: str) -> bool:
        if self._analyzer is None:
            return False
        return self._analyzer.is_call_site(line, col, name)

    def _slice_bytes(self, full_bytes: bytes, start: int, end: int) -> str:
        return full_bytes[start:end].decode("utf-8", errors="replace")

    def _initial_state_for(self, full_bytes: bytes, start: int):
        if start < 3:
            return None
        scan_start = max(0, start - 8000)
        prefix = self._slice_bytes(full_bytes, scan_start, start)
        stripped_lines = []
        for line in prefix.split("\n"):
            ci = line.find("#")
            if ci >= 0:
                stripped_lines.append(line[:ci])
            else:
                stripped_lines.append(line)
        clean = "\n".join(stripped_lines)
        dq_count = clean.count(_TRIPLE_DOUBLE)
        sq_count = clean.count(_TRIPLE_SINGLE)
        if dq_count % 2 == 1:
            last_dq = clean.rfind(_TRIPLE_DOUBLE)
            before_last = clean[:last_dq]
            stripped_before = []
            for line in before_last.split("\n"):
                ci = line.find("#")
                if ci >= 0:
                    stripped_before.append(line[:ci])
                else:
                    stripped_before.append(line)
            clean_before = "\n".join(stripped_before)
            if clean_before.count(_TRIPLE_DOUBLE) % 2 == 0:
                return (_STATE_ML_DQUOTE, '"')
        if sq_count % 2 == 1:
            last_sq = clean.rfind(_TRIPLE_SINGLE)
            before_last = clean[:last_sq]
            stripped_before = []
            for line in before_last.split("\n"):
                ci = line.find("#")
                if ci >= 0:
                    stripped_before.append(line[:ci])
                else:
                    stripped_before.append(line)
            clean_before = "\n".join(stripped_before)
            if clean_before.count(_TRIPLE_SINGLE) % 2 == 0:
                return (_STATE_ML_SQUOTE, "'")
        return None

    def styleText(self, start: int, end: int) -> None:
        editor = self.editor()
        if not editor:
            return

        length = end - start
        if length <= 0:
            return

        full_bytes = editor.text().encode("utf-8")
        text = self._slice_bytes(full_bytes, start, end)

        full_text = editor.text()
        editor.SendScintilla(editor.SCI_STARTSTYLING, start)

        init_state = self._lexer_state
        detected = self._initial_state_for(full_bytes, start)
        if detected is not None:
            ml_state, qchar = detected
            init_state = ml_state

        in_multiline = init_state in (_STATE_ML_DQUOTE, _STATE_ML_SQUOTE)
        was_multiline = in_multiline
        quote_char = ""
        quote_run = 0
        if init_state == _STATE_ML_DQUOTE:
            quote_char = '"'
        elif init_state == _STATE_ML_SQUOTE:
            quote_char = "'"

        if start == 0:
            line = 0
            col = 0
        else:
            line = editor.SendScintilla(editor.SCI_LINEFROMPOSITION, start)
            line_start_byte = editor.SendScintilla(
                editor.SCI_POSITIONFROMLINE, line
            )
            col = editor.SendScintilla(
                editor.SCI_COUNTCHARACTERS, line_start_byte, start
            )

        last_significant_token = None
        prev_was_def = False
        prev_was_class = False
        expect_annotation = False
        expect_return_annotation = False

        for match in _TOKEN_RE.finditer(text):
            raw = match.group(0)
            byte_len = len(raw.encode("utf-8"))

            current_token_line = line
            current_token_col = col

            tok = "default"
            style_id = _STYLE_IDS["default"]
            styled = False

            if in_multiline:
                closed_by_quotes = False
                for ch in raw:
                    if ch == quote_char:
                        quote_run += 1
                    else:
                        quote_run = 0
                    if quote_run >= 3:
                        in_multiline = False
                        quote_run = 0
                        closed_by_quotes = True
                        break
                if closed_by_quotes or match.group("string3"):
                    if closed_by_quotes:
                        in_multiline = False
                        quote_run = 0
                    tok = "string_doc"
                    style_id = _STYLE_IDS[tok]
                else:
                    tok = "string_doc"
                    style_id = _STYLE_IDS[tok]
                    editor.SendScintilla(
                        editor.SCI_SETSTYLING, byte_len, style_id
                    )
                    for ch in raw:
                        if ch == "\n":
                            line += 1
                            col = 0
                        else:
                            col += 1
                    continue

            if match.group("ellipsis"):
                tok = "punctuation"
                style_id = _STYLE_IDS[tok]
                last_significant_token = None

            elif match.group("comment"):
                tok = "comment"
                style_id = _STYLE_IDS[tok]
                last_significant_token = None
                comment_text = raw[1:]
                if _COMMENT_TODO_RE.search(comment_text):
                    editor.SendScintilla(
                        editor.SCI_SETSTYLING, byte_len, style_id
                    )
                    for ch in raw:
                        if ch == "\n":
                            line += 1
                            col = 0
                        else:
                            col += 1
                    expect_annotation = False
                    expect_return_annotation = False
                    continue

            elif match.group("string3") and not in_multiline:
                tok = "string_doc"
                style_id = _STYLE_IDS[tok]
                last_significant_token = None

            elif match.group("fstring") and not in_multiline:
                tok = "string_fstring"
                style_id = _STYLE_IDS[tok]
                last_significant_token = None

            elif match.group("string") and not in_multiline:
                tok = "string"
                style_id = _STYLE_IDS[tok]
                last_significant_token = None

            elif match.group("number_float") and not in_multiline:
                tok = "number_float"
                style_id = _STYLE_IDS[tok]

            elif match.group("number") and not in_multiline:
                tok = "number"
                style_id = _STYLE_IDS[tok]

            elif match.group("decorator") and not in_multiline:
                tok = "decorator"
                style_id = _STYLE_IDS[tok]
                prev_was_def = False
                prev_was_class = False

            elif match.group("operator") and not in_multiline:
                op = raw
                tok = "operator"
                style_id = _STYLE_IDS[tok]
                if op == ".":
                    last_significant_token = "."
                elif op == "->":
                    expect_return_annotation = True
                    last_significant_token = None
                elif op == ":":
                    expect_annotation = True
                    last_significant_token = None
                else:
                    last_significant_token = None
                prev_was_def = False
                prev_was_class = False

            elif match.group("punctuation") and not in_multiline:
                ch = raw
                tok = "punctuation"
                style_id = _STYLE_IDS[tok]
                if ch == ".":
                    last_significant_token = "."
                elif ch in ("(", ")"):
                    expect_annotation = False
                    last_significant_token = None
                elif ch == ":":
                    expect_annotation = True
                    last_significant_token = None
                else:
                    last_significant_token = None
                prev_was_def = False
                prev_was_class = False

            elif match.group("word") and not in_multiline:
                word = match.group("word")
                actual_line = current_token_line
                actual_col = current_token_col
                if word.isidentifier():
                    if word == "_":
                        tok = "default"
                        style_id = _STYLE_IDS["default"]
                    elif expect_return_annotation:
                        tok = "annotation"
                        style_id = _STYLE_IDS[tok]
                        expect_return_annotation = False
                    elif expect_annotation:
                        tok = "annotation"
                        style_id = _STYLE_IDS[tok]
                        expect_annotation = False
                    elif prev_was_def:
                        tok = "function"
                        style_id = _STYLE_IDS[tok]
                        prev_was_def = False
                    elif prev_was_class:
                        tok = "class"
                        style_id = _STYLE_IDS[tok]
                        prev_was_class = False
                    elif word in ("self", "cls"):
                        tok = "self"
                        style_id = _STYLE_IDS[tok]
                    elif word in self._keyword_map:
                        tok = self._keyword_map[word]
                        style_id = _STYLE_IDS.get(
                            tok, _STYLE_IDS["keyword"]
                        )
                        prev_was_def = word == "def"
                        prev_was_class = word == "class"
                        if word in ("def", "class"):
                            expect_annotation = False
                            expect_return_annotation = False
                    elif word in self._builtin_types:
                        tok = "builtin_type"
                        style_id = _STYLE_IDS[tok]
                    elif word in self._builtins:
                        tok = "builtin"
                        style_id = _STYLE_IDS[tok]
                    elif _CAPITAL_WORD_RE.fullmatch(word):
                        tok = "constant"
                        style_id = _STYLE_IDS[tok]
                    elif _DUNDER_RE.fullmatch(word):
                        tok = "constant"
                        style_id = _STYLE_IDS[tok]
                    else:
                        if self._is_call_site(
                            actual_line, actual_col, word
                        ):
                            tok = "function_call"
                            style_id = _STYLE_IDS["function_call"]
                        else:
                            jedi_type = self._get_jedi_type(
                                actual_line, actual_col, word
                            )
                            if jedi_type and jedi_type in _STYLE_IDS:
                                tok = jedi_type
                                style_id = _STYLE_IDS[jedi_type]
                            elif last_significant_token == ".":
                                tok = "attribute"
                                style_id = _STYLE_IDS[tok]
                                last_significant_token = None
                else:
                    tok = "default"
                    style_id = _STYLE_IDS["default"]

            if not styled:
                if tok in ("string", "string_fstring", "string_doc"):
                    has_escape = "\\" in raw and tok != "string_doc"
                    if has_escape:
                        editor.SendScintilla(
                            editor.SCI_SETSTYLING, 0, style_id
                        )
                        _styling_escape(editor, raw, style_id)
                    else:
                        editor.SendScintilla(
                            editor.SCI_SETSTYLING, byte_len, style_id
                        )
                else:
                    editor.SendScintilla(
                        editor.SCI_SETSTYLING, byte_len, style_id
                    )

            for ch in raw:
                if ch == "\n":
                    line += 1
                    col = 0
                else:
                    col += 1

        if not in_multiline and not was_multiline:
            clean_lines = []
            for line_text in text.split("\n"):
                comment_pos = line_text.find("#")
                if comment_pos >= 0:
                    clean_lines.append(line_text[:comment_pos])
                else:
                    clean_lines.append(line_text)
            clean_text = "\n".join(clean_lines)

            i = 0
            while i < len(clean_text):
                dq = clean_text.find(_TRIPLE_DOUBLE, i)
                sq = clean_text.find(_TRIPLE_SINGLE, i)
                if dq == -1 and sq == -1:
                    break
                if dq != -1 and (sq == -1 or dq < sq):
                    cdq = clean_text.find(_TRIPLE_DOUBLE, dq + 3)
                    if cdq == -1:
                        in_multiline = True
                        quote_char = '"'
                        break
                    i = cdq + 3
                else:
                    csq = clean_text.find(_TRIPLE_SINGLE, sq + 3)
                    if csq == -1:
                        in_multiline = True
                        quote_char = "'"
                        break
                    i = csq + 3

        if in_multiline:
            if quote_char == '"':
                self._lexer_state = _STATE_ML_DQUOTE
            else:
                self._lexer_state = _STATE_ML_SQUOTE
        else:
            self._lexer_state = _STATE_NORMAL

    def apply_syntax_theme(self, t) -> None:
        text_color = t.color("editor.text")
        bg_color = t.color("editor.background")
        self.setDefaultColor(QColor(text_color))
        self.setDefaultPaper(QColor(bg_color))

        theme_key_map = self.json_data.get("color_theme_keys", {})

        for style_name, style_id in _STYLE_IDS.items():
            theme_key = theme_key_map.get(style_name, "editor.text")
            hex_color = t.color(theme_key, text_color)
            self.setColor(QColor(hex_color), style_id)
            self.setPaper(QColor(bg_color), style_id)
            self.setFont(self._default_font, style_id)

    def apply_font(self, font: QFont) -> None:
        self._default_font = QFont(font)
        self.setDefaultFont(self._default_font)
        for style_id in _STYLE_IDS.values():
            self.setFont(self._default_font, style_id)

    def shutdown(self) -> None:
        if self._analyzer is not None:
            try:
                self.destroyed.disconnect(self.shutdown)
            except (TypeError, RuntimeError):
                pass
            self._analyzer.shutdown()
            self._analyzer = None
