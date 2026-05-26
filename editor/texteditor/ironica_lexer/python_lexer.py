import re
from PyQt6.Qsci import QsciLexerCustom
from PyQt6.QtGui import QColor, QFont

(STYLE_DEFAULT, STYLE_STRING, STYLE_COMMENT, STYLE_NUMBER,
 STYLE_DEFINITION, STYLE_IMPORT, STYLE_KEYWORD, STYLE_EXECUTION_LOGIC,
 STYLE_LOGIC, STYLE_CONSTRUCTOR, STYLE_COLLECTION, STYLE_META,
 STYLE_ITERATOR, STYLE_EXCEPTION_CLASS, STYLE_WARNING_CLASS) = range(15)

_STYLE_NAMES = {
    "definition": STYLE_DEFINITION,
    "import": STYLE_IMPORT,
    "keyword": STYLE_KEYWORD,
    "execution_logic": STYLE_EXECUTION_LOGIC,
    "logic": STYLE_LOGIC,
    "constructor": STYLE_CONSTRUCTOR,
    "collection": STYLE_COLLECTION,
    "meta": STYLE_META,
    "iterator": STYLE_ITERATOR,
    "exception_class": STYLE_EXCEPTION_CLASS,
    "warning_class": STYLE_WARNING_CLASS,
}

_STATE_NORMAL = 0
_STATE_ML_DQUOTE = 1
_STATE_ML_SQUOTE = 2

_TRIPLE_DOUBLE = '"""'
_TRIPLE_SINGLE = "'''"

_STR_PREFIX = r"(?:[rR](?:[bBfF])?|[bB][rR]?|[fF][rR]?|[uU])"

_TOKEN_RE = re.compile(
    # Triple-quoted strings with optional prefix
    r'(?P<string3>'
    + _STR_PREFIX + r'?"""(?:[^"\\]|\\.|"(?!""))*"""|'
    + _STR_PREFIX + r"?" + r"'''(?:[^'\\]|\\.|'(?!''))*''')|"
    # Single-line strings with prefix support
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
    r"(?P<number_int>"
    r"\b0[xX][\da-fA-F](_?[\da-fA-F])*\b|"
    r"\b0[bB][01](_?[01])*\b|"
    r"\b0[oO][0-7](_?[0-7])*\b|"
    r"\b\d(_?\d)*[jJ]?\b"
    r")|"
    r"(?P<word>\b[^\W\d]\w*\b)|"
    r"(?P<ws>\s+)|"
    r"(?P<other>.)"
)


class CustomPythonLexer(QsciLexerCustom):
    def __init__(self, parent, json_data):
        super().__init__(parent)
        self.json_data = json_data

        self.default_font = QFont("JetBrains Mono", 11)
        self.setDefaultFont(self.default_font)
        self.setDefaultPaper(QColor("#1E1E1E"))
        self.setDefaultColor(QColor("#D4D4D4"))

        self.setColor(QColor("#D4D4D4"), STYLE_DEFAULT)
        self.setColor(QColor("#CE9178"), STYLE_STRING)
        self.setColor(QColor("#6A9955"), STYLE_COMMENT)
        self.setColor(QColor("#B5CEA8"), STYLE_NUMBER)

        for i in range(STYLE_WARNING_CLASS + 1):
            self.setPaper(QColor("#1E1E1E"), i)
            self.setFont(self.default_font, i)

        colors_schema = self.json_data.get("colors_schema", {})
        for category, hex_color in colors_schema.items():
            sid = _STYLE_NAMES.get(category)
            if sid is not None:
                self.setColor(QColor(hex_color), sid)
                self.setPaper(QColor("#1E1E1E"), sid)
                self.setFont(self.default_font, sid)

        self._lexer_state = _STATE_NORMAL
        self.word_to_style = {}
        categories = ["words", "types", "iterators", "exceptions"]
        for cat in categories:
            for word, word_category in self.json_data.get(cat, {}).items():
                sid = _STYLE_NAMES.get(word_category)
                if sid is not None:
                    self.word_to_style[word] = sid

    def language(self):
        return "CustomPython"

    def description(self, style):
        for name, sid in _STYLE_NAMES.items():
            if sid == style:
                return f"Python_{name}"
        if style == STYLE_DEFAULT:
            return "Python_default"
        if style == STYLE_STRING:
            return "Python_string"
        if style == STYLE_COMMENT:
            return "Python_comment"
        if style == STYLE_NUMBER:
            return "Python_number"
        return f"Style_{style}"

    def apply_syntax_theme(self, t) -> None:
        bg = t.color("editor.background", "#1E1E1E")
        fg = t.color("editor.text", "#D4D4D4")
        self.setDefaultColor(QColor(fg))
        self.setDefaultPaper(QColor(bg))
        self.setColor(QColor(fg), STYLE_DEFAULT)
        self.setColor(QColor(t.color("syntax.string", "#CE9178")), STYLE_STRING)
        self.setColor(QColor(t.color("syntax.comment", "#6A9955")), STYLE_COMMENT)
        self.setColor(QColor(t.color("syntax.number", "#B5CEA8")), STYLE_NUMBER)
        for i in range(STYLE_WARNING_CLASS + 1):
            self.setPaper(QColor(bg), i)
        category_map = {
            STYLE_DEFINITION: "syntax.definition",
            STYLE_IMPORT: "syntax.import",
            STYLE_KEYWORD: "syntax.keyword",
            STYLE_EXECUTION_LOGIC: "syntax.execution_logic",
            STYLE_LOGIC: "syntax.logic",
            STYLE_CONSTRUCTOR: "syntax.type",
            STYLE_COLLECTION: "syntax.collection",
            STYLE_META: "syntax.meta",
            STYLE_ITERATOR: "syntax.iterator",
            STYLE_EXCEPTION_CLASS: "syntax.exception",
            STYLE_WARNING_CLASS: "syntax.warning",
        }
        for sid, theme_key in category_map.items():
            self.setColor(QColor(t.color(theme_key, fg)), sid)

    def apply_font(self, font: QFont) -> None:
        self.default_font = QFont(font)
        self.setDefaultFont(self.default_font)
        for i in range(STYLE_WARNING_CLASS + 1):
            self.setFont(self.default_font, i)

    def styleText(self, start, end):
        editor = self.editor()
        if not editor:
            return

        full_bytes = editor.text().encode("utf-8")
        text = full_bytes[start:end].decode("utf-8", errors="replace")

        init_state = self._lexer_state
        in_multiline = init_state in (_STATE_ML_DQUOTE, _STATE_ML_SQUOTE)
        was_multiline = in_multiline
        quote_char = ""
        quote_run = 0
        if init_state == _STATE_ML_DQUOTE:
            quote_char = '"'
        elif init_state == _STATE_ML_SQUOTE:
            quote_char = "'"

        editor.SendScintilla(editor.SCI_STARTSTYLING, start)

        for match in _TOKEN_RE.finditer(text):
            token_text = match.group(0)
            length = len(token_text.encode("utf-8"))
            style_id = STYLE_DEFAULT

            if in_multiline:
                if match.group("string3"):
                    in_multiline = False
                    quote_run = 0
                    style_id = STYLE_STRING
                else:
                    for ch in token_text:
                        if ch == quote_char:
                            quote_run += 1
                        else:
                            quote_run = 0
                        if quote_run >= 3:
                            in_multiline = False
                            quote_run = 0
                            break
                    style_id = STYLE_STRING
            elif match.group("string3"):
                style_id = STYLE_STRING
            elif match.group("string"):
                style_id = STYLE_STRING
            elif match.group("comment"):
                style_id = STYLE_COMMENT
            elif match.group("number_float") or match.group("number_int"):
                style_id = STYLE_NUMBER
            elif match.group("word"):
                word = match.group("word")
                style_id = self.word_to_style.get(word, STYLE_DEFAULT)

            editor.SendScintilla(editor.SCI_SETSTYLING, length, style_id)

        if not in_multiline and not was_multiline:
            # Strip comments before scanning for unclosed triple quotes
            # to avoid false positives from # """ inside comments
            clean_lines = []
            for line in text.split('\n'):
                comment_pos = line.find('#')
                if comment_pos >= 0:
                    clean_lines.append(line[:comment_pos])
                else:
                    clean_lines.append(line)
            clean_text = '\n'.join(clean_lines)

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
