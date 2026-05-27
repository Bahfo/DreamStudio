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

_STATE_NORMAL = 0
_STATE_ML_DQUOTE = 1
_STATE_ML_SQUOTE = 2

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
    "string_doc_sq": 30,
}

_ID_TO_NAME = {v: k for k, v in _STYLE_IDS.items()}

_ESCAPE_RE = re.compile(
    r"\\(x[\da-fA-F]{1,2}|u[\da-fA-F]{4}|U[\da-fA-F]{8}|N\{\w+\}|[0-7]{1,3}|.)"
)
_COMMENT_TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK|NOTE|BUG|OPTIMIZE)\b")
_DUNDER_RE = re.compile(r"__\w+__")
_CAPITAL_WORD_RE = re.compile(r"\b[A-Z][A-Z0-9_]*\b")

_ML_DQUOTE_END_RE = re.compile(r'(?<!\\)(?:\\\\)*"""')
_ML_SQUOTE_END_RE = re.compile(r"(?<!\\)(?:\\\\)*'''")

_TOKEN_RE = re.compile(
    r"(?P<decorator>@[^\W\d]\w*(?:\.[^\W\d]\w*)*)|"
    r"(?P<ml_dq_start>[uUbBfFrR]*\"\"\")|"
    r"(?P<ml_sq_start>[uUbBfFrR]*\'\'\')|"
    r"(?P<fstring>[fF][rR]?\"[^\n\"\\]*(?:\\.[^\n\"\\]*)*\"|[fF][rR]?\'[^\n\'\\]*(?:\\.[^\n\'\\]*)*\')|"
    r"(?P<string>[uUbBrR]*\"[^\n\"\\]*(?:\\.[^\n\"\\]*)*\"|[uUbBrR]*\'[^\n\'\\]*(?:\\.[^\n\'\\]*)*\')|"
    r"(?P<comment>#[^\n]*)|"
    r"(?P<number_float>\b\d(?:_?\d)*\.\d(?:_?\d)*(?:[eE][+-]?\d(?:_?\d)*)?[jJ]?\b|\b\d(?:_?\d)*\.(?=\W|$)|(?<!\w)\.\d(?:_?\d)*(?:[eE][+-]?\d(?:_?\d)*)?[jJ]?\b|\b\d(?:_?\d)*[eE][+-]?\d(?:_?\d)*[jJ]?\b)|"
    r"(?P<number>\b0[xX][\da-fA-F](?:_?[\da-fA-F])*\b|\b0[bB][01](?:_?[01])*\b|\b0[oO][0-7](?:_?[0-7])*\b|\b\d(?:_?\d)*[jJ]?\b)|"
    r"(?P<word>\b[^\W\d]\w*\b)|"
    r"(?P<operator>\*\*|//|<<|>>|==|!=|<=|>=|->|:=|\.\.\.|[-+*/%&|^~<>!=]=?|@=?)|"
    r"(?P<punctuation>[;,.:()\[\]{}])|"
    r"(?P<ws>[ \t\r\n]+)|"
    r"(?P<other>.)"
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
        self.cache: Dict[str, str] = {}
        self._cache_mutex = QMutex()

    def request_analysis(
        self, source: str, path: Optional[str], env_path: Optional[str], request_id: int
    ) -> None:
        self._mutex.lock()
        while len(self._queue) >= 20:
            self._queue.popleft()
        self._queue.append((source, path, env_path, request_id))
        self._cond.wakeOne()
        self._mutex.unlock()

    def get_name_type(self, name: str) -> Optional[str]:
        self._cache_mutex.lock()
        result = self.cache.get(name)
        self._cache_mutex.unlock()
        return result

    def clear_cache(self) -> None:
        self._cache_mutex.lock()
        self.cache.clear()
        self._cache_mutex.unlock()

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
            self._queue.clear()
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

                new_cache: Dict[str, str] = {}
                for n in names:
                    if n.name and n.type in (
                        "function",
                        "class",
                        "module",
                        "param",
                        "instance",
                        "statement",
                        "property",
                    ):
                        new_cache[n.name] = n.type

                self._cache_mutex.lock()
                self.cache = new_cache
                self._cache_mutex.unlock()

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
            fallback = (
                colors.get("string_doc", "#6A9955")
                if style_name == "string_doc_sq"
                else "#D4D4D4"
            )
            hex_color = colors.get(style_name, fallback)
            self.setColor(QColor(hex_color), style_id)
            self.setPaper(QColor("#1E1E1E"), style_id)
            self.setFont(self._default_font, style_id)

    def language(self) -> str:
        return "PythonJedi"

    def description(self, style: int) -> str:
        return f"Python_{_ID_TO_NAME.get(style, 'unknown')}"

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
            lines_on_screen = self._editor.SendScintilla(self._editor.SCI_LINESONSCREEN)
            total_lines = self._editor.SendScintilla(self._editor.SCI_GETLINECOUNT)

            buffer_lines = 50
            start_line = max(0, first_visible - buffer_lines)
            end_line = min(
                total_lines - 1, first_visible + lines_on_screen + buffer_lines
            )

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

    def _get_jedi_type(self, name: str) -> Optional[str]:
        if self._analyzer is None:
            return None
        jedi_type = self._analyzer.get_name_type(name)
        if jedi_type is None:
            return None
        return self._jedi_type_map.get(jedi_type)

    def _style_with_escapes(self, editor, raw: str, base_style: int) -> None:
        if "\\" not in raw:
            editor.SendScintilla(
                editor.SCI_SETSTYLING, len(raw.encode("utf-8")), base_style
            )
            return

        pos = 0
        for m in _ESCAPE_RE.finditer(raw):
            start = m.start()
            if start > pos:
                chunk = raw[pos:start]
                editor.SendScintilla(
                    editor.SCI_SETSTYLING, len(chunk.encode("utf-8")), base_style
                )

            esc = m.group()
            editor.SendScintilla(
                editor.SCI_SETSTYLING, len(esc.encode("utf-8")), _STYLE_IDS["escape"]
            )
            pos = m.end()

        if pos < len(raw):
            chunk = raw[pos:]
            editor.SendScintilla(
                editor.SCI_SETSTYLING, len(chunk.encode("utf-8")), base_style
            )

    def styleText(self, start: int, end: int) -> None:
        editor = self.editor()
        if not editor:
            return

        line_start = editor.SendScintilla(editor.SCI_LINEFROMPOSITION, start)
        current_state = _STATE_NORMAL
        if line_start > 0:
            current_state = editor.SendScintilla(
                editor.SCI_GETLINESTATE, line_start - 1
            )

        full_bytes = editor.text().encode("utf-8")
        text_bytes = full_bytes[start:end]
        text_str = text_bytes.decode("utf-8", errors="replace")

        editor.SendScintilla(editor.SCI_STARTSTYLING, start)

        pos = 0
        text_len = len(text_str)
        current_line = line_start

        def advance_and_style(
            chunk: str, style: int, state_during_chunk: int, state_after_chunk: int
        ) -> int:
            nonlocal pos, current_line

            if style in (
                _STYLE_IDS["string"],
                _STYLE_IDS["string_fstring"],
                _STYLE_IDS["string_doc"],
                _STYLE_IDS["string_doc_sq"],
            ):
                self._style_with_escapes(editor, chunk, style)
            else:
                editor.SendScintilla(
                    editor.SCI_SETSTYLING, len(chunk.encode("utf-8")), style
                )

            newlines = chunk.count("\n")
            for _ in range(newlines):
                editor.SendScintilla(
                    editor.SCI_SETLINESTATE, current_line, state_during_chunk
                )
                current_line += 1

            pos += len(chunk)
            return state_after_chunk

        last_significant_token = None
        last_keyword = None
        expect_annotation = False

        while pos < text_len:
            if current_state == _STATE_ML_DQUOTE:
                match = _ML_DQUOTE_END_RE.search(text_str, pos)
                if not match:
                    chunk = text_str[pos:]
                    current_state = advance_and_style(
                        chunk,
                        _STYLE_IDS["string_doc"],
                        _STATE_ML_DQUOTE,
                        _STATE_ML_DQUOTE,
                    )
                else:
                    chunk = text_str[pos : match.end()]
                    current_state = advance_and_style(
                        chunk, _STYLE_IDS["string_doc"], _STATE_ML_DQUOTE, _STATE_NORMAL
                    )

            elif current_state == _STATE_ML_SQUOTE:
                match = _ML_SQUOTE_END_RE.search(text_str, pos)
                if not match:
                    chunk = text_str[pos:]
                    current_state = advance_and_style(
                        chunk,
                        _STYLE_IDS["string_doc_sq"],
                        _STATE_ML_SQUOTE,
                        _STATE_ML_SQUOTE,
                    )
                else:
                    chunk = text_str[pos : match.end()]
                    current_state = advance_and_style(
                        chunk,
                        _STYLE_IDS["string_doc_sq"],
                        _STATE_ML_SQUOTE,
                        _STATE_NORMAL,
                    )

            else:
                match = _TOKEN_RE.search(text_str, pos)
                if not match:
                    chunk = text_str[pos:]
                    current_state = advance_and_style(
                        chunk, _STYLE_IDS["default"], _STATE_NORMAL, _STATE_NORMAL
                    )
                    break

                start_idx = match.start()
                if start_idx > pos:
                    gap = text_str[pos:start_idx]
                    current_state = advance_and_style(
                        gap, _STYLE_IDS["default"], _STATE_NORMAL, _STATE_NORMAL
                    )

                raw = match.group(0)

                if match.group("ml_dq_start"):
                    current_state = advance_and_style(
                        raw,
                        _STYLE_IDS["string_doc"],
                        _STATE_ML_DQUOTE,
                        _STATE_ML_DQUOTE,
                    )
                    continue
                elif match.group("ml_sq_start"):
                    current_state = advance_and_style(
                        raw,
                        _STYLE_IDS["string_doc_sq"],
                        _STATE_ML_SQUOTE,
                        _STATE_ML_SQUOTE,
                    )
                    continue

                style_id = _STYLE_IDS["default"]

                if match.group("comment"):
                    style_id = (
                        _STYLE_IDS["comment_doc"]
                        if _COMMENT_TODO_RE.search(raw)
                        else _STYLE_IDS["comment"]
                    )
                    last_significant_token = None
                elif match.group("fstring"):
                    style_id = _STYLE_IDS["string_fstring"]
                    last_significant_token = None
                elif match.group("string"):
                    style_id = _STYLE_IDS["string"]
                    last_significant_token = None
                elif match.group("decorator"):
                    style_id = _STYLE_IDS["decorator"]
                    last_significant_token = None
                elif match.group("number_float"):
                    style_id = _STYLE_IDS["number_float"]
                    last_significant_token = None
                elif match.group("number"):
                    style_id = _STYLE_IDS["number"]
                    last_significant_token = None
                elif match.group("operator"):
                    style_id = _STYLE_IDS["operator"]
                    last_significant_token = raw if raw in (".", ":", "->") else None
                    if raw in (":", "->"):
                        expect_annotation = True
                elif match.group("ws"):
                    style_id = _STYLE_IDS["default"]
                elif match.group("word"):
                    word = match.group("word")
                    end_idx = match.end()

                    is_call = False
                    if end_idx < text_len:
                        peek = text_str[end_idx : end_idx + 15].lstrip()
                        if peek.startswith("("):
                            is_call = True

                    if word == "_":
                        style_id = _STYLE_IDS["default"]
                    elif word in ("self", "cls"):
                        style_id = _STYLE_IDS["self"]
                    elif word in ("import", "from"):
                        style_id = _STYLE_IDS["import_keyword"]
                        last_keyword = word
                        expect_annotation = False
                    elif word in self._keyword_map:
                        style_id = _STYLE_IDS.get(
                            self._keyword_map[word], _STYLE_IDS["keyword"]
                        )
                        if word in ("def", "class"):
                            last_keyword = word
                            expect_annotation = False
                    elif word in self._builtin_types:
                        style_id = _STYLE_IDS["builtin_type"]
                    elif word in self._builtins:
                        style_id = _STYLE_IDS["builtin"]
                    elif _CAPITAL_WORD_RE.fullmatch(word) or _DUNDER_RE.fullmatch(word):
                        style_id = _STYLE_IDS["constant"]
                    elif expect_annotation:
                        style_id = _STYLE_IDS["annotation"]
                        expect_annotation = False
                    elif last_significant_token == ".":
                        style_id = _STYLE_IDS["attribute"]
                    else:
                        if last_keyword == "class":
                            style_id = _STYLE_IDS["class"]
                        elif last_keyword == "def":
                            style_id = _STYLE_IDS["function"]
                        else:
                            jedi_type = self._get_jedi_type(word)
                            if jedi_type == "module":
                                style_id = _STYLE_IDS["variable"]
                            elif jedi_type and jedi_type in _STYLE_IDS:
                                style_id = _STYLE_IDS[jedi_type]
                            elif is_call:
                                if word[0].isupper():
                                    style_id = _STYLE_IDS["class"]
                                else:
                                    style_id = _STYLE_IDS["function_call"]
                            elif word[0].isupper():
                                style_id = _STYLE_IDS["class"]
                            else:
                                style_id = _STYLE_IDS["variable"]

                    if word not in ("class", "def", "import", "from"):
                        last_keyword = None

                    if last_significant_token != ".":
                        last_significant_token = "word"

                elif match.group("punctuation"):
                    style_id = _STYLE_IDS["punctuation"]
                    raw = match.group("punctuation")
                    last_significant_token = raw if raw in (".", ":") else None
                    if raw == ":":
                        expect_annotation = True
                    if raw in ("(", ")"):
                        expect_annotation = False
                    if raw in (":", ";", "(", ")"):
                        last_keyword = None

                current_state = advance_and_style(
                    raw, style_id, _STATE_NORMAL, _STATE_NORMAL
                )

        editor.SendScintilla(editor.SCI_SETLINESTATE, current_line, current_state)

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
