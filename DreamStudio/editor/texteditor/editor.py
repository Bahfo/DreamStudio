from PyQt6.Qsci import (
    QsciScintilla,
    QsciLexerCMake,
    QsciAPIs,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QKeyEvent

import json

### LOCAL IMPORTS
from editor.texteditor.ironica_lexer.python_lexer import CustomPythonLexer
from editor.texteditor.ironica_lexer.cpp_lexer import CustomCppLexer


CONFIG_CODE_EDITOR = {
    "Set TextEditor Font": ("JetBrains Mono", 10),
    "Encoding": "UTF-8",
    "Identation_Spacing": 4,
    "Auto Ident": True,
    "Backspace Unidents": True,
    "Tab Idents": True,
    "Identation Width": 4,
    "Numbering Foreground Colors": "#1E1E1E",
}


class CodeEditor(QsciScintilla):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._lexer = None

        ####################################
        # Texteditor Options
        ####################################
        self.font_size = 11
        self._font = QFont("JetBrains Mono", self.font_size)
        self.setFont(self._font)
        self.setUtf8(True)

        self._indentation_spacing = 4
        self._vertical_spacing = 1
        self.setAutoIndent(True)
        self.setBackspaceUnindents(True)
        self.setTabIndents(True)
        self.setIndentationWidth(self._indentation_spacing)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setIndentationGuides(True)

        self.fold_bg = QColor("#1C1C1C")
        self.fold_color = QColor("#A0A0A0")

        self.setObjectName("CodeEditor")

        self.setStyleSheet(
            """
        QWidget#CodeEditor {
            background-color: #1E1E1E;
            border: 1px solid #2A2A2A;
        }

        QScrollBar:vertical {
            background: #1E1E1E;
            width: 12px;
            margin: 0px;
        }

        QScrollBar::handle:vertical {
            background: #3A3A3A;
            min-height: 20px;
            border-radius: 4px;
        }

        QScrollBar::handle:vertical:hover {
            background: #4A4A4A;
        }
        """
        )

        ##### EDGES FOR TEXTEDITOR

        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
        self.setEdgeColumn(80)
        self.setEdgeColor(QColor("#444444"))
        self.zoomIn(0)

        ####################################
        # Main Implementation
        ####################################
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)

        self.setMarginWidth(0, "000000")
        self.setMarginLineNumbers(0, True)
        self.setMarginsBackgroundColor(self.fold_bg)
        self.setMarginsForegroundColor(QColor("#5F5F5F"))
        self.setFoldMarginColors(self.fold_bg, self.fold_bg)

        # Caret
        self.setCaretForegroundColor(QColor("white"))
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#323232"))
        self.setCaretWidth(2)
        self.setCaretLineVisible(True)

        # Brace Matching
        self.setBraceMatching(QsciScintilla.BraceMatch.StrictBraceMatch)

        # Code Folding
        self.setFolding(QsciScintilla.FoldStyle.PlainFoldStyle)
        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 12)
        self.setMarginSensitivity(1, True)
        self.setMarkerForegroundColor(
            QColor("#B0B0B0"), QsciScintilla.SC_MARKNUM_FOLDER
        )
        self.setMarkerForegroundColor(
            QColor("#B0B0B0"), QsciScintilla.SC_MARKNUM_FOLDEROPEN
        )
        self.setMarkerForegroundColor(
            self.fold_color, QsciScintilla.SC_MARKNUM_FOLDEROPEN
        )

        self.markerDefine(
            QsciScintilla.MarkerSymbol.Plus, QsciScintilla.SC_MARKNUM_FOLDER
        )
        self.markerDefine(
            QsciScintilla.MarkerSymbol.Minus, QsciScintilla.SC_MARKNUM_FOLDEROPEN
        )

        self.set_wrap_mode()

        # TODO: ADDING SUPPORT ONCE THE FILE IS OPENED IMMEDIATELY
        self.setLanguage("Python")

        ### Enable AutoCompletion:
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        self.setAutoCompletionThreshold(1)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(True)

    def set_editor_font(self, font):
        self._font = QFont(font, 10)
        self.setFont(self._font)

    def set_editor_font_size(self, font_size):
        self.font_size = font_size
        if self._lexer:
            self._lexer.setFont(self._font)

    def set_wrap_mode(self, enabled=True):
        if enabled:
            self.setWrapMode(QsciScintilla.WrapMode.WrapWord)
        else:
            self.setWrapMode(QsciScintilla.WrapMode.WrapNone)

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key.Key_Return or e.key() == Qt.Key.Key_Enter:
            line, index = self.getCursorPosition()
            current_line_text = self.text(line)

            stripped = current_line_text.rstrip()

            base_indent = ""
            for char in current_line_text:
                if char == " ":
                    base_indent += " "
                elif char == "\t":
                    base_indent += "\t"
                else:
                    break

            if (
                stripped.endswith(":")
                or stripped.endswith("{")
                or stripped.endswith("(")
            ):
                indent = base_indent + (" " * self._indentation_spacing)
            else:
                indent = base_indent

            self.beginUndoAction()
            self.insert("\n" + indent)
            self.endUndoAction()

            self.setCursorPosition(line + 1, len(indent))
        else:
            super().keyPressEvent(e)

    def setLanguage(self, lang: str):
        if lang == "Python":
            self._lexer = self.load_language_keywords("Python")
            if self._lexer:
                self._lexer.setDefaultFont(self._font)
                self.setLexer(self._lexer)
                self.apply_theme()

        elif lang == "CPP":
            self._lexer = self.load_language_keywords("CPP")
            if self._lexer:
                self._lexer.setDefaultFont(self._font)
                self.setLexer(self._lexer)
                self.apply_theme()

        elif lang == "CMAKE":
            self._lexer = QsciLexerCMake()
            self._lexer.setDefaultFont(self._font)
            self.setLexer(self._lexer)
            self.apply_theme()

        else:
            self._lexer = None
            self.setLexer(None)
            return

    def apply_theme(self):
        if not self._lexer:
            return

        self.setPaper(QColor("#1E1E1E"))
        self.setColor(QColor("#D4D4D4"))

        for style in range(128):
            self._lexer.setPaper(QColor("#1E1E1E"), style)

        self._lexer.setDefaultColor(QColor("#D4D4D4"))
        self.setSelectionBackgroundColor(QColor("#264F78"))
        self.setSelectionForegroundColor(QColor("#FFFFFF"))

    def load_language_keywords(self, lang: str):
        if lang == "Python":
            path = "editor/texteditor/keywords/python.json"
            lexer_class = CustomPythonLexer

        elif lang == "CPP":
            path = "editor/texteditor/keywords/cpp.json"
            lexer_class = CustomCppLexer

        else:
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.words = data.get("words", {})
        self.types = data.get("types", {})
        self.iters = data.get("iterators", {})
        self.exceptions = data.get("exceptions", {})
        self.colors = data.get("colors_schema", {})

        classification_map = {}

        for word, category in self.words.items():
            classification_map[word] = category
        for word, category in self.types.items():
            classification_map[word] = category
        for word, category in self.iters.items():
            classification_map[word] = category
        for word, category in self.exceptions.items():
            classification_map[word] = category

        self.classification_map = classification_map

        lexer = lexer_class(self, data)

        self.api = QsciAPIs(lexer)
        for word in classification_map.keys():
            self.api.add(word)
        self.api.prepare()

        return lexer
