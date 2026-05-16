import re
from PyQt6.QtGui import QColor, QFont, QFontInfo
from PyQt6.Qsci import QsciLexerCustom


class CustomJSONLexer(QsciLexerCustom):
    """A high-performance byte-accurate JSON lexer matching VS Code Dark+ styling."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_styles()

    def setup_styles(self):
        self.bg_color = QColor("#1E1E1E")
        self.default_fg = QColor("#D4D4D4")

        self.setDefaultPaper(self.bg_color)
        self.setDefaultColor(self.default_fg)

        for style_id in range(128):
            self.setPaper(self.bg_color, style_id)
            self.setColor(self.default_fg, style_id)

        self.styles = {
            0: self.default_fg,  # Default / Whitespace
            1: QColor("#CE9178"),  # String Values (Terracotta)
            2: QColor("#B5CEA8"),  # Numbers (Light Green)
            3: QColor("#569CD6"),  # Keywords / Booleans (Bright Blue)
            4: self.default_fg,  # Punctuation / Brackets
            5: QColor("#9CDCFE"),  # JSON Keys (Light Sky Blue)
        }

        for style_id, color in self.styles.items():
            self.setColor(color, style_id)

        font = QFont("JetBrains Mono", 11)
        if not QFontInfo(font).exactMatch():
            font = QFont("Consolas", 11)

        for style_id in range(128):
            self.setFont(font, style_id)

    def language(self):
        return "JSON"

    def description(self, style):
        descriptions = {
            0: "Default",
            1: "String Value",
            2: "Number",
            3: "Keyword",
            4: "Punctuation",
            5: "JSON Key",
        }
        return descriptions.get(style, "Unknown")

    def styleText(self, start, end):
        editor = self.parent()
        if not editor:
            return

        self.startStyling(start)
        raw_bytes = editor.text().encode("utf-8")
        buffer = raw_bytes[start:end]

        pos = 0
        buf_len = len(buffer)

        while pos < buf_len:
            # Whitespace
            ws_match = re.compile(rb"\s+").match(buffer, pos)
            if ws_match:
                self.setStyling(len(ws_match.group(0)), 0)
                pos = ws_match.end()
                continue

            # JSON Key Lookahead
            key_match = re.compile(rb'"[^"\\]*(?:\\.[^"\\]*)*"\s*(?=:)').match(
                buffer, pos
            )
            if key_match:
                full_match = key_match.group(0)
                str_part = (
                    re.compile(rb'"[^"\\]*(?:\\.[^"\\]*)*"').match(full_match).group(0)
                )
                self.setStyling(len(str_part), 5)
                if len(full_match) > len(str_part):
                    self.setStyling(len(full_match) - len(str_part), 0)
                pos = key_match.end()
                continue

            # Standard String Value
            str_match = re.compile(rb'"[^"\\]*(?:\\.[^"\\]*)*"').match(buffer, pos)
            if str_match:
                self.setStyling(len(str_match.group(0)), 1)
                pos = str_match.end()
                continue

            # Numbers
            num_match = re.compile(rb"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?").match(
                buffer, pos
            )
            if num_match:
                self.setStyling(len(num_match.group(0)), 2)
                pos = num_match.end()
                continue

            # Keywords
            kw_match = re.compile(rb"\b(?:true|false|null)\b").match(buffer, pos)
            if kw_match:
                self.setStyling(len(kw_match.group(0)), 3)
                pos = kw_match.end()
                continue

            # Structural Punctuation
            punc_match = re.compile(rb"[\{\}\[\]\:,]").match(buffer, pos)
            if punc_match:
                self.setStyling(len(punc_match.group(0)), 4)
                pos = punc_match.end()
                continue

            self.setStyling(1, 0)
            pos += 1
