from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QFont, QFontInfo, QColor

from editor.texteditor.ironica_lexer.json_lexer import CustomJSONLexer


class EditConfigurationsTab(QsciScintilla):
    """JSON User Configurations file: Imported from IDE directory into the editor."""

    def __init__(self, _parent=None, language=None, theme_manager=None):
        super().__init__(_parent)
        self._theme_manager = theme_manager

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

        self.apply_theme()

    def run_text(self):
        self.setText('{\n    "configurations": true\n}')

    def apply_theme(self, t=None):
        if t is not None:
            self._theme_manager = t
        t = self._theme_manager

        if t is not None:
            bg = t.color("editor.background")
            fg = t.color("editor.text")
            sel_bg = t.color("editor.selection_bg")
            sel_fg = t.color("editor.selection_fg")
            caret = t.color("editor.caret")
            margin_bg = t.color("editor.margin_bg")
            margin_fg = t.color("editor.margin_fg")
            tab_bg = t.color("tab.inactive_bg")
            tab_sel_bg = t.color("tab.selected_bg")
            tab_fg = t.color("tab.text_inactive")
            tab_sel_fg = t.color("tab.text_selected")
            caret_line = t.color("widget.border")
        else:
            bg = "#1E1E1E"
            fg = "#D4D4D4"
            sel_bg = "#264F78"
            sel_fg = "#FFFFFF"
            caret = "#FFFFFF"
            margin_bg = "#1E1E1E"
            margin_fg = "#858585"
            tab_bg = "#2D2D2D"
            tab_sel_bg = "#1E1E1E"
            tab_fg = "#AFB1B3"
            tab_sel_fg = "white"
            caret_line = "#282828"

        self._lexer = CustomJSONLexer(self)
        self.setLexer(self._lexer)

        self.setPaper(QColor(bg))
        self.setColor(QColor(fg))

        self.setCaretForegroundColor(QColor(caret))
        self.setCaretLineBackgroundColor(QColor(caret_line))
        self.setSelectionBackgroundColor(QColor(sel_bg))
        self.setSelectionForegroundColor(QColor(sel_fg))

        margin_bg_q = QColor(margin_bg)
        self.setMarginsBackgroundColor(margin_bg_q)
        self.setMarginsForegroundColor(QColor(margin_fg))
        self.setFoldMarginColors(margin_bg_q, margin_bg_q)

        self.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {bg};
            }}
            QTabBar {{
                border: none;
                qproperty-drawBase: 0;
            }}
            QTabBar::tab {{
                color: {tab_fg};
                background: {tab_bg};
                padding: 6px 12px;
            }}
            QTabBar::tab:selected {{
                color: {tab_sel_fg};
                background: {tab_sel_bg};
            }}
            QTabBar::close-button {{
                image: url(assets/system/close.png);
                background-color: transparent;
            }}
            QTabBar::close-button:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
            }}
        """)

        if self._lexer and t is not None:
            if hasattr(self._lexer, "apply_syntax_theme"):
                self._lexer.apply_syntax_theme(t)
