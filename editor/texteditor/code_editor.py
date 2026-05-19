from PyQt6.Qsci import (
    QsciScintilla,
    QsciLexerCMake,
    QsciAPIs,
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtWidgets import (
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QApplication,
)
from PyQt6.QtGui import QFont, QIcon, QColor, QKeyEvent

import ast
import re
import json
import logging

logger = logging.getLogger(__name__)

### LOCAL IMPORTS
from editor.texteditor.ironica_lexer.python_lexer import CustomPythonLexer
from editor.texteditor.ironica_lexer.cpp_lexer import CustomCppLexer
from editor.texteditor.clangd import ClangdClient


class CodeEditor(QsciScintilla):
    def __init__(self, _parent=None, language=None):
        super().__init__(_parent)

        self._lexer = None
        self.keyword_map = {}
        self._parent = _parent
        self.language = language
        self.current_completion_context = None
        self.api = None

        self.document_symbols = {
            "variables": set(),
            "functions": set(),
            "classes": set(),
        }
        self.imported_modules = set()
        self.imported_symbols = set()

        self.font_size = 11
        self._font = QFont("JetBrains Mono", self.font_size)
        self.setFont(self._font)
        try:
            self.setUtf8(True)
        except Exception:
            pass

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

        #####################################
        # Lines and Columns
        #####################################
        self.cursorPositionChanged.connect(self._parent._parent.update_position_status)

        #####################################
        # JEDI
        #####################################
        self.jedi_enabled = True
        self.current_file_path = None
        self._saved_hash: int = 0

        #####################################
        # ClangD
        #####################################
        self.clangd = ClangdClient()

        #####################################
        # Configuration
        #####################################
        self.setObjectName("CodeEditor")
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
        }
        QTabBar::tab:selected {
            color: white; 
        }
        QTabBar::close-button {
            image: url(assets/system/close.png);
            background-color: transparent;
            padding-left: 4px;
            padding-right: 4px;
            border-radius: 2px;
        }
        QTabBar::close-button:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        """)

        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
        self.setEdgeColumn(80)
        self.setEdgeColor(QColor("#444444"))
        self.zoomIn(0)

        ####################################
        # AutoCompletion
        ####################################

        self.completion_popup = QListWidget(self)
        self.completion_popup.setFixedWidth(600)
        self.completion_popup.setWindowFlags(
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self.completion_popup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.completion_popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.completion_popup.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, False
        )
        self.completion_popup.hide()
        self.completion_popup.setStyleSheet("""
            QListWidget {
                background-color: #252526;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                padding: 4px;
                font-family: "JetBrains Mono";
                font-size: 11pt;
            }
            QListWidget::item { padding: 4px 8px; }
            QListWidget::item:selected {
                background-color: #094771;
                color: white;
            }
        """)

        self.completion_popup.itemClicked.connect(self._complete_current_item)

        self._symbol_update_timer = QTimer(self)
        self._symbol_update_timer.setSingleShot(True)
        self._symbol_update_timer.timeout.connect(self.update_document_symbols)

        self._completion_timer = QTimer(self)
        self._completion_timer.setSingleShot(True)
        self._completion_timer.timeout.connect(self.request_completion)

        # Jedi async request tracking
        self._completion_request_id = None
        self._goto_request_id = None
        self._hover_request_id = None

        self._symbol_update_timer.setInterval(400)

        self.completion_icons = {
            "function": QIcon("assets/editor/function.png"),
            "class": QIcon("assets/editor/class.png"),
            "module": QIcon("assets/editor/module.png"),
            "instance": QIcon("assets/editor/variable.png"),
            "statement": QIcon("assets/editor/keyword.png"),
            "param": QIcon("assets/editor/parameter.png"),
            "path": QIcon("assets/editor/path.png"),
            "variable": QIcon("assets/editor/variable.png"),
            "imported_symbol": QIcon("assets/editor/import.png"),
            "keyword": QIcon("assets/editor/keyword.png"),
            "keywords": QIcon("assets/editor/keyword.png"),
            "property": QIcon("assets/editor/property.png"),
            "method": QIcon("assets/editor/method.png"),
            "namespace": QIcon("assets/editor/module.png"),
        }

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

        self.setCaretForegroundColor(QColor("white"))
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#323232"))
        self.setCaretWidth(2)

        self.setBraceMatching(QsciScintilla.BraceMatch.StrictBraceMatch)

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
        self.setLanguage(self.language)

        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsNone)
        self.setAutoCompletionThreshold(0)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(True)

        self.SCN_CHARADDED.connect(self._on_char_added)

        self._hyperlink_indicator = 8
        self._highlight_indicator = 9
        self._hyperlink_target = None
        self._last_word = None
        self._last_line = -1
        self._last_index = -1
        self._hyperlink_debounce_timer = QTimer(self)
        self._hyperlink_debounce_timer.setSingleShot(True)
        self._hyperlink_debounce_timer.setInterval(100)
        self._hyperlink_debounce_timer.timeout.connect(
            self._on_hyperlink_debounce_timeout
        )
        self._pending_hyperline_update = False
        self._setup_hyperlink_indicator()

        ###############################
        # Find and Replace Indicators
        ###############################
        self.setup_find_indicators()

    def setup_find_indicators(self):
        FIND_ALL = 11
        CURRENT = 12
        NO_MATCH = 13

        # all matches
        self.indicatorDefine(QsciScintilla.IndicatorStyle.RoundBoxIndicator, FIND_ALL)
        self.setIndicatorForegroundColor(QColor("#D18616"), FIND_ALL)
        self.setIndicatorDrawUnder(True, FIND_ALL)

        # current active match
        self.indicatorDefine(
            QsciScintilla.IndicatorStyle.ThinCompositionIndicator, CURRENT
        )
        self.setIndicatorForegroundColor(QColor("#FF8C00"), CURRENT)
        self.setIndicatorDrawUnder(False, CURRENT)

        # invalid regex / no match
        self.indicatorDefine(QsciScintilla.IndicatorStyle.SquiggleIndicator, NO_MATCH)
        self.setIndicatorForegroundColor(QColor("#FF5555"), NO_MATCH)
        self.setIndicatorDrawUnder(False, NO_MATCH)

    def _setup_hyperlink_indicator(self):
        self.indicatorDefine(
            QsciScintilla.IndicatorStyle.TextColorIndicator, self._hyperlink_indicator
        )
        self.setIndicatorForegroundColor(QColor("#00558A"), self._hyperlink_indicator)
        self.indicatorDefine(
            QsciScintilla.IndicatorStyle.RoundBoxIndicator, self._highlight_indicator
        )
        self.setIndicatorForegroundColor(QColor("#2D5F2D"), self._highlight_indicator)
        self.setIndicatorDrawUnder(True, self._highlight_indicator)

    def focusInEvent(self, event):
        self._force_clear_hyperlink_state()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._force_clear_hyperlink_state()
        super().focusOutEvent(event)

    def hideEvent(self, event):
        self._force_clear_hyperlink_state()
        super().hideEvent(event)

    def _force_clear_hyperlink_state(self):
        self._hyperlink_debounce_timer.stop()
        self._pending_hyperline_update = False
        self._last_word = None
        self._last_line = -1
        self._last_index = -1
        if self._hyperlink_target:
            try:
                line = self._hyperlink_target["line"]
                start = self._hyperlink_target["start"]
                end = self._hyperlink_target["end"]
                self.clearIndicatorRange(
                    line, start, line, end, self._hyperlink_indicator
                )
            except RuntimeError:
                pass
            self._hyperlink_target = None

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        mods = QApplication.keyboardModifiers()
        has_ctrl = bool(
            mods
            & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
        )
        if has_ctrl:
            self._last_mouse_pos = event.pos()
            self._schedule_hyperlink_update()
        else:
            self._force_clear_hyperlink_state()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            mods = QApplication.keyboardModifiers()
            has_ctrl = bool(
                mods
                & (
                    Qt.KeyboardModifier.ControlModifier
                    | Qt.KeyboardModifier.MetaModifier
                )
            )

            if has_ctrl and self._hyperlink_target:
                # Convert mouse coordinates into Scintilla position
                pos = self.SendScintilla(
                    QsciScintilla.SCI_POSITIONFROMPOINT,
                    event.pos().x(),
                    event.pos().y(),
                )
                line, index = self.lineIndexFromPosition(pos)

                if line >= 0 and self._is_hyperlink_at(line, index):
                    self._hyperlink_debounce_timer.stop()
                    self._pending_hyperline_update = False
                    self._navigate_to_definition()
                    event.accept()
                    return

            # Clear state only if we didn't execute a valid navigation click
            self._force_clear_hyperlink_state()

        super().mousePressEvent(event)

    def _schedule_hyperlink_update(self):
        self._hyperlink_debounce_timer.stop()
        self._pending_hyperline_update = True
        self._hyperlink_debounce_timer.start()

    def _on_hyperlink_debounce_timeout(self):
        self._pending_hyperline_update = False
        self._update_hyperlink_from_cursor()

    def _update_hyperlink_from_cursor(self):
        if (
            self.language != "Python"
            or not self.jedi_enabled
            or not self.current_file_path
        ):
            return

        if not hasattr(self, "_last_mouse_pos") or self._last_mouse_pos is None:
            return

        pos = self.SendScintilla(
            QsciScintilla.SCI_POSITIONFROMPOINT,
            self._last_mouse_pos.x(),
            self._last_mouse_pos.y(),
        )
        line, index = self.lineIndexFromPosition(pos)

        if line < 0 or index < 0:
            self._force_clear_hyperlink_state()
            return

        if line == self._last_line and index == self._last_index:
            return

        text = self.text(line)
        if not text:
            self._force_clear_hyperlink_state()
            # Save coordinates to avoid re-evaluating this empty line on next move
            self._last_line, self._last_index = line, index
            return

        word_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
        word = None
        start = 0
        end = 0

        for match in word_pattern.finditer(text):
            s, e = match.span()
            if s <= index <= e:
                word = match.group()
                start = s
                end = e
                break

        # Save coordinates to minimize thread lookup workloads
        self._last_line = line
        self._last_index = index

        if not word or self._is_python_keyword(word):
            # Clear target indicator without destroying our coordinate cache tracking
            if self._hyperlink_target:
                try:
                    old_line = self._hyperlink_target["line"]
                    old_start = self._hyperlink_target["start"]
                    old_end = self._hyperlink_target["end"]
                    self.clearIndicatorRange(
                        old_line,
                        old_start,
                        old_line,
                        old_end,
                        self._hyperlink_indicator,
                    )
                except RuntimeError:
                    pass
                self._hyperlink_target = None
            self._last_word = None
            return

        if word == self._last_word and start == self._last_index:
            return

        self._last_word = word

        _existing = self._hyperlink_target
        if _existing:
            try:
                self.clearIndicatorRange(
                    _existing["line"],
                    _existing["start"],
                    _existing["line"],
                    _existing["end"],
                    self._hyperlink_indicator,
                )
            except RuntimeError:
                pass

        self._hyperlink_target = {
            "word": word,
            "line": line,
            "start": start,
            "end": end,
            "definition": None,
        }

        self._request_definition_location(word, line, start)

    def _is_python_keyword(self, word):
        keywords = {
            "False",
            "None",
            "True",
            "and",
            "as",
            "assert",
            "async",
            "await",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "try",
            "while",
            "with",
            "yield",
        }
        return word in keywords

    def _request_definition_location(self, word, line, index):
        if self.language != "Python" or not self.jedi_enabled:
            return
        if not self.current_file_path:
            return
        if self._is_python_keyword(word):
            return

        win = self.window()
        if not hasattr(win, "_jedi_worker"):
            return

        source = self.text()
        req_id = win._jedi_request_counter
        win._jedi_request_counter += 1
        win._pending_jedi_requests[req_id] = self
        self._goto_request_id = req_id

        win._jedi_worker.request_goto(
            source, self.current_file_path, line + 1, index, req_id
        )

    def handle_jedi_goto_results(self, definitions):
        win = self.window()
        if hasattr(win, '_pending_jedi_requests'):
            to_remove = [rid for rid, ed in win._pending_jedi_requests.items() if ed is self]
            for rid in to_remove:
                win._pending_jedi_requests.pop(rid, None)
        self._goto_request_id = None
        if not definitions:
            self._on_definition_ready(None)
            return

        for d in definitions:
            file_path = d.get("file")
            if file_path is None:
                continue
            if d.get("in_builtin"):
                continue

            self._on_definition_ready({
                "file": file_path,
                "line": d["line"] - 1 if d["line"] else 0,
                "column": d["column"] or 0,
                "same_file": file_path == self.current_file_path,
            })
            return

        self._on_definition_ready(None)

    def handle_jedi_hover_results(self, items):
        win = self.window()
        if hasattr(win, '_pending_jedi_requests'):
            to_remove = [rid for rid, ed in win._pending_jedi_requests.items() if ed is self]
            for rid in to_remove:
                win._pending_jedi_requests.pop(rid, None)
        self._hover_request_id = None

    def _on_definition_ready(self, definition):
        target = self._hyperlink_target
        if target is None:
            return
        if definition:
            target["definition"] = definition
            try:
                self.fillIndicatorRange(
                    target["line"],
                    target["start"],
                    target["line"],
                    target["end"],
                    self._hyperlink_indicator,
                )
            except RuntimeError:
                pass
        else:
            self._force_clear_hyperlink_state()

    def _clear_hyperlink_highlight(self):
        self._force_clear_hyperlink_state()

    def _is_hyperlink_at(self, line, index):
        if not self._hyperlink_target:
            return False
        target = self._hyperlink_target
        return target["line"] == line and target["start"] <= index <= target["end"]

    def _navigate_to_definition(self):
        if not self._hyperlink_target:
            return

        definition = self._hyperlink_target.get("definition")
        if not definition:
            # If definition hasn't loaded yet, try to wait briefly
            self.window().statusBar().showMessage("Resolving definition...", 2000)
            return

        file_path = definition.get("file")
        line = definition.get("line", 0)

        if not file_path:
            return

        same_file = definition.get("same_file", False)

        self._force_clear_hyperlink_state()

        if same_file:
            self.setCursorPosition(line, 0)
            self.ensureLineVisible(line)
            self.setFocus()
            self._flash_definition_line(line)
        else:
            self._parent.open_file_at_line(file_path, line)

    def _flash_definition_line(self, line):
        line_len = len(self.text(line))
        self.fillIndicatorRange(line, 0, line, line_len, self._highlight_indicator)
        QTimer.singleShot(2000, lambda: self._clear_flash_highlight(line))

    def _clear_flash_highlight(self, line):
        try:
            line_len = len(self.text(line))
            self.clearIndicatorRange(line, 0, line, line_len, self._highlight_indicator)
        except RuntimeError:
            pass

    def _schedule_document_symbol_update(self):
        self._symbol_update_timer.start(150)

    def _schedule_completion(self):
        self._completion_timer.start(25)

    def _get_line_text(self, line):
        lines = self.text().splitlines()
        if 0 <= line < len(lines):
            return lines[line]
        return ""

    def update_document_symbols(self):
        self.imported_modules.clear()
        self.imported_symbols.clear()
        self.document_symbols["variables"] = set()
        self.document_symbols["functions"] = set()
        self.document_symbols["classes"] = set()

        if self.language != "Python":
            return

        source = self.text()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.document_symbols["functions"].add(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                self.document_symbols["functions"].add(node.name)
            elif isinstance(node, ast.ClassDef):
                self.document_symbols["classes"].add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.document_symbols["variables"].add(target.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.imported_modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imported_modules.add(node.module.split(".")[0])
                for alias in node.names:
                    self.imported_symbols.add(alias.name)

    def show_completion_popup(self, items):
        self.completion_popup.clear()

        if not items:
            self.completion_popup.hide()
            return

        for item in items:
            item_type = self.normalize_type(item.get("type", "variable"))

            # enforce consistent structure so UI never degrades unexpectedly
            item.setdefault("label", "")
            item.setdefault("signature", "")
            item.setdefault("doc", "")
            item.setdefault("source", "")
            item["type"] = item_type

            display_text = self.build_completion_display(item)

            list_item = QListWidgetItem("   " + display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)

            # guaranteed fallback icon (prevents empty icon cases)
            icon = self.completion_icons.get(
                item_type, self.completion_icons.get("variable")
            )
            list_item.setIcon(icon)

            self.completion_popup.addItem(list_item)

        self.position_completion_popup()
        self.completion_popup.setCurrentRow(0)
        self.completion_popup.show()

    def _complete_current_item(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict) or "label" not in data:
            return
        self.insert_completion(data["label"])

    def position_completion_popup(self):
        pos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
        x = self.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, pos)
        y = self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, pos)

        global_pos = self.mapToGlobal(QPoint(x, y + 24))
        self.completion_popup.move(global_pos)

    def _on_char_added(self, char_number):
        try:
            ch = chr(char_number)
        except (ValueError, TypeError):
            return

        if ch.isalnum() or ch in "._:":
            self._schedule_completion()
        else:
            self.current_completion_context = None
            self.completion_popup.hide()

    def get_completion_context(self):
        line, index = self.getCursorPosition()
        current_line = self._get_line_text(line)
        text_before_cursor = current_line[:index]

        object_match = re.search(
            r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z0-9_]*)$", text_before_cursor
        )
        if object_match:
            obj, prefix = object_match.groups()
            return {
                "type": "attribute",
                "object": obj,
                "prefix": prefix,
                "line": line,
                "index": index,
            }

        global_match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)$", text_before_cursor)
        if global_match:
            return {
                "type": "global",
                "prefix": global_match.group(1),
                "line": line,
                "index": index,
            }

        m = re.search(r"self\.([A-Za-z_]\w*)$", text_before_cursor)
        if m:
            return {
                "type": "attribute",
                "scope": "class",
                "prefix": m.group(1),
                "object": "self",
                "line": line,
                "index": index,
            }

        cpp_scope_match = re.search(
            r"([A-Za-z_]\w*(?:::\w+)*)::([A-Za-z0-9_]*)$", text_before_cursor
        )
        if cpp_scope_match:
            obj, prefix = cpp_scope_match.groups()
            return {
                "type": "attribute",
                "object": obj,
                "prefix": prefix,
                "line": line,
                "index": index,
            }

        return None

    def request_completion(self):
        context = self.get_completion_context()

        if not context:
            self.current_completion_context = None
            self.completion_popup.hide()
            return

        self.current_completion_context = context
        items = self.get_completion_items(context)
        self.show_completion_popup(items)
        self._request_jedi_completions(context)

    def normalize_type(self, t):
        return {
            "function": "function",
            "method": "method",
            "module": "module",
            "class": "class",
            "instance": "variable",
            "param": "param",
            "keyword": "keyword",
        }.get(t, "variable")

    def score_item(self, item, context):
        base = item.get("score", 0)
        source = item.get("source", "")
        item_type = item.get("type", "")

        if source == "jedi":
            base += 150
        if source == "local":
            base += 20
        if source == "imported":
            base += 15
        if source == "keywords":
            base += 5
        if item_type == "variable":
            base += 5

        return base

    def normalize_jedi_items(self, items):
        seen = set()
        result = []

        for item in items:
            key = (item.get("label"), item.get("type"), item.get("module"))
            if key in seen:
                continue
            seen.add(key)
            result.append(item)

        return result

    def add_item(self, items_by_label, item, context):
        # normalize item immediately so all pipelines behave identically
        item.setdefault("label", "")
        item.setdefault("signature", "")
        item.setdefault("doc", "")
        item.setdefault("source", "")
        item["type"] = self.normalize_type(item.get("type", "variable"))

        label = item["label"]
        existing = items_by_label.get(label)

        if existing is None:
            items_by_label[label] = item
            return

        old_score = self.score_item(existing, context)
        new_score = self.score_item(item, context)

        if new_score > old_score:
            items_by_label[label] = item

    def get_completion_items(self, context):
        prefix = context["prefix"]
        context_type = context.get("type", "global")
        items_by_label = {}

        def add(item):
            self.add_item(items_by_label, item, context)

        if context_type != "attribute":
            for word, word_type in self.keyword_map.items():
                if word.lower().startswith(prefix.lower()):
                    add(
                        {
                            "label": word,
                            "type": word_type,
                            "source": "keywords",
                            "score": 20,
                        }
                    )

        for func_name in self.document_symbols["functions"]:
            if func_name.lower().startswith(prefix.lower()):
                add(
                    {
                        "label": func_name,
                        "type": "function",
                        "source": "local",
                        "score": 80,
                    }
                )

        for class_name in self.document_symbols["classes"]:
            if class_name.lower().startswith(prefix.lower()):
                add(
                    {
                        "label": class_name,
                        "type": "class",
                        "source": "local",
                        "score": 75,
                    }
                )

        for variable_name in self.document_symbols["variables"]:
            if variable_name.lower().startswith(prefix.lower()):
                add(
                    {
                        "label": variable_name,
                        "type": "variable",
                        "source": "local",
                        "score": 70,
                    }
                )

        for module_name in self.imported_modules:
            if module_name.lower().startswith(prefix.lower()):
                add(
                    {
                        "label": module_name,
                        "type": "module",
                        "source": "imported",
                        "score": 72,
                        "signature": f"module {module_name}",
                        "doc": "",
                    }
                )

        for symbol_name in self.imported_symbols:
            if symbol_name.lower().startswith(prefix.lower()):
                add(
                    {
                        "label": symbol_name,
                        "type": "imported_symbol",
                        "source": "imported",
                        "score": 74,
                    }
                )

        items = list(items_by_label.values())
        items.sort(
            key=lambda x: (
                self.score_item(x, context),
                x.get("score", 0),
                x["label"].lower(),
            ),
            reverse=True,
        )
        return items

    def insert_completion(self, completion_text):
        context = self.current_completion_context
        if not context:
            return

        line = context["line"]
        index = context["index"]
        prefix = context["prefix"]

        start_index = max(0, index - len(prefix))

        self.setSelection(line, start_index, line, index)
        self.replaceSelectedText(completion_text)

        self.current_completion_context = None
        self.completion_popup.hide()
        self.setFocus()

    def clean_signature(self, signature):
        if not signature:
            return ""
        return " ".join(signature.split())

    def build_completion_display(self, item):
        label = item.get("label") or ""
        item_type = item.get("type") or ""
        signature = self.clean_signature(item.get("signature", ""))

        if signature.strip() == label.strip():
            signature = ""

        parts = [label]
        if signature:
            parts.append(signature)
        if item_type:
            parts.append(f"[{item_type}]")

        return "    ".join(parts)

    def _request_jedi_completions(self, context):
        if self.language != "Python" or not self.jedi_enabled:
            return
        if not self.current_file_path:
            return

        win = self.window()
        if not hasattr(win, "_jedi_worker"):
            return

        source = self.text()
        line, index = self.getCursorPosition()
        req_id = win._jedi_request_counter
        win._jedi_request_counter += 1
        win._pending_jedi_requests[req_id] = self
        self._completion_request_id = req_id

        win._jedi_worker.request_completion(
            source, self.current_file_path, line + 1, index, req_id
        )

    def handle_jedi_completion_results(self, items):
        if not items:
            return
        if not self.current_completion_context:
            return

        win = self.window()
        if hasattr(win, '_pending_jedi_requests'):
            to_remove = [rid for rid, ed in win._pending_jedi_requests.items() if ed is self]
            for rid in to_remove:
                win._pending_jedi_requests.pop(rid, None)
        self._completion_request_id = None

        context = self.current_completion_context
        prefix = context.get("prefix", "")
        items_by_label = {}

        def add(item):
            self.add_item(items_by_label, item, context)

        for item in items:
            label = item.get("label", "")
            if prefix and not label.lower().startswith(prefix.lower()):
                continue
            add({
                "label": label,
                "type": self.normalize_type(item.get("type", "variable")),
                "source": "jedi",
                "score": 200,
                "signature": label,
                "module": item.get("module", ""),
            })

        if not items_by_label:
            return

        existing_popup_items = []
        if self.completion_popup.isVisible():
            for i in range(self.completion_popup.count()):
                existing_popup_items.append(
                    self.completion_popup.item(i).data(Qt.ItemDataRole.UserRole)
                )
            self.completion_popup.clear()
        else:
            self.show_completion_popup(list(items_by_label.values()))
            return

        merged = {}
        for item in existing_popup_items:
            self.add_item(merged, item, context)
        for item in items_by_label.values():
            self.add_item(merged, item, context)

        merged_items = list(merged.values())
        merged_items.sort(
            key=lambda x: (
                self.score_item(x, context),
                x.get("score", 0),
                x["label"].lower(),
            ),
            reverse=True,
        )
        self.show_completion_popup(merged_items)

    def load_from_file(self, file_path):
        self.current_file_path = file_path

        with open(file_path, "r", encoding="utf-8") as f:
            self.setText(f.read())
        self.clear_dirty()

        if self.language in ("CPP", "C", "C++"):
            self.clangd.did_open(file_path, self.text())

    def set_editor_font(self, font):
        if isinstance(font, QFont):
            self._font = QFont(font)
        else:
            self._font = QFont(str(font), self.font_size)

        self._font.setPointSize(self.font_size)
        self.setFont(self._font)

        if self._lexer:
            self._lexer.setDefaultFont(self._font)

    def set_editor_font_size(self, font_size):
        self.font_size = int(font_size)
        self._font.setPointSize(self.font_size)
        self.setFont(self._font)

        if self._lexer:
            self._lexer.setDefaultFont(self._font)

    def set_wrap_mode(self, enabled=True):
        self.setWrapMode(
            QsciScintilla.WrapMode.WrapWord
            if enabled
            else QsciScintilla.WrapMode.WrapNone
        )

    def keyPressEvent(self, e: QKeyEvent):

        if (
            e.modifiers() & Qt.KeyboardModifier.ControlModifier
            and e.modifiers() & Qt.KeyboardModifier.ShiftModifier
            and e.key() == Qt.Key.Key_T
        ):
            self._parent.add_new_editor()
            return

        if self.completion_popup.isVisible():
            if e.key() == Qt.Key.Key_Down:
                row = self.completion_popup.currentRow()
                if row < self.completion_popup.count() - 1:
                    self.completion_popup.setCurrentRow(row + 1)
                return

            if e.key() == Qt.Key.Key_Up:
                row = self.completion_popup.currentRow()
                if row > 0:
                    self.completion_popup.setCurrentRow(row - 1)
                return

            if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                item = self.completion_popup.currentItem()
                if item:
                    data = item.data(Qt.ItemDataRole.UserRole)
                    if isinstance(data, dict) and "label" in data:
                        self.insert_completion(data["label"])
                return

            if e.key() == Qt.Key.Key_Escape:
                self.current_completion_context = None
                self.completion_popup.hide()
                return

        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            line, index = self.getCursorPosition()
            current_line_text = self._get_line_text(line)

            base_indent = ""
            for ch in current_line_text:
                if ch in (" ", "\t"):
                    base_indent += ch
                else:
                    break

            if current_line_text.rstrip().endswith((":", "{", "(")):
                indent = base_indent + (" " * self._indentation_spacing)
            else:
                indent = base_indent

            self.beginUndoAction()
            self.insert("\n" + indent)
            self.endUndoAction()

            self.setCursorPosition(line + 1, len(indent))
            return

        super().keyPressEvent(e)

        if e.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self._schedule_completion()
            self._schedule_document_symbol_update()

    def setLanguage(self, lang: str):
        if not lang:
            self._lexer = None
            self.setLexer(None)
            self.keyword_map = {}
            if self.api is not None and hasattr(self.api, "clear"):
                self.api.clear()
            self.api = None
            self.apply_theme()
            return

        if lang == "Python":
            self._lexer = self.load_language_keywords("Python")
            if self._lexer:
                self._lexer.setDefaultFont(self._font)
                self.setLexer(self._lexer)
                self.apply_theme()
                self._schedule_document_symbol_update()

        elif lang in ("CPP", "C", "C++"):
            self._lexer = self.load_language_keywords("CPP")
            if self._lexer:
                self._lexer.setDefaultFont(self._font)
                self.setLexer(self._lexer)
                self.apply_theme()
                self._schedule_document_symbol_update()

        elif lang == "CMAKE":
            self._lexer = QsciLexerCMake()
            self._lexer.setDefaultFont(self._font)
            self.setLexer(self._lexer)
            self.apply_theme()
            self._schedule_document_symbol_update()

        else:
            self._lexer = None
            self.setLexer(None)
            self.keyword_map = {}
            if self.api is not None and hasattr(self.api, "clear"):
                self.api.clear()
            self.api = None
            self.apply_theme()
            return

    def apply_theme(self):
        self.setPaper(QColor("#1E1E1E"))
        self.setColor(QColor("#D4D4D4"))
        self.setSelectionBackgroundColor(QColor("#264F78"))
        self.setSelectionForegroundColor(QColor("#FFFFFF"))
        self.setCaretForegroundColor(QColor("#FFFFFF"))

        self.setMarginsBackgroundColor(QColor("#1E1E1E"))
        self.setMarginsForegroundColor(QColor("#D4D4D4"))

        if self._lexer:
            self._lexer.setDefaultColor(QColor("#D4D4D4"))
            for style in range(128):
                self._lexer.setPaper(QColor("#1E1E1E"), style)

    def load_language_keywords(self, lang: str):
        lang_key = "CPP" if lang in ("C", "CPP", "C++") else lang

        configs = {
            "Python": ("editor/texteditor/keywords/python.json", CustomPythonLexer),
            "CPP": ("editor/texteditor/keywords/cpp.json", CustomCppLexer),
        }

        if lang_key not in configs:
            return None

        path, lexer_class = configs[lang_key]

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            self.keyword_map = {}
            return None

        classification_map = {}
        for category in ["words", "types", "iterators", "exceptions"]:
            items = data.get(category, {})
            if isinstance(items, dict):
                classification_map.update(items)

        lexer = lexer_class(self, data)

        if self.api is not None and hasattr(self.api, "clear"):
            self.api.clear()

        self.api = QsciAPIs(lexer)
        for word in classification_map.keys():
            self.api.add(word)
        self.api.prepare()

        self.keyword_map = classification_map
        return lexer

    def clear_dirty(self):
        self._saved_hash = hash(self.text())

    def is_dirty(self):
        return self._saved_hash != hash(self.text())

    def save(self):
        if self.current_file_path:
            return self.save_to_file(self.current_file_path)
        return self.save_as()

    def save_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            self.current_file_path or "",
            "All Files (*)",
        )
        if not file_path:
            return False
        return self.save_to_file(file_path)

    def save_to_file(self, file_path):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.text())
            self.current_file_path = file_path
            self.clear_dirty()
            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    def copy_selection_as_plain_text(self):
        selected_text = self.selectedText()
        if selected_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(selected_text)
