from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt


class MiniMap(QsciScintilla):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._lexer = None

        ####################################
        # Minimap Options
        ####################################
        self.font_size = 1
        self._font = QFont("JetBrains Mono", self.font_size)
        self.setFont(self._font)
        self.setUtf8(True)
        self.setReadOnly(True)
        self.setPaper(QColor("#1E1E1E"))

        self.setCaretWidth(0)
        self.setCaretLineVisible(False)
        self.setFolding(QsciScintilla.FoldStyle.NoFoldStyle)
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setMarginWidth(0, 0)
        self.setMarginWidth(1, 0)
        self.setMarginWidth(2, 0)

        self.setIndentationGuides(False)
        self.setAutoIndent(False)
        self.setBackspaceUnindents(False)
        self.setTabIndents(False)
        self.setIndentationsUseTabs(False)

        self.setObjectName("MiniMap")

        self.setStyleSheet(
            """
            QWidget#MiniMap {
                background-color: #1E1E1E;
                border: 1px solid #2A2A2A;
            }
            """
        )

        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeNone)

    def retheme(self, t) -> None:
        self.setPaper(QColor(t.color("editor.background")))
        self.setColor(QColor(t.color("editor.text")))
        self.setStyleSheet(
            f"""
            QWidget#MiniMap {{
                background-color: {t.color("minimap.background")};
                border: 1px solid {t.color("minimap.border")};
            }}
            """
        )

    def set_editor_text(self, text: str):
        self.setText(text)
