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
}

_ID_TO_NAME = {v: k for k, v in _STYLE_IDS.items()}

_TRIPLE_DOUBLE = '"""'
_TRIPLE_SINGLE = "'''"

_STR_PREFIX = r"(?:[rR](?:[bBfF])?|[bB][rR]?|[fF][rR]?|[uU])"

_TOKEN_RE = re.compile(
    r"(?P<decorator>@\w+(?:\.\w+)*(?:\s*\([^()]*\))?)|"

    r'(?P<string3>'
    + _STR_PREFIX + r'?"""(?:[^"\\]|\\.|"(?!""))*"""|'
    + _STR_PREFIX + r"?" + r"'''(?:[^'\\]|\\.|'(?!''))*''')|"

    r'(?P<fstring>'
    r'(?:[fF][rR]|[rR][fF]|[fF])"(?:[^"\\]|\\.)*"|'
    r"(?:[fF][rR]|[rR][fF]|[fF])'(?:[^\'\\]|\\.)*')|"

    r'(?P<string>'
    r'(?:[rR][bB]|[bB][rR]|[rRbBuU])?"(?:[^"\\]|\\.)*"|'
    r"(?:[rR][bB]|[bB][rR]|[rRbBuU])?'(?:[^\'\\]|\\.)*')|"

    r"(?P<comment>#.*)|"

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
    r"\*\*=|//=|<<=|>>=|->|:=|\.\.\.|"
    r"\*\*|//|<<|>>|==|!=|<=|>=|"
    r"[-+*/%&|^~<>!]=?|@=?|="
    r")|"

    r"(?P<punctuation>[;,.:()\[\]{}])|"
    r"(?P<word>\b[^\W\d]\w*\b)|"
    r"(?P<ws>\s+)|"
    r"(?P<other>.)"
)

_CAPITAL_WORD_RE = re.compile(r"\b[A-Z][A-Z0-9_]*\b")


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
                script = jedi.Script(
                    code=source, path=path, environment=env
                )
                names = script.get_names(all_scopes=True)
                new_cache: Dict[Tuple[int, int, str], str] = {}
                new_call_cache: Set[Tuple[int, int, str]] = set()
                for n in names:
                    key = (n.line - 1, n.column, n.name)
                    ntype = n.type
                    if n.is_definition():
                        if ntype in ("function", "class", "module", "param"):
                            new_cache[key] = ntype
                        elif ntype == "instance":
                            new_cache[key] = "instance"
                        elif ntype == "statement":
                            new_cache[key] = "statement"
                    elif ntype in ("function", "property", "class", "instance"):
                        new_call_cache.add(key)

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
    def __init__(
        self, parent, json_data: Optional[dict] = None
    ) -> None:
        super().__init__(parent)
        self.json_data = json_data or self._load_defaults()
        self._editor = parent
        self._analyzer: Optional[_JediAnalyzer] = None
        self._current_env_path: Optional[str] = None
        self._last_analysis_key: Optional[Tuple[str, Optional[str], Optional[str]]] = None
        self._restyling = False
        self._request_counter = 0
        self._latest_request_id = -1

        self._default_font = QFont("JetBrains Mono", 11)
        self.setDefaultFont(self._default_font)
        self.setDefaultPaper(QColor("#1E1E1E"))
        self.setDefaultColor(QColor("#D4D4D4"))

        self._style_colors: Dict[str, str] = dict(
            self.json_data.get("styles", {})
        )

        self._keyword_map: Dict[str, str] = dict(
            self.json_data.get("keyword_map", {})
        )

        self._builtins: Set[str] = set(
            self.json_data.get("builtins", [])
        )
        self._builtin_types: Set[str] = set(
            self.json_data.get("builtin_types", [])
        )

        self._jedi_type_map: Dict[str, str] = dict(
            self.json_data.get("jedi_type_map", {})
        )

        self._analysis_timer = QTimer(self)
        self._analysis_timer.setSingleShot(True)
        self._analysis_timer.setInterval(300)
        self._analysis_timer.timeout.connect(self._do_analysis)

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

    def _on_analysis_complete(self, request_id: int) -> None:
        if request_id != self._latest_request_id:
            return
        if self._editor is None or self._restyling:
            return
        self._restyling = True
        try:
            total = self._editor.SendScintilla(
                self._editor.SCI_GETTEXTLENGTH
            )
            if total > 0:
                self._editor.SendScintilla(
                    self._editor.SCI_COLOURISE, 0, total
                )
        except Exception:
            pass
        finally:
            self._restyling = False

    def _on_analysis_failed(self, request_id: int) -> None:
        if request_id != self._latest_request_id:
            return
        if self._analyzer is not None:
            self._analyzer.clear_cache()
        if self._editor is not None and not self._restyling:
            self._restyling = True
            try:
                total = self._editor.SendScintilla(
                    self._editor.SCI_GETTEXTLENGTH
                )
                if total > 0:
                    self._editor.SendScintilla(
                        self._editor.SCI_COLOURISE, 0, total
                    )
            except Exception:
                pass
            finally:
                self._restyling = False

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

    def _initial_state_for(
        self, editor, full_bytes: bytes, start: int
    ) -> Optional[Tuple[int, str]]:
        if start < 6:
            return None

        if start > 0:
            prev_style = editor.SendScintilla(
                editor.SCI_GETSTYLEAT, start - 1
            )
            if prev_style == _STYLE_IDS["string_doc"]:
                scan = self._slice_bytes(
                    full_bytes, max(0, start - 6000), start
                )
                last_dq = scan.rfind(_TRIPLE_DOUBLE)
                last_sq = scan.rfind(_TRIPLE_SINGLE)
                q = '"' if last_dq > last_sq else "'"
                return (prev_style, q)

        scan_start = max(0, start - 6000)
        prefix = self._slice_bytes(full_bytes, scan_start, start)

        double_count = prefix.count(_TRIPLE_DOUBLE)
        single_count = prefix.count(_TRIPLE_SINGLE)
        if double_count % 2 == 1:
            return (_STYLE_IDS["string_doc"], '"')
        if single_count % 2 == 1:
            return (_STYLE_IDS["string_doc"], "'")
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

        editor.SendScintilla(editor.SCI_STARTSTYLING, start)

        prev_was_dot = False
        prev_was_def = False
        prev_was_class = False
        in_multiline = False
        quote_run = 0
        quote_char = ""

        if start > 0:
            ml_result = self._initial_state_for(editor, full_bytes, start)
            if ml_result is not None:
                in_multiline = True
                ml_state, quote_char = ml_result
                boundary_start = max(0, start - 3)
                boundary = self._slice_bytes(full_bytes, boundary_start, start)
                for ch in reversed(boundary):
                    if ch == quote_char:
                        quote_run += 1
                    else:
                        break
                if quote_run >= 3:
                    in_multiline = False
                    quote_run = 0

            ctx_scan = max(0, start - 200)
            prefix = self._slice_bytes(full_bytes, ctx_scan, start)
            m = re.search(r"\b(async\s+)?(def|class)\s+\w*\Z", prefix)
            if m:
                category = m.group(2)
                if category == "def":
                    prev_was_def = True
                elif category == "class":
                    prev_was_class = True

            stripped = prefix.rstrip()
            if stripped.endswith("."):
                prev_was_dot = True

        byte_offset = 0
        for match in _TOKEN_RE.finditer(text):
            raw = match.group(0)
            byte_len = len(raw.encode("utf-8"))

            tok = "default"
            style_id = _STYLE_IDS["default"]

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

                if closed_by_quotes:
                    tok = "string_doc"
                    style_id = _STYLE_IDS[tok]
                elif match.group("string3"):
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
                    byte_offset += byte_len
                    continue

            if match.group("comment"):
                tok = "comment"
                style_id = _STYLE_IDS[tok]

            elif match.group("string3"):
                tok = "string_doc"
                style_id = _STYLE_IDS[tok]

            elif match.group("fstring"):
                tok = "string_fstring"
                style_id = _STYLE_IDS[tok]

            elif match.group("string"):
                tok = "string"
                style_id = _STYLE_IDS[tok]

            elif match.group("number_float"):
                tok = "number_float"
                style_id = _STYLE_IDS[tok]

            elif match.group("number"):
                tok = "number"
                style_id = _STYLE_IDS[tok]

            elif match.group("decorator"):
                tok = "decorator"
                style_id = _STYLE_IDS[tok]
                prev_was_def = False
                prev_was_class = False

            elif match.group("operator"):
                tok = "operator"
                style_id = _STYLE_IDS[tok]
                prev_was_dot = raw == "."
                prev_was_def = False
                prev_was_class = False

            elif match.group("punctuation"):
                ch = raw
                tok = "punctuation"
                style_id = _STYLE_IDS[tok]
                prev_was_dot = ch == "."
                prev_was_def = False
                prev_was_class = False

            elif match.group("word"):
                word = match.group("word")
                actual_pos = start + byte_offset
                actual_line = editor.SendScintilla(
                    editor.SCI_LINEFROMPOSITION, actual_pos
                )
                line_start_byte = editor.SendScintilla(
                    editor.SCI_POSITIONFROMLINE, actual_line
                )
                actual_col = editor.SendScintilla(
                    editor.SCI_COUNTCHARACTERS, line_start_byte, actual_pos
                )

                if prev_was_def:
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
                elif word in self._builtin_types:
                    tok = "builtin_type"
                    style_id = _STYLE_IDS[tok]
                elif word in self._builtins:
                    tok = "builtin"
                    style_id = _STYLE_IDS[tok]
                elif _CAPITAL_WORD_RE.fullmatch(word):
                    tok = "constant"
                    style_id = _STYLE_IDS[tok]
                else:
                    if self._is_call_site(actual_line, actual_col, word):
                        tok = "function_call"
                        style_id = _STYLE_IDS["function_call"]
                    else:
                        jedi_type = self._get_jedi_type(
                            actual_line, actual_col, word
                        )
                        if jedi_type and jedi_type in _STYLE_IDS:
                            tok = jedi_type
                            style_id = _STYLE_IDS[jedi_type]
                        elif prev_was_dot:
                            tok = "attribute"
                            style_id = _STYLE_IDS[tok]
                            prev_was_dot = False

                prev_was_dot = False

            elif match.group("ws"):
                tok = "default"
                style_id = _STYLE_IDS["default"]

            else:
                tok = "default"
                style_id = _STYLE_IDS["default"]

            editor.SendScintilla(
                editor.SCI_SETSTYLING, byte_len, style_id
            )

            byte_offset += byte_len

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

    def shutdown(self) -> None:
        if self._analyzer is not None:
            try:
                self.destroyed.disconnect(self.shutdown)
            except (TypeError, RuntimeError):
                pass
            self._analyzer.shutdown()
            self._analyzer = None
