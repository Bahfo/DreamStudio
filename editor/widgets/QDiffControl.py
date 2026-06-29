from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QToolTip,
)
from PyQt6.QtGui import QFont, QColor, QFontMetrics

import difflib
import json
import pathlib
import logging

from editor.texteditor import keywords_path
from editor.texteditor.ironica_lexer.python_lexer import DreamPythonLexer
from editor.texteditor.ironica_lexer.python_jedi_highlighter import (
    DreamPythonHighlighter,
)

logger = logging.getLogger(__name__)


_LINE_ADDED_BG = "#1E3A1E"
_LINE_DELETED_BG = "#3A1E1E"
_LINE_MODIFIED_BG = "#3A3A1A"

_OLD_LABEL_BG = "#3D1A1A"
_OLD_LABEL_FG = "#FF6B6B"
_NEW_LABEL_BG = "#1A3D1A"
_NEW_LABEL_FG = "#4ECF4E"

SCI_MARKERDEFINE = 2040
SCI_MARKERSETBACK = 2042
SCI_MARKERADD = 2043
SCI_MARKERDELETEALL = 2045
SC_MARK_BACKGROUND = 33

MARKER_ADDED = 0
MARKER_DELETED = 1
MARKER_MODIFIED = 2


class _DiffEditor(QsciScintilla):
    def __init__(self, side="old", _parent=None):
        super().__init__(_parent)
        self._side = side
        self._parent_widget = _parent
        self._lexer = None
        self._blame_timer = QTimer(self)
        self._blame_timer.setSingleShot(True)
        self._blame_timer.setInterval(3000)
        self._blame_timer.timeout.connect(self._on_blame_timeout)
        self._hover_line = -1

        self._font = QFont("Jetbrains Mono", 11)
        self.setFont(self._font)
        self.setUtf8(True)

        self.setReadOnly(True)

        self.setAutoIndent(True)
        self.setBackspaceUnindents(True)
        self.setTabIndents(True)
        self.setIndentationWidth(4)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.SendScintilla(QsciScintilla.SCI_SETINDENTATIONGUIDES, 0)

        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "000000")
        self.setMarginLineNumbers(0, True)
        self.setMarginsBackgroundColor(QColor("#1C1C1C"))
        self.setMarginsForegroundColor(QColor("#5F5F5F"))
        self.setFoldMarginColors(QColor("#1C1C1C"), QColor("#1C1C1C"))

        self.setCaretForegroundColor(QColor("white"))
        self.setCaretLineVisible(False)
        self.setCaretWidth(1)

        self.setBraceMatching(QsciScintilla.BraceMatch.NoBraceMatch)
        self.setFolding(QsciScintilla.FoldStyle.PlainFoldStyle)

        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 12)
        self.setMarginSensitivity(1, True)

        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
        self.setEdgeColumn(80)
        self.setEdgeColor(QColor("#444444"))

        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._setup_markers()
        self._apply_scrollbar_style()

        self.setMouseTracking(True)
        self.SCN_DWELLSTART.connect(self._on_dwell_start)
        self.SCN_DWELLEND.connect(self._on_dwell_end)

    def _setup_markers(self):
        self.SendScintilla(SCI_MARKERDEFINE, MARKER_ADDED, SC_MARK_BACKGROUND)
        self.SendScintilla(SCI_MARKERSETBACK, MARKER_ADDED, QColor(_LINE_ADDED_BG))
        self.SendScintilla(SCI_MARKERDEFINE, MARKER_DELETED, SC_MARK_BACKGROUND)
        self.SendScintilla(SCI_MARKERSETBACK, MARKER_DELETED, QColor(_LINE_DELETED_BG))
        self.SendScintilla(SCI_MARKERDEFINE, MARKER_MODIFIED, SC_MARK_BACKGROUND)
        self.SendScintilla(
            SCI_MARKERSETBACK, MARKER_MODIFIED, QColor(_LINE_MODIFIED_BG)
        )

    def _apply_scrollbar_style(self, t=None):
        try:
            if t is not None:
                bg = t.color("scrollbar.bg", "#1E1E1E")
                fg = t.color("scrollbar.fg", "#424242")
                hover = t.color("scrollbar.hover", "#555555")
            else:
                bg = "#1E1E1E"
                fg = "#424242"
                hover = "#555555"
            css = f"""
                QScrollBar:vertical {{
                    background: {bg};
                    width: 8px;
                    margin: 0;
                    border: none;
                }}
                QScrollBar::handle:vertical {{
                    background: {fg};
                    min-height: 24px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {hover};
                }}
                QScrollBar:horizontal {{
                    background: {bg};
                    height: 8px;
                    margin: 0;
                    border: none;
                }}
                QScrollBar::handle:horizontal {{
                    background: {fg};
                    min-width: 24px;
                }}
                QScrollBar::handle:horizontal:hover {{
                    background: {hover};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    height: 0;
                    width: 0;
                    border: none;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                    background: none;
                    border: none;
                }}
            """
            vsb = self.verticalScrollBar()
            if vsb:
                vsb.setStyleSheet(css)
            hsb = self.horizontalScrollBar()
            if hsb:
                hsb.setStyleSheet(css)
        except RuntimeError:
            pass

    def clear_markers(self):
        self.SendScintilla(SCI_MARKERDELETEALL, MARKER_ADDED)
        self.SendScintilla(SCI_MARKERDELETEALL, MARKER_DELETED)
        self.SendScintilla(SCI_MARKERDELETEALL, MARKER_MODIFIED)

    def add_line_marker(self, line, marker_type):
        self.SendScintilla(SCI_MARKERADD, line, marker_type)

    def apply_theme_colors(self, bg="#1E1E1E", fg="#D4D4D4"):
        self.setPaper(QColor(bg))
        self.setColor(QColor(fg))
        self.setMarginsBackgroundColor(QColor(bg))
        self.setMarginsForegroundColor(QColor(fg))

    def retheme(self, t):
        bg = t.color("editor.background", "#1E1E1E")
        fg = t.color("editor.text", "#D4D4D4")
        sel_bg = t.color("editor.selection_bg", "#264F78")
        self.setPaper(QColor(bg))
        self.setColor(QColor(fg))
        self.setSelectionBackgroundColor(QColor(sel_bg))
        self.setMarginsBackgroundColor(QColor(bg))
        self.setMarginsForegroundColor(QColor(fg))
        self.setFoldMarginColors(QColor(bg), QColor(bg))
        self._apply_scrollbar_style(t)

        added_bg = t.color("diff.added_bg", _LINE_ADDED_BG)
        deleted_bg = t.color("diff.deleted_bg", _LINE_DELETED_BG)
        modified_bg = t.color("diff.modified_bg", _LINE_MODIFIED_BG)
        self.SendScintilla(SCI_MARKERSETBACK, MARKER_ADDED, QColor(added_bg))
        self.SendScintilla(SCI_MARKERSETBACK, MARKER_DELETED, QColor(deleted_bg))
        self.SendScintilla(SCI_MARKERSETBACK, MARKER_MODIFIED, QColor(modified_bg))
        self.update()

        if self._lexer is not None:
            if hasattr(self._lexer, "apply_syntax_theme"):
                self._lexer.apply_syntax_theme(t)
            else:
                self._lexer.setDefaultColor(QColor(fg))
                for style in range(128):
                    self._lexer.setPaper(QColor(bg), style)

    def set_language(self, lang: str):
        if not lang or lang != "Python":
            self._lexer = None
            self.setLexer(None)
            return

        path = keywords_path("python_highlights.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            logger.debug(
                "Failed to load python_highlights.json, falling back to keyword lexer"
            )
            self._lexer = self._load_keyword_lexer()
            if self._lexer:
                self._lexer.apply_font(self._font)
                self.setLexer(self._lexer)
            return

        lexer = DreamPythonHighlighter(self, data)
        lexer.apply_font(self._font)
        self._lexer = lexer
        self.setLexer(lexer)

    def _load_keyword_lexer(self):
        path = keywords_path("python.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

        from PyQt6.Qsci import QsciAPIs

        lexer = DreamPythonLexer(self, data)
        api = QsciAPIs(lexer)
        for word in data.get("words", {}):
            api.add(word)
        for word in data.get("types", {}):
            api.add(word)
        for word in data.get("iterators", {}):
            api.add(word)
        for word in data.get("exceptions", {}):
            api.add(word)
        api.prepare()
        return lexer

    def _on_dwell_start(self, pos, x, y):
        line, index = self.lineIndexFromPosition(pos)
        if line < 0:
            return
        self._hover_line = line
        self._blame_timer.start()

    def _on_dwell_end(self, pos, x, y):
        self._blame_timer.stop()
        self._hover_line = -1

    def _on_blame_timeout(self):
        if self._hover_line < 0:
            return
        file_path = getattr(self._parent_widget, "file_path", None)
        if not file_path:
            return
        repo = getattr(self._parent_widget, "_repo", None)
        if repo is None:
            return
        from backend.git_control import get_blame_info

        info = get_blame_info(repo, file_path, self._hover_line)
        if info is None:
            return

        line_text = self.text(self._hover_line).strip()
        side_tag = "Old" if self._side == "old" else "New"

        html = (
            f"<div style='font-family: 'inter', sans-serif; font-size: 12px;'>"
            f"<b style='color: #569CD6;'>{side_tag}</b> "
            f"<span style='color: #888;'>|</span> "
            f"<b>Line {self._hover_line + 1}:</b> "
            f"<code style='color: #D4D4D4;'>{line_text[:60]}</code><br>"
            f"<hr style='border: none; border-top: 1px solid #444; margin: 4px 0;'>"
            f"<b style='color: #C586C0;'>{info['author']}</b>"
            f" <span style='color: #888;'>&lt;{info['email']}&gt;</span><br>"
            f"<span style='color: #6BBF6B;'>{info['date']}</span>"
            f" <span style='color: #888;'>|</span> "
            f"<code style='color: #DCDCAA;'>{info['hexsha']}</code><br>"
            f"<span style='color: #A9B7C6;'>{info['summary']}</span>"
            f"</div>"
        )

        sci_pos = self.positionFromLineIndex(self._hover_line, 0)
        x = self.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, sci_pos)
        y = self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, sci_pos)
        global_pos = self.mapToGlobal(QPoint(x + 20, y + self._font.pointSize() + 8))
        QToolTip.showText(global_pos, html)


class QDiffControl(QFrame):
    def __init__(
        self, file_path="", old_content="", new_content="", repo=None, _parent=None
    ):
        super().__init__(_parent)
        self._parent = _parent
        self.file_path = file_path
        self._repo = repo
        self.file_key = None
        self.viewer_type = "diff"

        self._build_ui()
        self._load_content(old_content, new_content)

    def _build_ui(self):
        self.setStyleSheet("background-color: #171717; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("background-color: #1E1E1E;")
        header.setFixedHeight(36)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        file_name = pathlib.Path(self.file_path).name if self.file_path else "Unknown"
        self.header_label = QLabel(f"Diff: {file_name}")
        self.header_label.setStyleSheet(
            "color: #D4D4D4; font-size: 12px; font-weight: bold; background: transparent;"
        )
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet(
            "color: #969696; font-size: 11px; background: transparent;"
        )
        header_layout.addWidget(self.stats_label)

        layout.addWidget(header)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(3)

        old_container = QFrame()
        old_container.setStyleSheet("background-color: transparent; border: none;")
        old_layout = QVBoxLayout(old_container)
        old_layout.setContentsMargins(0, 0, 0, 0)
        old_layout.setSpacing(0)

        old_sub_header = QLabel("  Old File")
        old_sub_header.setFixedHeight(24)
        old_sub_header.setStyleSheet(
            f"""
            color: {_OLD_LABEL_FG}; font-size: 10px; font-weight: bold;
            background-color: {_OLD_LABEL_BG}; padding-left: 8px;
        """
        )
        old_layout.addWidget(old_sub_header)
        self._old_sub_header = old_sub_header

        self.old_editor = _DiffEditor(side="old", _parent=self)
        old_layout.addWidget(self.old_editor)

        new_container = QFrame()
        new_container.setStyleSheet("background-color: transparent; border: none;")
        new_layout = QVBoxLayout(new_container)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.setSpacing(0)

        new_sub_header = QLabel("  New File")
        new_sub_header.setFixedHeight(24)
        new_sub_header.setStyleSheet(
            f"""
            color: {_NEW_LABEL_FG}; font-size: 10px; font-weight: bold;
            background-color: {_NEW_LABEL_BG}; padding-left: 8px;
        """
        )
        new_layout.addWidget(new_sub_header)
        self._new_sub_header = new_sub_header

        self.new_editor = _DiffEditor(side="new", _parent=self)
        new_layout.addWidget(self.new_editor)

        self.splitter.addWidget(old_container)
        self.splitter.addWidget(new_container)
        self.splitter.setSizes([1, 1])

        layout.addWidget(self.splitter)

        self._sync_scrolling()

    def _load_content(self, old_content, new_content):
        self.old_editor.clear_markers()
        self.new_editor.clear_markers()

        lang = None
        if self.file_path and self.file_path.endswith(".py"):
            lang = "Python"
        self.old_editor.set_language(lang)
        self.new_editor.set_language(lang)

        self.old_editor.setText(old_content)
        self.new_editor.setText(new_content)

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        opcodes = matcher.get_opcodes()

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                continue
            elif tag == "delete":
                for i in range(i1, i2):
                    self.old_editor.add_line_marker(i, MARKER_DELETED)
            elif tag == "insert":
                for j in range(j1, j2):
                    self.new_editor.add_line_marker(j, MARKER_ADDED)
            elif tag == "replace":
                for i in range(i1, i2):
                    self.old_editor.add_line_marker(i, MARKER_MODIFIED)
                for j in range(j1, j2):
                    self.new_editor.add_line_marker(j, MARKER_MODIFIED)

        old_line_count = len(old_lines)
        new_line_count = len(new_lines)
        added_count = 0
        deleted_count = 0

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "insert":
                added_count += j2 - j1
            elif tag == "delete":
                deleted_count += i2 - i1
            elif tag == "replace":
                deleted_count += i2 - i1
                added_count += j2 - j1

        stats_parts = []
        if old_line_count != new_line_count:
            stats_parts.append(f"{old_line_count} \u2192 {new_line_count} lines")
        if added_count:
            stats_parts.append(f"+{added_count}")
        if deleted_count:
            stats_parts.append(f"-{deleted_count}")
        if stats_parts:
            self.stats_label.setText("  ".join(stats_parts))
        else:
            self.stats_label.setText("")

        self.old_editor.setCursorPosition(0, 0)
        self.new_editor.setCursorPosition(0, 0)

    def _sync_scrolling(self):
        old_sb = self.old_editor.verticalScrollBar()
        new_sb = self.new_editor.verticalScrollBar()

        def sync_old_to_new(value):
            if not self._syncing:
                self._syncing = True
                new_sb.setValue(value)
                self._syncing = False

        def sync_new_to_old(value):
            if not self._syncing:
                self._syncing = True
                old_sb.setValue(value)
                self._syncing = False

        self._syncing = False
        old_sb.valueChanged.connect(sync_old_to_new)
        new_sb.valueChanged.connect(sync_new_to_old)

    def retheme(self, t):
        bg = t.color("sidebar.background", "#171717")
        self.setStyleSheet(f"background-color: {bg}; border: none;")

        self.old_editor.retheme(t)
        self.new_editor.retheme(t)

        txt = t.color("window.text", "#D4D4D4")
        self.header_label.setStyleSheet(
            f"color: {txt}; font-size: 12px; font-weight: bold; background: transparent;"
        )
        self.stats_label.setStyleSheet(
            f"color: {t.color('sidebar.text', '#969696')}; font-size: 11px; background: transparent;"
        )

        hdr_bg = t.color("titlebar.background", "#1E1E1E")
        header = self.layout().itemAt(0).widget()
        header.setStyleSheet(f"background-color: {hdr_bg};")

        old_fg = t.color("git.deleted", _OLD_LABEL_FG)
        new_fg = t.color("git.added", _NEW_LABEL_FG)

        self._old_sub_header.setStyleSheet(
            f"""
            color: {old_fg}; font-size: 10px; font-weight: bold;
            background-color: {t.color('editor.background', '#1E1E1E')}; padding-left: 8px;
        """
        )
        self._new_sub_header.setStyleSheet(
            f"""
            color: {new_fg}; font-size: 10px; font-weight: bold;
            background-color: {t.color('editor.background', '#1E1E1E')}; padding-left: 8px;
        """
        )

    def set_content(self, file_path, old_content, new_content, repo=None):
        self.file_path = file_path
        if repo is not None:
            self._repo = repo
        file_name = pathlib.Path(file_path).name if file_path else "Unknown"
        self.header_label.setText(f"Diff: {file_name}")
        self._load_content(old_content, new_content)
