import re
from PyQt6.Qsci import QsciLexerCustom
from PyQt6.QtGui import QColor, QFont


class CustomPythonLexer(QsciLexerCustom):
    def __init__(self, parent, json_data):
        super().__init__(parent)
        self.json_data = json_data

        self.default_font = QFont("JetBrains Mono", 11)
        self.setDefaultFont(self.default_font)
        self.setDefaultPaper(QColor("#1E1E1E"))
        self.setDefaultColor(QColor("#D4D4D4"))

        self.STYLE_DEFAULT = 0
        self.STYLE_STRING = 1
        self.STYLE_COMMENT = 2
        self.STYLE_NUMBER = 3

        self.setColor(QColor("#D4D4D4"), self.STYLE_DEFAULT)
        self.setColor(QColor("#CE9178"), self.STYLE_STRING)
        self.setColor(QColor("#6A9955"), self.STYLE_COMMENT)
        self.setColor(QColor("#B5CEA8"), self.STYLE_NUMBER)

        for i in range(4):
            self.setPaper(QColor("#1E1E1E"), i)
            self.setFont(self.default_font, i)

        self.word_to_style = {}
        colors_schema = self.json_data.get("colors_schema", {})

        current_style_id = 4
        category_to_style_id = {}

        for category, hex_color in colors_schema.items():
            self.setColor(QColor(hex_color), current_style_id)
            self.setPaper(QColor("#1E1E1E"), current_style_id)
            self.setFont(self.default_font, current_style_id)
            category_to_style_id[category] = current_style_id
            current_style_id += 1

        categories = ["words", "types", "iterators", "exceptions"]
        for cat in categories:
            for word, word_category in self.json_data.get(cat, {}).items():
                if word_category in category_to_style_id:
                    self.word_to_style[word] = category_to_style_id[word_category]

        self.token_regex = re.compile(
            r'(?P<string>"(?:\\"|[^"])*"|\'(?:\\\'|[^\'])*\')|'
            r"(?P<comment>#.*)|"
            r"(?P<number>\b\d+\.?\d*\b)|"
            r"(?P<word>\b\w+\b)|"
            r"(?P<ws>\s+)|"
            r"(?P<other>.)"
        )

    def language(self):
        return "CustomPython"

    def description(self, style):
        return f"Style_{style}"

    def apply_syntax_theme(self, t) -> None:
        self.setDefaultColor(QColor(t.color("editor.text")))
        self.setDefaultPaper(QColor(t.color("editor.background")))
        self.setColor(QColor(t.color("syntax.string")), self.STYLE_STRING)
        self.setColor(QColor(t.color("syntax.comment")), self.STYLE_COMMENT)
        self.setColor(QColor(t.color("syntax.number")), self.STYLE_NUMBER)
        for i in range(128):
            self.setPaper(QColor(t.color("editor.background")), i)
        colors_schema = self.json_data.get("colors_schema", {})
        category_map = {
            "definition": "syntax.definition",
            "import": "syntax.import",
            "keyword": "syntax.keyword",
            "execution_logic": "syntax.execution_logic",
            "logic": "syntax.logic",
            "constructor": "syntax.type",
            "collection": "syntax.collection",
            "meta": "syntax.meta",
            "iterator": "syntax.iterator",
            "exception_class": "syntax.exception",
            "warning_class": "syntax.warning",
        }
        current_style_id = 4
        for category in colors_schema:
            theme_key = category_map.get(category, "syntax.keyword")
            self.setColor(QColor(t.color(theme_key)), current_style_id)
            current_style_id += 1

    def styleText(self, start, end):
        editor = self.editor()
        if not editor:
            return

        editor.SendScintilla(editor.SCI_STARTSTYLING, start)
        text = editor.text()[start:end]

        for match in self.token_regex.finditer(text):
            token_text = match.group(0)
            length = len(token_text.encode("utf-8"))
            style_id = self.STYLE_DEFAULT

            if match.group("string"):
                style_id = self.STYLE_STRING
            elif match.group("comment"):
                style_id = self.STYLE_COMMENT
            elif match.group("number"):
                style_id = self.STYLE_NUMBER
            elif match.group("word"):
                word = match.group("word")
                style_id = self.word_to_style.get(word, self.STYLE_DEFAULT)

            editor.SendScintilla(editor.SCI_SETSTYLING, length, style_id)
