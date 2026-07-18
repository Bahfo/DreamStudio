from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget
from PyQt6.Qsci import QsciScintilla

from editor.texteditor.code_editor import CodeEditor


class MiniMapEditor(QsciScintilla):
    """Read-only minimap companion for a code editor.

    Mirrors the source editor's text and visible region so the minimap
    behaves like the VS Code / Visual Studio minimap.
    """

    def __init__(self, source: CodeEditor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._source = source
        self._syncing = False

        self.setObjectName("MiniMapEditor")
        self.setReadOnly(True)
        try:
            self.setUtf8(True)
        except Exception:
            pass

        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        self.setBraceMatching(QsciScintilla.BraceMatch.NoBraceMatch)
        self.setCaretLineVisible(False)
        self.setCaretWidth(0)
        self.setFolding(QsciScintilla.FoldStyle.NoFoldStyle)
        self.setMarginWidth(0, 0)
        self.setMarginWidth(1, 0)
        self.setMarginLineNumbers(0, False)
        self.setMarginLineNumbers(1, False)
        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeNone)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTabWidth(4)
        self.setIndentationWidth(4)
        self.setIndentationsUseTabs(False)
        self.setAutoIndent(False)
        self.setEolVisibility(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.SendScintilla(QsciScintilla.SCI_SETUNDOCOLLECTION, 0)

        try:
            self.setWhitespaceVisibility(QsciScintilla.WhiteSpaceVisibility.WsInvisible)
        except Exception:
            pass

        font = QFont("JetBrains Mono")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(3)
        self.setFont(font)
        self.setMarginsFont(font)

        self._apply_theme()

        self._sync_timer = QTimer(self)
        self._sync_timer.setSingleShot(True)
        self._sync_timer.timeout.connect(self._sync_from_source)

        self._source.textChanged.connect(self.schedule_sync)
        self._source.cursorPositionChanged.connect(self._sync_scroll_from_source)

        source_scrollbar = self._source.verticalScrollBar()
        if source_scrollbar is not None:
            source_scrollbar.valueChanged.connect(self._sync_scroll_from_source)

        self.verticalScrollBar().valueChanged.connect(self._sync_source_scroll)

        self.schedule_sync()

    def _apply_theme(self) -> None:
        pal = self.palette()
        bg = pal.color(QPalette.ColorRole.Window)
        text = pal.color(QPalette.ColorRole.WindowText)

        if bg.lightness() < 128:
            paper = bg.darker(120)
            border = bg.lighter(140)
        else:
            paper = bg.darker(104)
            border = bg.darker(130)

        self.setPaper(paper)
        self.setColor(text)
        self.setMarginsBackgroundColor(paper)
        self.setMarginsForegroundColor(text)
        self.setFoldMarginColors(paper, paper)
        self.setCaretForegroundColor(text)
        self.setCaretLineBackgroundColor(paper)
        self.setSelectionBackgroundColor(border)
        self.setSelectionForegroundColor(text)

    def schedule_sync(self) -> None:
        if self._syncing:
            return
        self._sync_timer.start(30)

    def _sync_from_source(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            source_text = self._source.text()
            if self.text() != source_text:
                self.setText(source_text)
            self._sync_scroll_from_source()
        finally:
            self._syncing = False

    def _sync_scroll_from_source(self, *_args) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            source = self._source
            if source is None or not source.text():
                return
            first_visible = source.SendScintilla(QsciScintilla.SCI_GETFIRSTVISIBLELINE)
            self.SendScintilla(QsciScintilla.SCI_SETFIRSTVISIBLELINE, first_visible)
            line, _col = source.getCursorPosition()
            line = max(0, line)
            self.setCursorPosition(line, 0)
            self.ensureLineVisible(line)
        finally:
            self._syncing = False

    def _sync_source_scroll(self, *_args) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            source = self._source
            if source is None:
                return
            first_visible = self.SendScintilla(QsciScintilla.SCI_GETFIRSTVISIBLELINE)
            source.SendScintilla(QsciScintilla.SCI_SETFIRSTVISIBLELINE, first_visible)
            line, _col = self.getCursorPosition()
            line = max(0, line)
            source.setCursorPosition(line, 0)
            source.ensureLineVisible(line)
        finally:
            self._syncing = False

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_scroll_from_source()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    def wheelEvent(self, event: QWheelEvent) -> None:
        self._source.wheelEvent(event)


class MiniMapHostWidget(QWidget):
    """Wraps a CodeEditor and a MiniMapEditor side by side.

    Delegates all attribute access to the underlying editor so the host
    widget can be used as a drop-in replacement wherever CodeEditor is
    expected.
    """

    position_changed = pyqtSignal(int, int)
    dirty_state_changed = pyqtSignal(bool)

    def __init__(
        self,
        editor: CodeEditor,
        parent: Optional[QWidget] = None,
        minimap_width: int = 100,
    ):
        super().__init__(parent)
        self.setObjectName("MiniMapHostWidget")

        self._editor = editor
        self._minimap = MiniMapEditor(editor, self)
        self._minimap_width = minimap_width
        self._minimap_visible = True

        if self._editor.parent() is not self:
            self._editor.setParent(self)

        self._editor.position_changed.connect(self.position_changed.emit)
        self._editor.dirty_state_changed.connect(self.dirty_state_changed.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._editor, 1)
        layout.addWidget(self._minimap, 0)

        self._minimap.setFixedWidth(self._minimap_width)
        self._minimap.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )

    @property
    def editor(self) -> CodeEditor:
        return self._editor

    @property
    def minimap(self) -> MiniMapEditor:
        return self._minimap

    def set_minimap_visible(self, visible: bool) -> None:
        self._minimap_visible = visible
        self._minimap.setVisible(visible)
        self._minimap.setFixedWidth(self._minimap_width if visible else 0)
        if visible:
            self._minimap.schedule_sync()
            self._minimap._sync_scroll_from_source()

    def __getattr__(self, name: str):
        return getattr(self._editor, name)


def attach_minimap(editor: CodeEditor, parent: Optional[QWidget] = None, minimap_width: int = 100) -> MiniMapHostWidget:
    return MiniMapHostWidget(editor, parent=parent, minimap_width=minimap_width)


def ensure_minimap(editor_or_host):
    """Return the MiniMapHostWidget for *editor_or_host*.

    If *editor_or_host* is already a ``MiniMapHostWidget`` it is returned
    as-is.  If it is a bare ``CodeEditor`` it is wrapped in a new host.
    """
    if isinstance(editor_or_host, MiniMapHostWidget):
        return editor_or_host
    return attach_minimap(editor_or_host)
