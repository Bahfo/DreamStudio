"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Python Syntax Highlighter (Ironica) for DreamStudio.
"""
# Written by Bahaa Nofal - 31/5/2026

import re
import json
import logging
from typing import Optional, Dict, Set

from PyQt6.Qsci import QsciLexerCustom
from PyQt6.QtGui import QColor, QFont

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
    "function": 12,        # Used ONLY for definition
    "function_call": 13,   # Unused with new rules
    "class": 14,           # Used ONLY for definition
    "decorator": 15,
    "self": 16,
    "variable": 17,        # Unused with new rules
    "parameter": 18,       # Used ONLY inside def(...)
    "constant": 19,
    "module": 20,          # Unused with new rules
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

_ESCAPE_RE = re.compile(r"""\\(x[\da-fA-F]{1,2}|u[\da-fA-F]{4}|U[\da-fA-F]{8}
                        |N\{\w+\}|[0-7]{1,3}|.)""", re.VERBOSE)
_COMMENT_TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK|NOTE|BUG|OPTIMIZE)\b")
_DUNDER_RE = re.compile(r"__\w+__")
_CAPITAL_WORD_RE = re.compile(r"\b[A-Z][A-Z0-9_]*\b")

_ML_DQUOTE_END_RE = re.compile(r'(?<!\\)(?:\\\\)*"""')
_ML_SQUOTE_END_RE = re.compile(r"(?<!\\)(?:\\\\)*'''")

_TOKEN_RE = re.compile(r"""
    (?P<decorator> @ [^\W\d] \w* (?: \. [^\W\d] \w* )* )
    |(?P<ml_dq_start> [uUbBfFrR]* \"\"\" )
    |(?P<ml_sq_start> [uUbBfFrR]* ''' )
    |(?P<fstring> [fF][rR]? " [^\n\"\\]* (?: \\ . [^\n\"\\]* )* " 
        |[fF][rR]? ' [^\n\'\\]* (?: \\ . [^\n\'\\]* )* ')
    |(?P<string> [uUbBrR]* " [^\n\"\\]* (?: \\ . [^\n\"\\]* )* " 
        |[uUbBrR]* ' [^\n\'\\]* (?: \\ . [^\n\'\\]* )* ')
    |(?P<comment> \# [^\n]* )
    |(?P<number_float> 
        \b \d (?: _? \d )* \. \d (?: _? \d )* (?: [eE] [+-]? \d (?: _? \d )* )? [jJ]? \b 
        | \b \d (?: _? \d )* \. (?= \W | $ )
        | (?<! \w ) \. \d (?: _? \d )* (?: [eE] [+-]? \d (?: _? \d )* )? [jJ]? \b
        | \b \d (?: _? \d )* [eE] [+-]? \d (?: _? \d )* [jJ]? \b)
    |(?P<number> \b 0 [xX] [\da-fA-F] (?: _? [\da-fA-F] )* \b
        | \b 0 [bB] [01] (?: _? [01] )* \b
        | \b 0 [oO] [0-7] (?: _? [0-7] )* \b
        | \b \d (?: _? \d )* [jJ]? \b)
    |(?P<word> \b [^\W\d] \w* \b )
    |(?P<operator> 
        \*\* | // | << | >> | == | != | <= | >= | -> | := | \.\.\. 
        | [-+*/%&|^~<>!=] =? | @=?)
    |(?P<punctuation> [;,.:()\[\]{}] )
    |(?P<ws> [ \t\r\n]+ )
    |(?P<other> . )
""", re.VERBOSE)

class DreamPythonHighlighter(QsciLexerCustom):
    def __init__(self, parent, json_data: Optional[dict] = None) -> None:
        super().__init__(parent)
        self.json_data = json_data or self._load_defaults()
        self._editor = parent
        
        self._default_font = QFont("JetBrains Mono", 11)
        self.setDefaultFont(self._default_font)
        self.setDefaultPaper(QColor("#1E1E1E"))
        self.setDefaultColor(QColor("#D4D4D4"))

        self._style_colors: Dict[str, str] = dict(self.json_data.get("styles", {}))
        self._keyword_map: Dict[str, str] = dict(self.json_data.get("keyword_map", {}))
        self._builtins: Set[str] = set(self.json_data.get("builtins", []))
        self._builtin_types: Set[str] = set(self.json_data.get("builtin_types", []))
        self._exceptions: Set[str] = set(self.json_data.get("exceptions", []))

        self._init_styles()

    def _load_defaults(self) -> dict:
        try:
            with open(_HIGHLIGHTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.warning("Failed to load %s, using fallback defaults", _HIGHLIGHTS_PATH)
            return {"styles": {"default": "#D4D4D4"}, "keyword_map": {}, 
                "builtins": [], "builtin_types": [], "exceptions": []}

    def _init_styles(self) -> None:
        colors = self._style_colors
        for style_name, style_id in _STYLE_IDS.items():
            fallback = colors.get("string_doc", "#6A9955") if style_name == "string_doc_sq" else "#D4D4D4"
            hex_color = colors.get(style_name, fallback)
            self.setColor(QColor(hex_color), style_id)
            self.setPaper(QColor("#1E1E1E"), style_id)
            self.setFont(self._default_font, style_id)

    def language(self) -> str:
        return "Python"

    def description(self, style: int) -> str:
        return f"Python_{_ID_TO_NAME.get(style, 'unknown')}"

    def _style_with_escapes(self, editor, raw: str, base_style: int) -> None:
        if "\\" not in raw:
            editor.SendScintilla(editor.SCI_SETSTYLING, len(raw.encode("utf-8")), base_style)
            return

        pos = 0
        for m in _ESCAPE_RE.finditer(raw):
            start = m.start()
            if start > pos:
                chunk = raw[pos:start]
                editor.SendScintilla(editor.SCI_SETSTYLING, len(chunk.encode("utf-8")), base_style)

            esc = m.group()
            editor.SendScintilla(editor.SCI_SETSTYLING, len(esc.encode("utf-8")), _STYLE_IDS["escape"])
            pos = m.end()

        if pos < len(raw):
            chunk = raw[pos:]
            editor.SendScintilla(editor.SCI_SETSTYLING, len(chunk.encode("utf-8")), base_style)

    def styleText(self, start: int, end: int) -> None:
        editor = self.editor()
        if not editor:
            return

        line_start = editor.SendScintilla(editor.SCI_LINEFROMPOSITION, start)
        current_state = _STATE_NORMAL
        if line_start > 0:
            current_state = editor.SendScintilla(editor.SCI_GETLINESTATE, line_start - 1)

        full_bytes = editor.text().encode("utf-8")
        text_bytes = full_bytes[start:end]
        text_str = text_bytes.decode("utf-8", errors="replace")

        editor.SendScintilla(editor.SCI_STARTSTYLING, start)

        pos = 0
        text_len = len(text_str)
        current_line = line_start

        def advance_and_style(chunk: str, style: int, state_during_chunk: int, 
            state_after_chunk: int) -> int:
            nonlocal pos, current_line
            if style in (_STYLE_IDS["string"], _STYLE_IDS["string_fstring"], 
                _STYLE_IDS["string_doc"], _STYLE_IDS["string_doc_sq"]):
                self._style_with_escapes(editor, chunk, style)
            else:
                editor.SendScintilla(editor.SCI_SETSTYLING, len(chunk.encode("utf-8")), style)

            newlines = chunk.count("\n")
            for _ in range(newlines):
                editor.SendScintilla(editor.SCI_SETLINESTATE, current_line, state_during_chunk)
                current_line += 1
            pos += len(chunk)
            return state_after_chunk

        # Context Tracking State Machine
        last_keyword = None
        in_def_params = False
        param_depth = 0
        expect_annotation = False

        while pos < text_len:
            if current_state == _STATE_ML_DQUOTE:
                match = _ML_DQUOTE_END_RE.search(text_str, pos)
                if not match:
                    current_state = advance_and_style(text_str[pos:], _STYLE_IDS["string_doc"], 
                        _STATE_ML_DQUOTE, _STATE_ML_DQUOTE)
                    break
                else:
                    current_state = advance_and_style(text_str[pos:match.end()], _STYLE_IDS["string_doc"],
                        _STATE_ML_DQUOTE, _STATE_NORMAL)

            elif current_state == _STATE_ML_SQUOTE:
                match = _ML_SQUOTE_END_RE.search(text_str, pos)
                if not match:
                    current_state = advance_and_style(text_str[pos:], _STYLE_IDS["string_doc_sq"], 
                        _STATE_ML_SQUOTE, _STATE_ML_SQUOTE)
                    break
                else:
                    current_state = advance_and_style(text_str[pos:match.end()], 
                        _STYLE_IDS["string_doc_sq"], _STATE_ML_SQUOTE, _STATE_NORMAL)

            else:
                match = _TOKEN_RE.search(text_str, pos)
                if not match:
                    current_state = advance_and_style(text_str[pos:], _STYLE_IDS["default"], 
                        _STATE_NORMAL, _STATE_NORMAL)
                    break

                if match.start() > pos:
                    current_state = advance_and_style(text_str[pos:match.start()], 
                        _STYLE_IDS["default"], _STATE_NORMAL, _STATE_NORMAL)

                raw = match.group(0)

                if match.group("ml_dq_start"):
                    current_state = advance_and_style(raw, _STYLE_IDS["string_doc"], 
                        _STATE_ML_DQUOTE, _STATE_ML_DQUOTE)
                    continue
                elif match.group("ml_sq_start"):
                    current_state = advance_and_style(raw, _STYLE_IDS["string_doc_sq"], 
                        _STATE_ML_SQUOTE, _STATE_ML_SQUOTE)
                    continue

                style_id = _STYLE_IDS["default"]

                if match.group("comment"):
                    if _COMMENT_TODO_RE.search(raw):
                        style_id = _STYLE_IDS["comment_doc"] 
                    else: style_id = _STYLE_IDS["comment"]
                elif match.group("fstring"):
                    style_id = _STYLE_IDS["string_fstring"]
                elif match.group("string"):
                    style_id = _STYLE_IDS["string"]
                elif match.group("decorator"):
                    style_id = _STYLE_IDS["decorator"]
                elif match.group("number_float"):
                    style_id = _STYLE_IDS["number_float"]
                elif match.group("number"):
                    style_id = _STYLE_IDS["number"]
                elif match.group("operator"):
                    style_id = _STYLE_IDS["operator"]
                    if raw == "->": expect_annotation = True
                
                elif match.group("punctuation"):
                    style_id = _STYLE_IDS["punctuation"]
                    if raw == ":":
                        expect_annotation = True
                    elif raw == "(":
                        expect_annotation = False
                        if last_keyword == "def_named":
                            in_def_params = True
                        if in_def_params:
                            param_depth += 1
                    elif raw == ")":
                        expect_annotation = False
                        if in_def_params:
                            param_depth -= 1
                            if param_depth <= 0:
                                in_def_params = False
                                param_depth = 0
                                last_keyword = None

                elif match.group("word"):
                    word = match.group("word")

                    if word in ("self", "cls"):
                        style_id = _STYLE_IDS["self"]
                    elif word in self._keyword_map:
                        style_id = _STYLE_IDS.get(self._keyword_map[word], _STYLE_IDS["keyword"])
                        if word in ("def", "class"):
                            last_keyword = word
                    elif word in self._builtin_types:
                        style_id = _STYLE_IDS["builtin_type"]
                    elif word in self._builtins or word in self._exceptions:
                        style_id = _STYLE_IDS["builtin"]
                    elif _CAPITAL_WORD_RE.fullmatch(word) or _DUNDER_RE.fullmatch(word):
                        style_id = _STYLE_IDS["constant"]
                    elif expect_annotation:
                        style_id = _STYLE_IDS["annotation"]
                        expect_annotation = False
                    else:
                        # Contextual Highlighting Rules Apply Here
                        if last_keyword == "class":
                            style_id = _STYLE_IDS["class"]
                            last_keyword = "class_named"
                        elif last_keyword == "def":
                            style_id = _STYLE_IDS["function"]
                            last_keyword = "def_named"
                        elif in_def_params:
                            style_id = _STYLE_IDS["parameter"]
                        else:
                            # Rule 1: Everything else remains uncolored (default)
                            style_id = _STYLE_IDS["default"]

                current_state = advance_and_style(raw, style_id, _STATE_NORMAL, _STATE_NORMAL)

        editor.SendScintilla(editor.SCI_SETLINESTATE, current_line, current_state)

        # Set fold levels for all processed lines
        indent_unit = 4
        line_count = editor.SendScintilla(editor.SCI_GETLINECOUNT)
        for line_num in range(line_start, min(current_line + 1, line_count)):
            raw_line = editor.text(line_num)
            indent = len(raw_line) - len(raw_line.lstrip())
            indent_level = indent // indent_unit

            stripped = raw_line.strip()
            is_header = False
            if stripped and not stripped.startswith(("#", '"""', "'''")):
                is_header = any(
                    stripped.startswith(kw)
                    for kw in ("def ", "class ", "if ", "elif ", "else:", "for ",
                        "while ", "try:", "except ", "finally:", "with ", "async def ",
                        "async for ", "async with ", "@"))

            level = indent_level + 0x400
            if is_header:
                level |= 0x2000

            editor.SendScintilla(editor.SCI_SETFOLDLEVEL, line_num, level)

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