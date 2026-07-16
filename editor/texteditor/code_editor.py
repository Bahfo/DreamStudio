"""
(C) COPYRIGHT 2026 - EXcellent TechStacks, All Rights Reserved.

Ironica Code Editor - Lightweight static text editor for DreamStudio.

This code is protected under the GPLv3 License.
"""

# Written By Bahaa Nofal - 26/May/2026

import logging
import pathlib
import re
import stat

from typing import Optional, Any

from PyQt6.QtCore import Qt, QEvent, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QKeyEvent, QPalette
from PyQt6.QtWidgets import QApplication
from PyQt6.Qsci import QsciScintilla

from editor.texteditor.language_engine import LanguageRegistry, LanguageLexer
from editor.texteditor.autocomplete_menu import EditorAutocompleteExtension, HoverDocumentationPopup

logger = logging.getLogger(__name__)


class CodeEditor(QsciScintilla):
    """
    Base class code editor for complex language support for DreamStudio.

    Builds on top of QScintilla. The ``CodeEditor`` class supports a multi-
    plugin system for languages support via its modern engine built on top
    of Ironica Lexers.

    **Ownership Model:**

    The editor owns the following state exclusively:

    - Text content (via QScintilla buffer)
    - Cursor position and selection
    - Modified (dirty) flag (via ``isModified()``)
    - Lexer and language configuration
    - Read-only state (via ``setReadOnly()``)
    - ``current_file_path`` — the canonical path of the file on disk
    - ``current_lang`` — the resolved language identifier
    - ``current_provider`` — the language intelligence provider

    The tab manager (``DreamTabbedEditor``) owns:

    - Tab title, position, and ordering
    - The ``opened_files`` deduplication map
    - Per-tab UI indicators (dirty dot, read-only lock)
    """

    position_changed = pyqtSignal(int, int)
    dirty_state_changed = pyqtSignal(bool)

    _INDENTATION_SPACING = 4

    def __init__(self, _parent=None, language=None, file_path=None):
        """
        Initialise the editor widget.

        Args:
            _parent: Parent widget (typically the tab editor).
            language: Optional language identifier string. When ``None``,
                no syntax highlighting or provider is attached.
            file_path: Optional file path to load immediately. If provided,
                ``load_from_file`` is called during construction.
        """
        super().__init__(_parent)

        self._lexer = None
        self._parent = _parent
        self.current_file_path = None
        self._font_size = 10
        self._is_dirty = False

        self.setObjectName("CodeEditor")

        self.textChanged.connect(self._on_text_changed)

        # Language state — single source of truth.
        self.current_lang: Optional[str] = None
        self.current_provider: Optional[Any] = None

        self._font = QFont()
        self._font.setFamilies(["JetBrains Mono", "Consolas", "Courier New", "monospace"])
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        self._font.setPointSize(11)
        self.setFont(self._font)
        try:
            self.setUtf8(True)
        except Exception:
            pass

        self.setMouseTracking(True)
        self._setup_indentation()
        self._setup_auto_indent()
        self._setup_margins()
        self._setup_folding()
        self._setup_caret()
        self._setup_edge()
        self._setup_wrap()

        # Hover timer for documentation tooltips.
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._on_hover_timeout)
        self._last_mouse_pos = None
        self._hover_popup: Optional[HoverDocumentationPopup] = None

        # Import highlighting indicators (debounced).
        self._import_highlight_timer = QTimer(self)
        self._import_highlight_timer.setSingleShot(True)
        self._import_highlight_timer.setInterval(300)
        self._import_highlight_timer.timeout.connect(self._apply_semantic_indicators)

        self.cursorPositionChanged.connect(self._emit_position)

        # QScintilla AutoCompletion configuration.
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsNone)
        self.setAutoCompletionThreshold(2)
        self.setAutoCompletionCaseSensitivity(True)
        self.setAutoCompletionReplaceWord(True)
        self.setAutoCompletionUseSingle(QsciScintilla.AutoCompletionUseSingle.AcusNever)

        self.userListActivated.connect(self._on_completion_selected)

        # Autocomplete extension — event filter + popup controller.
        self._autocomplete_ext = EditorAutocompleteExtension(self)
        self._autocomplete_ext.install()

        # Apply language if provided.
        if language:
            self.setLanguage(language)

        # Load file if provided.
        if file_path:
            self.load_from_file(file_path)

    # ------------------------------------------------------------------
    # Dirty state
    # ------------------------------------------------------------------

    def _on_text_changed(self) -> None:
        if not self._is_dirty:
            self._is_dirty = True
            self.dirty_state_changed.emit(True)
        if self.current_lang == "python":
            self._import_highlight_timer.start()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _setup_indentation(self) -> None:
        """Configure indentation, tab width, and backspace behaviour."""
        self.setAutoIndent(True)
        self.setBackspaceUnindents(True)
        self.setTabIndents(True)
        self.setIndentationWidth(self._INDENTATION_SPACING)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(self._INDENTATION_SPACING)
        self.SendScintilla(QsciScintilla.SCI_SETINDENTATIONGUIDES, 3)

    def _theme_colors(self):
        """Derive palette colours for margins, caret, and folding."""
        pal = self.palette()
        bg = pal.color(QPalette.ColorRole.Window)
        text = pal.color(QPalette.ColorRole.WindowText)
        mid = bg.lighter(130) if bg.lightness() < 128 else bg.darker(115)
        border = bg.lighter(150) if bg.lightness() < 128 else bg.darker(130)
        return bg, text, mid, border

    def _setup_margins(self) -> None:
        """Configure line-number and folding margins."""
        bg, text, mid, border = self._theme_colors()
        self.setPaper(bg)
        self.setColor(text)
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "000000")
        self.setMarginLineNumbers(0, True)
        self.setMarginsBackgroundColor(bg)
        self.setMarginsForegroundColor(text)
        self.setFoldMarginColors(mid, mid)

    def _setup_caret(self) -> None:
        """Configure caret appearance."""
        bg, text, mid, _ = self._theme_colors()
        self.setCaretForegroundColor(text)
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(mid)
        self.setCaretWidth(2)

    def _setup_folding(self) -> None:
        """Configure code folding markers."""
        _, _, mid, _ = self._theme_colors()
        self.setFolding(QsciScintilla.FoldStyle.PlainFoldStyle)
        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 12)
        self.setMarginSensitivity(1, True)

        self.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDER)
        self.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDEROPEN)
        self.markerDefine(
            QsciScintilla.MarkerSymbol.Plus,
            QsciScintilla.SC_MARKNUM_FOLDER,
        )
        self.markerDefine(
            QsciScintilla.MarkerSymbol.Minus,
            QsciScintilla.SC_MARKNUM_FOLDEROPEN,
        )

    def _setup_edge(self) -> None:
        """Configure the long-line edge marker."""
        _, _, mid, _ = self._theme_colors()
        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
        self.setEdgeColumn(80)
        self.setEdgeColor(mid)

    def _setup_wrap(self) -> None:
        """Configure word-wrap mode."""
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def _setup_auto_indent(self) -> None:
        """Configure brace matching."""
        self.setBraceMatching(QsciScintilla.BraceMatch.StrictBraceMatch)

    # ------------------------------------------------------------------
    # Position / signals
    # ------------------------------------------------------------------

    def _emit_position(self, line: int, col: int) -> None:
        """Forward cursor position changes to the ``position_changed`` signal."""
        self.position_changed.emit(line, col)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

    def wheelEvent(self, event) -> None:
        """Dismiss all popups and cancel hover when the editor scrolls."""
        self._hover_timer.stop()
        self._dismiss_all_popups()
        super().wheelEvent(event)

    def changeEvent(self, event) -> None:
        if event.type() in (
            QEvent.Type.StyleChange,
            QEvent.Type.PaletteChange,
        ):
            if getattr(self, "_in_change_event", False):
                return
            self._in_change_event = True
            try:
                self._setup_margins()
                self._setup_caret()
                self._setup_folding()
                self._setup_edge()
            finally:
                self._in_change_event = False
        elif event.type() == QEvent.Type.WindowStateChange:
            self._dismiss_all_popups()
        super().changeEvent(event)

    def focusOutEvent(self, event) -> None:
        """Dismiss hover popup when the editor loses focus."""
        self._dismiss_hover()
        super().focusOutEvent(event)

    # ------------------------------------------------------------------
    # Font management
    # ------------------------------------------------------------------

    @property
    def font_size(self) -> int:
        """Current font point size."""
        return self._font_size

    @font_size.setter
    def font_size(self, size: int) -> None:
        self._font_size = int(size)
        self._font.setPointSize(self._font_size)
        self.setFont(self._font)
        self.setMarginsFont(self._font)
        if self._lexer and hasattr(self._lexer, "setFont"):
            self._lexer.setFont(self._font, -1)

    def set_editor_font(self, font) -> None:
        """
        Set the editor font family or QFont instance.

        Args:
            font: A ``QFont`` instance or a font family name string.
        """
        if isinstance(font, QFont):
            self._font = QFont(font)
        else:
            self._font = QFont()
            self._font.setFamilies([str(font), "Consolas", "Courier New", "monospace"])
            self._font.setStyleHint(QFont.StyleHint.Monospace)

        self._font.setPointSize(self.font_size)
        self.setFont(self._font)
        self.setMarginsFont(self._font)

        if self._lexer and hasattr(self._lexer, "setFont"):
            self._lexer.setFont(self._font, -1)

    def set_editor_font_size(self, font_size: int) -> None:
        """Set the editor font point size."""
        self.font_size = int(font_size)

    def set_wrap_mode(self, enabled: bool = False) -> None:
        """Enable or disable word wrapping."""
        self.setWrapMode(
            QsciScintilla.WrapMode.WrapNone
            if not enabled
            else QsciScintilla.WrapMode.WrapWord
        )
        if not enabled:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    # ------------------------------------------------------------------
    # Keyboard events
    # ------------------------------------------------------------------

    def keyPressEvent(self, e: QKeyEvent) -> None:
        """Intercept key events for autocomplete trigger, goto definition,
        and enhanced enter/return behaviour."""
        # Dismiss hover popup on any key press.
        self._dismiss_hover()

        if (
            e.modifiers() == Qt.KeyboardModifier.ControlModifier
            and e.key() == Qt.Key.Key_Space
        ):
            self._autocomplete_ext.trigger_autocomplete()
            e.accept()
            return

        if e.key() == Qt.Key.Key_F12:
            self.execute_goto_definition()
            e.accept()
            return

        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            line, index = self.getCursorPosition()
            current_line_text = self.text(line)

            base_indent = ""
            for ch in current_line_text:
                if ch in (" ", "\t"):
                    base_indent += ch
                else:
                    break

            if current_line_text.rstrip().endswith((":", "{", "(")):
                indent = base_indent + (" " * self._INDENTATION_SPACING)
            else:
                indent = base_indent

            self.beginUndoAction()
            self.insert("\n" + indent)
            self.endUndoAction()
            self.setCursorPosition(line + 1, len(indent))
            return

        super().keyPressEvent(e)

        if e.text() == "." or (e.text().isalnum() and not self.isListActive()):
            self._autocomplete_ext.schedule_autocomplete()

    # ------------------------------------------------------------------
    # Mouse events / hover
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, e):
        """Track cursor movement for the documentation hover window."""
        super().mouseMoveEvent(e)
        self._last_mouse_pos = e.position().toPoint()

        self._hover_timer.stop()
        if self.current_provider:
            self._hover_timer.start(1000)

    def leaveEvent(self, event):
        """Mouse left the editor — start hover popup dismiss timer."""
        self._hover_timer.stop()
        if self._hover_popup and self._hover_popup.isVisible():
            self._hover_popup._dismiss_timer.start()
        super().leaveEvent(event)

    def mousePressEvent(self, e: QKeyEvent) -> None:
        """Intercept Ctrl+Click for go-to-definition navigation."""
        # Dismiss hover popup on any mouse click.
        self._dismiss_hover()

        if (
            e.button() == Qt.MouseButton.LeftButton
            and e.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            px = int(e.position().x())
            py = int(e.position().y())
            position = self.SendScintilla(
                QsciScintilla.SCI_POSITIONFROMPOINT, px, py
            )
            if position != -1:
                line, col = self.lineIndexFromPosition(position)
                self.setCursorPosition(line, col)
                self.execute_goto_definition()
                e.accept()
                return

        super().mousePressEvent(e)

    def _on_hover_timeout(self) -> None:
        """Show a scrollable documentation popup when the cursor hovers
        over a symbol with a provider."""
        if not self.current_provider or not self._last_mouse_pos:
            return

        try:
            px = int(self._last_mouse_pos.x())
            py = int(self._last_mouse_pos.y())
            position = self.SendScintilla(
                QsciScintilla.SCI_POSITIONFROMPOINT, px, py
            )
            if position == -1:
                return
            line, col = self.lineIndexFromPosition(position)

            html = None
            if hasattr(self.current_provider, "get_hover_html"):
                html = self.current_provider.get_hover_html(self.text(), line, col)
            if not html:
                hint = self.current_provider.get_hover_hint(self.text(), line, col)
                if hint:
                    html = f"<pre style='margin:0; white-space:pre-wrap;'>{hint}</pre>"

            if not html:
                self._dismiss_hover()
                return

            if self._hover_popup is None:
                self._hover_popup = HoverDocumentationPopup()

            global_pos = self.mapToGlobal(self._last_mouse_pos)
            self._hover_popup.show_html(html, global_pos)
        except Exception as exc:
            logger.debug("Hover query failed: %s", exc)

    def _dismiss_hover(self) -> None:
        """Immediately hide the hover documentation popup."""
        if self._hover_popup and self._hover_popup.isVisible():
            self._hover_popup.hide()

    def _dismiss_all_popups(self) -> None:
        """Dismiss every open sub‑menu (hover + autocomplete)."""
        self._dismiss_hover()
        ext = getattr(self, "_autocomplete_ext", None)
        if ext is not None:
            ext.cancel_autocomplete()

    # ------------------------------------------------------------------
    # Go-to definition
    # ------------------------------------------------------------------

    def execute_goto_definition(self) -> None:
        """Resolve the symbol under the cursor and navigate to its definition.

        Falls back gracefully if no provider is active or the symbol
        cannot be resolved.  All provider errors are caught so that a
        plugin failure never crashes the editor.
        """
        if not self.current_provider:
            return

        try:
            line, col = self.getCursorPosition()
            target = self.current_provider.get_definition_location(
                self.text(), line, col
            )

            if not target:
                return

            file_path, target_line, target_col = target

            # Guard: empty or None file path — nothing to navigate to.
            if not file_path:
                return

            # Guard: already at the definition (same file + same line).
            current_path = getattr(self, "current_file_path", "") or ""
            if (
                file_path == current_path
                and target_line == line
            ):
                return

            tab_widget = self._parent
            if tab_widget and hasattr(tab_widget, "open_file_at_line"):
                tab_widget.open_file_at_line(file_path, target_line)

                current_editor = tab_widget.currentWidget()
                if current_editor and hasattr(
                    current_editor, "setCursorPosition"
                ):
                    current_editor.setCursorPosition(target_line, target_col)
        except Exception as exc:
            logger.debug("Go-to-definition failed: %s", exc)

    # ------------------------------------------------------------------
    # Language / lexer
    # ------------------------------------------------------------------

    def setLanguage(self, lang: str) -> None:
        """Assign a language to the editor.

        Args:
            lang: Language identifier (e.g. ``"python"``). When empty or
                ``None``, all language support is removed.
        """
        if not lang:
            self._lexer = None
            self.setLexer(None)
            self.current_lang = None
            self.current_provider = None
            return

        self.current_lang = lang
        self.current_provider = LanguageRegistry.get_provider(lang)
        config = LanguageRegistry.get_config(lang)

        if config:
            self._lexer = self._create_lexer(lang, config)
            self.setLexer(self._lexer)
            # Propagate editor font to ALL lexer style indices so
            # QsciLexerPython doesn't keep its Bitstream Vera defaults.
            if hasattr(self._lexer, "setFont"):
                self._lexer.setFont(self._font, -1)
            self._apply_semantic_indicators()
        else:
            self._lexer = None
            self.setLexer(None)

    def _create_lexer(self, lang: str, config: dict):
        """Create the best available lexer for *lang*.

        For Python, prefer the built-in ``QsciLexerPython`` which
        handles stateful syntax (comments, strings, f-strings) correctly.
        Falls back to the generic ``LanguageLexer`` for other languages.
        """
        if lang == "python":
            try:
                from PyQt6.Qsci import QsciLexerPython

                lexer = QsciLexerPython(self)
                self._apply_config_to_builtin_lexer(lexer, config)
                return lexer
            except ImportError:
                logger.debug(
                    "QsciLexerPython not available, falling back to LanguageLexer"
                )

        return LanguageLexer(self, config)

    def _apply_config_to_builtin_lexer(self, lexer, config: dict) -> None:
        """Apply custom colours from a JSON config to a built-in QScintilla lexer.

        Maps the config's ``"styles"`` dictionary onto the built-in
        lexer's style indices using the colour values.  Also propagates
        the ``string`` and ``comment`` colours to all variant styles
        (single/double/triple-quoted, f-strings, block comments).
        """
        from PyQt6.QtGui import QColor

        styles = config.get("styles", {})

        # Resolve collisions: use unique QsciLexerPython style indices
        # that don't overlap.
        colour_map = {
            "keyword": lexer.Keyword,               # 5
            "builtin": lexer.HighlightedIdentifier,  # 14
            "definition": lexer.FunctionMethodName,  # 9
            "class_def": lexer.ClassName,            # 8
            "string": lexer.DoubleQuotedString,      # 3
            "number": lexer.Number,                  # 2
            "comment": lexer.Comment,                # 1
            "decorator": lexer.Decorator,            # 15
            "operator": lexer.Operator,              # 10
        }

        for style_name, color_hex in styles.items():
            style_idx = colour_map.get(style_name)
            if style_idx is not None:
                lexer.setColor(QColor(color_hex), style_idx)

        # Propagate "string" colour to ALL string style variants.
        if "string" in styles:
            string_color = QColor(styles["string"])
            for idx in (
                lexer.SingleQuotedString,           # 4
                lexer.TripleDoubleQuotedString,     # 7
                lexer.TripleSingleQuotedString,     # 6
                lexer.UnclosedString,               # 13
                lexer.DoubleQuotedFString,          # 16
                lexer.SingleQuotedFString,          # 17
                lexer.TripleDoubleQuotedFString,    # 19
                lexer.TripleSingleQuotedFString,    # 18
            ):
                lexer.setColor(string_color, idx)

        # Propagate "comment" colour to block comments.
        if "comment" in styles:
            lexer.setColor(QColor(styles["comment"]), lexer.CommentBlock)  # 12

    # ------------------------------------------------------------------
    # Semantic indicators (imports, special keywords)
    # ------------------------------------------------------------------

    @staticmethod
    def _scintilla_rgb(hex_color: str) -> int:
        """Convert a ``#RRGGBB`` CSS colour to Scintilla's ``0x00BBGGRR``."""
        from PyQt6.QtGui import QColor
        c = QColor(hex_color)
        return ((c.blue() & 0xFF) << 16) | ((c.green() & 0xFF) << 8) | (c.red() & 0xFF)

    # Slot indices used for Scintilla indicators.
    _IND_IMPORT_CLASS = 0   # greenish  #4EC9B0  (classes / modules)
    _IND_IMPORT_FUNC  = 1   # yellowish #DCDCAA  (functions)
    _IND_SPECIAL_KW   = 2   # blue      #569CD6  (None, self, True …)

    _SPECIAL_KEYWORDS = frozenset({
        "None", "True", "False", "self", "cls",
    })
    _SPECIAL_DUNDER = True   # highlight dunder names like __name__

    def _apply_semantic_indicators(self) -> None:
        """Apply Scintilla indicators for import targets and special keywords.

        Indicator 0 → greenish  ``#4EC9B0`` (classes / modules)
        Indicator 1 → yellowish ``#DCDCAA`` (functions)
        Indicator 2 → blue      ``#569CD6`` (None, True, False, self …)
        """
        from PyQt6.QtGui import QColor

        if self.current_lang != "python":
            return

        text = self.text()
        if not text:
            return

        length = len(text)

        # ── clear all indicator slots ────────────────────────────────
        for ind in (self._IND_IMPORT_CLASS, self._IND_IMPORT_FUNC,
                    self._IND_SPECIAL_KW):
            self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, ind)
            self.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, 0, length)

        # ── configure indicator styles ───────────────────────────────
        self.SendScintilla(QsciScintilla.SCI_INDICSETSTYLE,
                           self._IND_IMPORT_CLASS, QsciScintilla.INDIC_TEXTFORE)
        self.SendScintilla(QsciScintilla.SCI_INDICSETFORE,
                           self._IND_IMPORT_CLASS,
                           self._scintilla_rgb("#4EC9B0"))

        self.SendScintilla(QsciScintilla.SCI_INDICSETSTYLE,
                           self._IND_IMPORT_FUNC, QsciScintilla.INDIC_TEXTFORE)
        self.SendScintilla(QsciScintilla.SCI_INDICSETFORE,
                           self._IND_IMPORT_FUNC,
                           self._scintilla_rgb("#DCDCAA"))

        self.SendScintilla(QsciScintilla.SCI_INDICSETSTYLE,
                           self._IND_SPECIAL_KW, QsciScintilla.INDIC_TEXTFORE)
        self.SendScintilla(QsciScintilla.SCI_INDICSETFORE,
                           self._IND_SPECIAL_KW,
                           self._scintilla_rgb("#569CD6"))

        # ── import targets ───────────────────────────────────────────
        _FROM_IMPORT_RE = re.compile(
            r"from\s+([\w.]+)\s+import\s+(.+?)(?:\n|$)"
        )
        _PLAIN_IMPORT_RE = re.compile(
            r"^import\s+(.+?)(?:\n|$)", re.MULTILINE
        )
        _IDENT_RE = re.compile(r"[\w]+")

        # from M import X, Y  → highlight M and each target
        for m in _FROM_IMPORT_RE.finditer(text):
            # Module name (e.g. "os", "os.path")
            mod_name = m.group(1)
            mod_start = text.find(mod_name, m.start(1))
            if mod_start != -1:
                self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT,
                                   self._IND_IMPORT_CLASS)
                self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE,
                                   mod_start, len(mod_name))

            # Individual targets after "import"
            imports_str = m.group(2)
            line_start = m.start(2)
            for id_m in _IDENT_RE.finditer(imports_str):
                target = id_m.group(0)
                if target == "as":
                    continue
                idx = text.find(target, line_start)
                if idx == -1 or idx >= length:
                    continue
                indicator = (self._IND_IMPORT_CLASS
                             if target[0].isupper()
                             else self._IND_IMPORT_FUNC)
                self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT,
                                   indicator)
                self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE,
                                   idx, len(target))
                line_start = idx + len(target)

        # import X, Y  → highlight each target
        for m in _PLAIN_IMPORT_RE.finditer(text):
            imports_str = m.group(1)
            line_start = m.start(1)
            for id_m in _IDENT_RE.finditer(imports_str):
                target = id_m.group(0)
                if target == "as":
                    continue
                idx = text.find(target, line_start)
                if idx == -1 or idx >= length:
                    continue
                indicator = (self._IND_IMPORT_CLASS
                             if target[0].isupper()
                             else self._IND_IMPORT_FUNC)
                self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT,
                                   indicator)
                self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE,
                                   idx, len(target))
                line_start = idx + len(target)

        # ── special keywords / dunders ───────────────────────────────
        _KW_RE = re.compile(r"\b(None|True|False|self|cls)\b")
        _DUNDER_RE = re.compile(r"__\w+__")
        for kw_m in _KW_RE.finditer(text):
            self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT,
                               self._IND_SPECIAL_KW)
            self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE,
                               kw_m.start(), kw_m.end() - kw_m.start())
        if self._SPECIAL_DUNDER:
            for du_m in _DUNDER_RE.finditer(text):
                self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT,
                                   self._IND_SPECIAL_KW)
                self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE,
                                   du_m.start(), du_m.end() - du_m.start())

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def load_from_file(self, file_path: str) -> None:
        """Load file contents into the editor.

        Attempts UTF-8 decoding first, then falls back to the system
        default encoding. Sets the editor to read-only when the file on
        disk lacks write permissions.

        Args:
            file_path: Absolute path to the file to load.

        Raises:
            FileNotFoundError: If the file does not exist.
            PermissionError: If the file cannot be read.
            UnicodeDecodeError: If the file cannot be decoded (after
                fallback attempt).
        """
        path_obj = pathlib.Path(file_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Try UTF-8 first, then fall back to system default.
        content = None
        for encoding in ("utf-8", "utf-8-sig", None):
            try:
                kwargs = {"encoding": encoding} if encoding else {}
                with open(file_path, "r", **kwargs) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            # Final fallback: read as bytes, replace errors.
            with open(file_path, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")

        self.current_file_path = file_path
        self.setText(content)
        self.setModified(False)
        self._is_dirty = False
        self.dirty_state_changed.emit(False)

        # Check read-only permissions.
        try:
            if not (path_obj.stat().st_mode & stat.S_IWUSR):
                self.setReadOnly(True)
        except OSError as exc:
            logger.warning(
                "Could not check file permissions for %s: %s", file_path, exc
            )

    def clear_dirty(self) -> None:
        """Reset the editor's modified (dirty) flag."""
        self.setModified(False)
        if self._is_dirty:
            self._is_dirty = False
            self.dirty_state_changed.emit(False)

    def is_dirty(self) -> bool:
        """Return ``True`` if the editor buffer has been modified."""
        return self._is_dirty

    def save(self) -> bool:
        """Save the current buffer to ``current_file_path``.

        If no file path is set, delegates to ``save_as()``.

        Returns:
            ``True`` on success, ``False`` on failure or cancellation.
        """
        if self.current_file_path:
            return self.save_to_file(self.current_file_path)
        return self.save_as()

    def save_as(self) -> bool:
        """Prompt the user for a path and save the buffer.

        Returns:
            ``True`` on success, ``False`` on failure or cancellation.
        """
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            self.current_file_path or "",
            "All Files (*)",
        )
        if not file_path:
            return False
        return self.save_to_file(file_path)

    def save_to_file(self, file_path: str) -> bool:
        """Write the editor buffer to *file_path*.

        Args:
            file_path: Destination path (overwritten if it exists).

        Returns:
            ``True`` on success, ``False`` on any I/O error.
        """
        try:
            content = self.text()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.current_file_path = file_path
            self.setModified(False)
            if self._is_dirty:
                self._is_dirty = False
                self.dirty_state_changed.emit(False)
            return True
        except OSError as exc:
            logger.error("Save failed for %s: %s", file_path, exc)
            return False

    # ------------------------------------------------------------------
    # Clipboard helpers
    # ------------------------------------------------------------------

    def copy_selection_as_plain_text(self) -> None:
        """Copy the current selection to the system clipboard as plain text."""
        selected_text = self.selectedText()
        if selected_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(selected_text)

    # ------------------------------------------------------------------
    # Read-only management
    # ------------------------------------------------------------------

    def make_file_readonly(self) -> None:
        """Toggle the file's read-only permission on disk and in the editor."""
        if not self.current_file_path:
            from editor.widgets.QExitDialog import ConfirmDialog

            dialog = ConfirmDialog(
                parent=self,
                title="No File Path",
                message="This file isn't provided with a path. Save it first.",
                confirm_text="OK",
                cancel_text="CANCEL",
                destructive=False,
            )
            dialog.exec()
            return

        try:
            file_path = pathlib.Path(self.current_file_path)
            current_mode = file_path.stat().st_mode

            if current_mode & stat.S_IWUSR:
                new_mode = current_mode & ~stat.S_IWUSR
                self.setReadOnly(True)
                self._update_readonly_tab_indicator(True)
            else:
                new_mode = current_mode | stat.S_IWUSR | stat.S_IXUSR
                self.setReadOnly(False)
                self._update_readonly_tab_indicator(False)

            file_path.chmod(new_mode)
        except OSError as exc:
            logger.error("Could not change file permissions: %s", exc)
            from editor.widgets.QExitDialog import ConfirmDialog

            dialog = ConfirmDialog(
                parent=self,
                title="Read-Only Error",
                message=f"Could not change file permissions: {exc}",
                confirm_text="OK",
                cancel_text="CANCEL",
                destructive=False,
            )
            dialog.exec()

    def _update_readonly_tab_indicator(self, is_readonly: bool) -> None:
        """Notify the tab bar to show or hide the read-only lock icon."""
        tab_widget = self._parent
        if tab_widget is None:
            return
        tab_bar = tab_widget.tabBar()
        for i in range(tab_widget.count()):
            if tab_widget.widget(i) is self:
                tab_bar.mark_readonly(i, is_readonly)
                break

    # ------------------------------------------------------------------
    # Completion callback
    # ------------------------------------------------------------------

    def _on_completion_selected(self, list_id: int, selection: int) -> None:
        """Handle insertion when an item is selected from the built-in menu."""
        if list_id != 1:
            return

        line, index = self.getCursorPosition()
        current_line_text = self.text(line)[:index]

        import re

        match = re.search(r"(\w+)$", current_line_text)
        word_len = len(match.group(1)) if match else 0

        self.beginUndoAction()
        if word_len > 0:
            self.setSelection(line, index - word_len, line, index)
            self.removeSelectedText()

        self.insert(selection)
        self.endUndoAction()
        self.setCursorPosition(line, index - word_len + len(selection))

    def trigger_autocomplete(self) -> None:
        """Manually trigger the autocomplete popup."""
        self._autocomplete_ext.trigger_autocomplete()

    # ------------------------------------------------------------------
    # Code formatting
    # ------------------------------------------------------------------

    def format_current_file(self) -> None:
        """Pass the buffer through the current provider's formatter.

        All provider errors are caught so that a plugin failure
        never crashes the editor.
        """
        if not self.current_provider:
            return

        try:
            raw_text = self.text()
            formatted_text = self.current_provider.format_source(raw_text)

            if formatted_text and formatted_text != raw_text:
                line, col = self.getCursorPosition()
                first_visible = self.SendScintilla(
                    QsciScintilla.SCI_GETFIRSTVISIBLELINE
                )

                self.beginUndoAction()
                self.setText(formatted_text)
                self.endUndoAction()

                total_lines = self.lines()
                clamped_line = max(0, min(line, total_lines - 1))
                self.setCursorPosition(clamped_line, col)
                self.SendScintilla(
                    QsciScintilla.SCI_SETFIRSTVISIBLELINE, first_visible
                )
        except Exception as exc:
            logger.debug("Format query failed: %s", exc)
