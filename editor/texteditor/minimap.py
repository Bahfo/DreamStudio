from typing import Optional, TYPE_CHECKING

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QFont, QColor, QPainter
from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtWidgets import QWidget

from editor.texteditor.ironica_lexer.python_lexer import CustomPythonLexer
from editor.texteditor.ironica_lexer.cpp_lexer import CustomCppLexer

if TYPE_CHECKING:
    from editor.texteditor.code_editor import CodeEditor


class ViewportOverlay(QWidget):
    def __init__(self, minimap: "MiniMap") -> None:
        super().__init__(minimap)
        self._minimap = minimap
        self._opacity = 28
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def paintEvent(self, event) -> None:
        rect = self._minimap._get_viewport_rect()
        if rect is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(rect, QColor(255, 255, 255, self._opacity))
        painter.setPen(QColor(255, 255, 255, self._opacity + 30))
        painter.drawRect(rect)


class MiniMap(QsciScintilla):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._editor: Optional["CodeEditor"] = None
        self._lexer = None
        self._scroll_syncing = False

        self._font = QFont("Consolas", 1)
        self.setFont(self._font)
        self.setContentsMargins(8, 10, 18, 10)
        self.setStyleSheet("border:none;")

        self.setUtf8(True)
        self.setReadOnly(True)
        self.setPaper(QColor("#1E1E1E"))
        self.setColor(QColor("#D4D4D4"))

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
        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeNone)

        self._overlay = ViewportOverlay(self)
        self._overlay.raise_()

        self._text_sync_timer = QTimer(self)
        self._text_sync_timer.setSingleShot(True)
        self._text_sync_timer.setInterval(50)
        self._text_sync_timer.timeout.connect(self._sync_text)

        self._update_timer = QTimer(self)
        self._update_timer.setInterval(30)
        self._update_timer.timeout.connect(self._update_tick)
        self._update_timer.start()

    def _clone_lexer(self, editor: "CodeEditor") -> bool:
        lexer_cls = type(editor._lexer)
        if lexer_cls in (CustomPythonLexer, CustomCppLexer):
            json_data = editor._lexer.json_data
            try:
                self._lexer = lexer_cls(self, json_data)
                if (
                    hasattr(self._lexer, "_analyzer")
                    and self._lexer._analyzer is not None
                ):
                    self._lexer._analyzer.shutdown()
                    self._lexer._analyzer = None
                self.setLexer(self._lexer)

                if hasattr(self._lexer, "apply_font"):
                    self._lexer.apply_font(self._font)

                return True
            except Exception as e:
                print(f"Minimap lexer clone failed: {e}")
        self._lexer = None
        self.setLexer(None)
        return False

    def bind_editor(self, editor: Optional["CodeEditor"]) -> None:
        if self._editor is editor:
            return
        self.unbind_editor()
        if editor is None:
            self._update_timer.stop()
            return

        self._editor = editor
        self._editor.textChanged.connect(self._on_editor_text_changed)
        self._update_timer.start()

        if editor._lexer is not None:
            self._clone_lexer(editor)
        else:
            self._lexer = None
            self.setLexer(None)

        self.setText(editor.text())

        editor_first_vis = editor.SendScintilla(QsciScintilla.SCI_GETFIRSTVISIBLELINE)
        first_doc = editor.SendScintilla(
            QsciScintilla.SCI_DOCLINEFROMVISIBLE, editor_first_vis
        )
        self.SendScintilla(QsciScintilla.SCI_SETFIRSTVISIBLELINE, first_doc)

    def unbind_editor(self) -> None:
        self._text_sync_timer.stop()
        if self._editor is not None:
            try:
                self._editor.textChanged.disconnect(self._on_editor_text_changed)
            except (TypeError, RuntimeError):
                pass
            self._editor = None
        self._lexer = None
        self.setLexer(None)

    def _on_editor_text_changed(self) -> None:
        self._text_sync_timer.start()

    def _sync_text(self) -> None:
        editor = self._editor
        if editor is not None:
            self.setText(editor.text())

    def _get_viewport_rect(self) -> Optional[QRect]:
        editor = self._editor
        if editor is None:
            return None

        w = self.width()
        h = self.height()
        if w <= 2 or h <= 2:
            return None

        mm_line_h = self.textHeight(0)
        if mm_line_h <= 0:
            return None

        total_lines = self.SendScintilla(QsciScintilla.SCI_GETLINECOUNT)
        if total_lines <= 0:
            return None

        e_first_vis = editor.SendScintilla(QsciScintilla.SCI_GETFIRSTVISIBLELINE)
        e_first_doc = editor.SendScintilla(
            QsciScintilla.SCI_DOCLINEFROMVISIBLE, e_first_vis
        )

        e_lines_on_screen = editor.SendScintilla(QsciScintilla.SCI_LINESONSCREEN)
        e_last_vis = e_first_vis + e_lines_on_screen
        e_last_doc = editor.SendScintilla(
            QsciScintilla.SCI_DOCLINEFROMVISIBLE, e_last_vis
        )
        mm_first_vis = self.SendScintilla(QsciScintilla.SCI_GETFIRSTVISIBLELINE)

        margins = self.contentsMargins()
        m_top = margins.top()
        m_left = margins.left()
        m_right = margins.right()
        m_bottom = margins.bottom()

        y_start = (e_first_doc - mm_first_vis) * mm_line_h + m_top
        y_end = (e_last_doc - mm_first_vis + 1) * mm_line_h + m_top
        if y_start >= (h - m_bottom) or y_end <= m_top:
            return None

        rect_w = w - m_left - m_right - 1
        rect_h = max(y_end - y_start, 2)
        return QRect(m_left, int(y_start), rect_w, int(rect_h))

    def _update_tick(self) -> None:
        if self._editor is None or self._scroll_syncing:
            return

        editor_first_vis = self._editor.SendScintilla(
            QsciScintilla.SCI_GETFIRSTVISIBLELINE
        )
        first_doc = self._editor.SendScintilla(
            QsciScintilla.SCI_DOCLINEFROMVISIBLE, editor_first_vis
        )

        current_first = self.SendScintilla(QsciScintilla.SCI_GETFIRSTVISIBLELINE)
        if current_first != first_doc:
            self._scroll_syncing = True
            self.SendScintilla(QsciScintilla.SCI_SETFIRSTVISIBLELINE, first_doc)
            self._scroll_syncing = False

        self._overlay.update()

    def _scroll_to_line(self, doc_line: int) -> None:
        editor = self._editor
        if editor is None:
            return

        self._scroll_syncing = True

        vis_lines = editor.SendScintilla(QsciScintilla.SCI_LINESONSCREEN)
        target_visual = editor.SendScintilla(
            QsciScintilla.SCI_VISIBLEFROMDOCLINE,
            max(0, doc_line - vis_lines // 2),
        )
        editor.SendScintilla(QsciScintilla.SCI_SETFIRSTVISIBLELINE, target_visual)
        editor.setCursorPosition(doc_line, 0)

        self._scroll_syncing = False

    def mousePressEvent(self, event) -> None:
        if self._editor is not None and event.button() == Qt.MouseButton.LeftButton:
            margins = self.contentsMargins()
            sci_pos = self.SendScintilla(
                QsciScintilla.SCI_POSITIONFROMPOINT,
                int(event.pos().x()) - margins.left(),
                int(event.pos().y()) - margins.top(),
            )
            line, _ = self.lineIndexFromPosition(sci_pos)
            if line >= 0:
                self._scroll_to_line(line)
                # WITHOUT super METHOD TO KEEP IT FROM NORMAL BEHAVIOR

    def mouseMoveEvent(self, event) -> None:
        if self._editor is not None and event.buttons() & Qt.MouseButton.LeftButton:
            margins = self.contentsMargins()
            sci_pos = self.SendScintilla(
                QsciScintilla.SCI_POSITIONFROMPOINT,
                int(event.pos().x()) - margins.left(),
                int(event.pos().y()) - margins.top(),
            )
            line, _ = self.lineIndexFromPosition(sci_pos)
            if line >= 0:
                self._scroll_to_line(line)
                # WITHOUT super METHOD TO KEEP IT FROM NORMAL BEHAVIOR

    def mouseDoubleClickEvent(self, event) -> None:
        """Kept like that to swallow all incoming events"""
        pass

    def resizeEvent(self, event) -> None:
        self._overlay.resize(self.size())
        super().resizeEvent(event)

    def retheme(self, t) -> None:
        self.setPaper(QColor(t.color("minimap.background")))
        self.setColor(QColor(t.color("editor.text")))

        if self._lexer is not None and hasattr(self._lexer, "apply_syntax_theme"):
            self._lexer.apply_syntax_theme(t)
