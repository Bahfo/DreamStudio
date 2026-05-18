from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QFont, QFontInfo, QColor

from editor.texteditor.ironica_lexer.json_lexer import CustomJSONLexer


class EditConfigurationsTab(QsciScintilla):
    """JSON User Configurations file: Imported from IDE directory into the editor."""

    def __init__(self, _parent=None, language=None):
        super().__init__(_parent)

        try:
            self.setUtf8(True)
        except Exception:
            pass

        self.font_size = 11
        self._font = QFont("JetBrains Mono", self.font_size)
        if not QFontInfo(self._font).exactMatch():
            self._font = QFont("Consolas", self.font_size)
        self.setFont(self._font)

        self.setAutoIndent(True)
        self.setBackspaceUnindents(True)
        self.setTabIndents(True)
        self.setIndentationWidth(4)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setIndentationGuides(True)

        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginLineNumbers(0, True)
        self.setMarginWidth(0, "4444")

        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 14)
        self.setMarginSensitivity(1, True)
        self.setFolding(QsciScintilla.FoldStyle.PlainFoldStyle)

        self.setCaretLineVisible(True)
        self.setCaretWidth(2)
        self.setBraceMatching(QsciScintilla.BraceMatch.StrictBraceMatch)

        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #1E1E1E;
            }
            QTabBar {
                border: none;
                qproperty-drawBase: 0; 
            }
            QTabBar::tab {
                color: #AFB1B3; 
                background: #2D2D2D;
                padding: 6px 12px;
            }
            QTabBar::tab:selected {
                color: white; 
                background: #1E1E1E;
            }
            QTabBar::close-button {
                image: url(assets/system/close.png);
                background-color: transparent;
            }
            QTabBar::close-button:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
            }
        """)

        self.apply_theme()

    def run_text(self):
        self.setText('{\n    "configurations": true\n}')

    def apply_theme(self):
        self._lexer = CustomJSONLexer(self)
        self.setLexer(self._lexer)

        self.setPaper(QColor("#1E1E1E"))
        self.setColor(QColor("#D4D4D4"))

        self.setCaretForegroundColor(QColor("#FFFFFF"))
        self.setCaretLineBackgroundColor(QColor("#282828"))
        self.setSelectionBackgroundColor(QColor("#264F78"))
        self.setSelectionForegroundColor(QColor("#FFFFFF"))

        margin_bg = QColor("#1E1E1E")
        self.setMarginsBackgroundColor(margin_bg)
        self.setMarginsForegroundColor(QColor("#858585"))
        self.setFoldMarginColors(margin_bg, margin_bg)
