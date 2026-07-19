from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QSizePolicy, QWidget, QToolButton
from PyQt6.Qsci import QsciScintilla

from editor.texteditor.code_editor import CodeEditor


class MinimapOverlay(QWidget):
    """Transparent overlay that highlights the visible region of the source editor."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Ensure mouse events pass through the overlay to the minimap below
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # Match the Visual Studio 2019 semi-transparent scroll thumb look
        self.setStyleSheet("background-color: rgba(128, 128, 128, 60);")

    def update_geometry(self, y_offset: int, height: int) -> None:
        """Update the position and height of the highlight box."""
        if self.parent():
            self.setGeometry(0, y_offset, self.parent().width(), height)


class MiniMapEditor(QsciScintilla):
    """Read-only minimap companion for a code editor.

    Mirrors the source editor's text and visible region so the minimap
    behaves like the VS Code / Visual Studio minimap.
    """

    def __init__(self, source: CodeEditor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._source = source
        self._syncing = False
        self._is_dragging = False

        self.setObjectName("MiniMapEditor")
        self.setReadOnly(True)
        try:
            self.setUtf8(True)
        except Exception:
            pass

        # Word wrap is disabled to maintain strict 1:1 line correlation
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

        # Turn off scrollbars; the minimap acts as the scrollbar itself
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

        # Shrink the font to absolute minimum pixel size to fit text fully horizontally
        font = QFont("JetBrains Mono")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPixelSize(2)
        self.setFont(font)
        self.setMarginsFont(font)

        # Force Scintilla to zoom out maximally to ensure long lines fit the viewport
        self.SendScintilla(QsciScintilla.SCI_SETZOOM, -10)
        self.setScrollWidth(1)

        self._apply_theme()

        # Overlay widget to represent the visible viewport (like VS2019)
        self._overlay = MinimapOverlay(self.viewport())

        # Timer remains for text syncing to avoid lag while typing rapidly
        self._text_sync_timer = QTimer(self)
        self._text_sync_timer.setSingleShot(True)
        self._text_sync_timer.timeout.connect(self._sync_from_source)

        self._source.textChanged.connect(self.schedule_text_sync)
        self._source.cursorPositionChanged.connect(self._sync_scroll_from_source)

        source_scrollbar = self._source.verticalScrollBar()
        if source_scrollbar is not None:
            # Connect directly for instant, smooth 1:1 scroll synchronization
            source_scrollbar.valueChanged.connect(self._sync_scroll_from_source)

        self.verticalScrollBar().valueChanged.connect(self._sync_source_scroll)

        self.schedule_text_sync()

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

    def schedule_text_sync(self) -> None:
        if self._syncing:
            return
        self._text_sync_timer.start(30)

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
            self._update_overlay()
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
            self._update_overlay()
        finally:
            self._syncing = False

    def _update_overlay(self) -> None:
        """Calculate and update the position of the highlight overlay."""
        try:
            source = self._source
            if source is None:
                return

            first_line = source.SendScintilla(QsciScintilla.SCI_GETFIRSTVISIBLELINE)
            lines_visible = source.SendScintilla(QsciScintilla.SCI_LINESONSCREEN)
            minimap_first = self.SendScintilla(QsciScintilla.SCI_GETFIRSTVISIBLELINE)

            line_height = self.SendScintilla(QsciScintilla.SCI_TEXTHEIGHT, 0)
            if line_height <= 0:
                line_height = 2

            y_offset = (first_line - minimap_first) * line_height
            height = lines_visible * line_height

            self._overlay.update_geometry(y_offset, height)
            self._overlay.show()
        except Exception:
            pass

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_scroll_from_source()
        self._update_overlay()

    def _move_source_to_event(self, event: QMouseEvent) -> None:
        """Translate a click/drag on the minimap into a source editor scroll."""
        try:
            pos = event.position().toPoint()
            position = self.SendScintilla(
                QsciScintilla.SCI_POSITIONFROMPOINT, pos.x(), pos.y()
            )
            if position != -1:
                line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, position)
                visible_lines = self._source.SendScintilla(
                    QsciScintilla.SCI_LINESONSCREEN
                )

                # Center the view around the clicked line
                target_first_visible = max(0, line - (visible_lines // 2))
                self._source.SendScintilla(
                    QsciScintilla.SCI_SETFIRSTVISIBLELINE, target_first_visible
                )
        except Exception:
            pass

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._move_source_to_event(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging:
            self._move_source_to_event(event)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    def wheelEvent(self, event: QWheelEvent) -> None:
        # Pass scroll wheel events directly to the main editor
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
        minimap_width: int = 110,  # Increased default width to aid text fitting
    ):
        super().__init__(parent)
        self.setObjectName("MiniMapHostWidget")

        self._editor = editor
        self._minimap_width = minimap_width
        self._minimap_visible = True

        if self._editor.parent() is not self:
            self._editor.setParent(self)

        self._editor.position_changed.connect(self.position_changed.emit)
        self._editor.dirty_state_changed.connect(self.dirty_state_changed.emit)

        # Main layout holds the editor on the left and the minimap container on the right
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._editor, 1)

        # ------------------------------------------------------------------
        # VS2019-Style Minimap Container (Vertical Layout with Arrow Buttons)
        # ------------------------------------------------------------------
        self._minimap_container = QWidget(self)
        minimap_layout = QVBoxLayout(self._minimap_container)
        minimap_layout.setContentsMargins(0, 0, 0, 0)
        minimap_layout.setSpacing(0)

        # Up Scroll Button
        self._btn_up = QToolButton(self._minimap_container)
        self._btn_up.setArrowType(Qt.ArrowType.UpArrow)
        self._btn_up.setAutoRepeat(True)
        self._btn_up.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._btn_up.setStyleSheet(
            "QToolButton { border: none; background: transparent; padding: 4px; }"
            "QToolButton:hover { background: rgba(128, 128, 128, 0.2); }"
        )
        self._btn_up.clicked.connect(self._scroll_up)

        # The Minimap View
        self._minimap = MiniMapEditor(editor, self._minimap_container)

        # Down Scroll Button
        self._btn_down = QToolButton(self._minimap_container)
        self._btn_down.setArrowType(Qt.ArrowType.DownArrow)
        self._btn_down.setAutoRepeat(True)
        self._btn_down.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._btn_down.setStyleSheet(
            "QToolButton { border: none; background: transparent; padding: 4px; }"
            "QToolButton:hover { background: rgba(128, 128, 128, 0.2); }"
        )
        self._btn_down.clicked.connect(self._scroll_down)

        minimap_layout.addWidget(self._btn_up)
        minimap_layout.addWidget(self._minimap, 1)
        minimap_layout.addWidget(self._btn_down)

        self._minimap_container.setFixedWidth(self._minimap_width)
        layout.addWidget(self._minimap_container, 0)

    @property
    def editor(self) -> CodeEditor:
        return self._editor

    @property
    def minimap(self) -> MiniMapEditor:
        return self._minimap

    def _scroll_up(self) -> None:
        """Triggered by the Up arrow; scrolls the source editor up one step."""
        sb = self._editor.verticalScrollBar()
        if sb:
            sb.setValue(sb.value() - sb.singleStep())

    def _scroll_down(self) -> None:
        """Triggered by the Down arrow; scrolls the source editor down one step."""
        sb = self._editor.verticalScrollBar()
        if sb:
            sb.setValue(sb.value() + sb.singleStep())

    def set_minimap_visible(self, visible: bool) -> None:
        self._minimap_visible = visible
        self._minimap_container.setVisible(visible)
        self._minimap_container.setFixedWidth(self._minimap_width if visible else 0)
        if visible:
            self._minimap.schedule_text_sync()
            self._minimap._sync_scroll_from_source()

    def __getattr__(self, name: str):
        return getattr(self._editor, name)


def attach_minimap(
    editor: CodeEditor, parent: Optional[QWidget] = None, minimap_width: int = 150
) -> MiniMapHostWidget:
    return MiniMapHostWidget(editor, parent=parent, minimap_width=minimap_width)


def ensure_minimap(editor_or_host):
    """Return the MiniMapHostWidget for *editor_or_host*.

    If *editor_or_host* is already a ``MiniMapHostWidget`` it is returned
    as-is.  If it is a bare ``CodeEditor`` it is wrapped in a new host.
    """
    if isinstance(editor_or_host, MiniMapHostWidget):
        return editor_or_host
    return attach_minimap(editor_or_host)
