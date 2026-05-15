"""
(C) COPYRIGHT - 2026 Excellent Technologies Cooperation - All Rights Reserved
Developed and Maintained Mainly by DreamStudio Maintainers and Contributors, and
Supervised by Excellent Technologies Co.

A Custom editor tab changer and code editor for DreamStudio.
"""

# Written by Bahaa Nofal

from PyQt6.Qsci import (
    QsciScintilla,
    QsciLexerCMake,
    QsciAPIs,
)
from PyQt6.QtCore import Qt, QSize, QTimer, QRect, QEvent, QPoint
from PyQt6.QtWidgets import (
    QStyle,
    QLabel,
    QTabBar,
    QWidget,
    QSplitter,
    QTabWidget,
    QFileDialog,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QPlainTextEdit,
    QStyleOptionTab,
    QListWidgetItem,
    QGraphicsOpacityEffect,
)
from PyQt6.QtGui import (
    QPen,
    QFont,
    QIcon,
    QColor,
    QPainter,
    QPalette,
    QKeyEvent,
    QPainterPath,
)

from PyQt6.QtWebEngineWidgets import QWebEngineView

import os
import re
import sys
import json
import jedi
import pathlib
import markdown

from rapidfuzz import fuzz

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


class DreamStudioIDETabBar(QTabBar):
    def __init__(self, _parent=None):
        super().__init__(_parent)
        self.setDrawBase(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setUsesScrollButtons(True)
        self._parent = _parent

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

        self._hover_index = -1
        self._is_syncing = False
        self.currentChanged.connect(self._on_current_changed)
        self.tabBarDoubleClicked.connect(
            self.on_double_click, Qt.ConnectionType.UniqueConnection
        )

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        index = self.tabAt(event.position().toPoint())
        if index != self._hover_index:
            self._hover_index = index
            self._sync_close_buttons()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hover_index = -1
        self._sync_close_buttons()

    def _sync_close_buttons(self):
        if getattr(self, "_is_syncing", False) or not self.tabsClosable():
            return

        self._is_syncing = True
        current_idx = self.currentIndex()

        for i in range(self.count()):
            button = self.tabButton(i, QTabBar.ButtonPosition.RightSide)
            if not button:
                continue

            is_visible = i == current_idx or i == self._hover_index

            effect = button.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(button)
                button.setGraphicsEffect(effect)

            effect.setOpacity(1.0 if is_visible else 0.0)
            button.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, not is_visible
            )

            rect = self.tabRect(i)
            if not rect.isNull():
                btn_w = 18
                btn_h = 18

                margin_right = 8
                x = rect.right() - btn_w - margin_right
                y = rect.center().y() - (btn_h // 2)

                new_geo = QRect(x, y, btn_w, btn_h)

                if button.geometry() != new_geo:
                    button.setGeometry(new_geo)

                button.raise_()

        self._is_syncing = False
        self._parent._parent.update_editor_visibility()

    def _on_current_changed(self):
        QTimer.singleShot(0, self._sync_close_buttons)

    def tabLayoutChange(self):
        super().tabLayoutChange()
        self._on_current_changed()

    def on_currentChanged(self, index):
        super().currentChanged(index)
        self._on_current_changed()

    def tabInserted(self, index):
        super().tabInserted(index)
        self._sync_close_buttons()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self._sync_close_buttons()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
            QEvent.Type.PaletteChange,
        ):
            self._sync_close_buttons()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        selected_index = self.currentIndex()

        # Define Colors
        selected_bg = QColor("#25324D")
        hover_bg = QColor("#2D2D2D")
        inactive_bg = QColor("#1E1E1E")
        border_color = QColor("#35538F")
        hover_border_color = QColor("#3C3F41")
        inactive_border_color = QColor("#1E1E1E")

        for i in range(self.count()):
            if i == selected_index:
                continue

            option = QStyleOptionTab()
            self.initStyleOption(option, i)
            is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

            bg = hover_bg if is_hovered else inactive_bg
            border = hover_border_color if is_hovered else inactive_border_color

            self._draw_tab(painter, i, bg, border, False, option)

        if selected_index >= 0:
            option = QStyleOptionTab()
            self.initStyleOption(option, selected_index)
            self._draw_tab(
                painter, selected_index, selected_bg, border_color, True, option
            )

    def _draw_tab(self, painter, index, bg_color, border_color, selected, option):
        rect = self.tabRect(index)
        if rect.isNull():
            return

        r = rect.adjusted(1, 6, -1, -6)
        radius = 5

        # SHAPE LOGIC
        path = QPainterPath()
        path.moveTo(r.left(), r.bottom() - radius)
        path.lineTo(r.left(), r.top() + radius)
        path.quadTo(r.left(), r.top(), r.left() + radius, r.top())
        path.lineTo(r.right() - radius, r.top())
        path.quadTo(r.right(), r.top(), r.right(), r.top() + radius)
        path.lineTo(r.right(), r.bottom() - radius)
        path.quadTo(r.right(), r.bottom(), r.right() - radius, r.bottom())
        path.lineTo(r.left() + radius, r.bottom())
        path.quadTo(r.left(), r.bottom(), r.left(), r.bottom() - radius)
        path.closeSubpath()

        painter.save()
        painter.fillPath(path, bg_color)

        pen = QPen(border_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)

        if selected:
            painter.drawLine(
                r.left() + radius,
                r.top(),
                r.right() - radius,
                r.top(),
            )

        if selected:
            option.palette.setColor(QPalette.ColorRole.WindowText, QColor("white"))
        else:
            option.palette.setColor(QPalette.ColorRole.WindowText, QColor("#AFB1B3"))

        right_reserve = 32 if self.tabsClosable() else 10
        option.rect = r.adjusted(10, 0, -right_reserve, 0)

        option.state &= ~QStyle.StateFlag.State_MouseOver
        option.state &= ~QStyle.StateFlag.State_HasFocus

        self.style().drawControl(
            QStyle.ControlElement.CE_TabBarTabLabel,
            option,
            painter,
            self,
        )

        painter.restore()

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        # +25px width compensates for the custom close button space
        # +12px height creates extra "breathing room" above and below the tabs
        return QSize(size.width() + 25, size.height() + 12)

    def on_double_click(self, index):
        print("double click triggered")
        if index == -1:
            self._parent.add_new_editor()


class DreamTabbedEditor(QTabWidget):
    def __init__(self, _parent):
        super().__init__(_parent)

        self.setTabBar(DreamStudioIDETabBar(self))
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self._parent = _parent
        self.currentDirectory = self._parent.currentDirectory
        self.opened_files = {}

        self.tab_counter = self.count()

        self.setStyleSheet("""
        QTabBar::tab {
            padding: 6px 12px;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            color: white; 
        }

        QTabBar::close-button {
            image: url(assets/system/close.png);
            background: transparent;
        }""")

        self.tabCloseRequested.connect(self.close_editor)

    def add_new_editor(self, file_name=None, content="", language=None, file_path=None):
        key = self.resolve_key(file_path) if file_path else None
        viewer_type = self.resolve_viewer_type(file_path) if file_path else "code"

        if key and key in self.opened_files:
            index = self.opened_files[key]
            if index != -1:
                self.setCurrentIndex(index)
                return self.widget(index)
            else:
                del self.opened_files[key]

        if viewer_type == "code":
            new_editor = CodeEditor(self, language=language)
            if file_path:
                new_editor.load_from_file(file_path)
            else:
                new_editor.setText(content)

        elif viewer_type == "image":
            try:
                from ComposerStudio.AssetsEditor.ImageViewer import ImageViewer

                new_editor = ImageViewer(self)

                if file_path:
                    new_editor.load_image(file_path)
                else:
                    new_editor = FallBack(self)

            except ImportError:
                new_editor = FallBack(self)

        elif viewer_type == "pdf":
            try:
                from ComposerStudio.PDFViewer.PDFViewer import PDFViewer

                new_editor = PDFViewer(self)

                if file_path:
                    new_editor.load_pdf(file_path)
                else:
                    new_editor = FallBack(self)

            except ImportError:
                new_editor = FallBack(self)

        elif viewer_type == "metadata":
            try:
                new_editor = MarkdownViewer()
                new_editor.load_file(file_path)
            except Exception:
                new_editor = FallBack(self)

        else:
            if file_path:
                try:
                    new_editor = CodeEditor(self, language=language)
                    new_editor.load_from_file(file_path)

                except (UnicodeDecodeError, OSError, ValueError):
                    new_editor = FallBack(self)
                    new_editor.setText(content)

            else:
                new_editor = CodeEditor(self, language=language)
                new_editor.setText(content)

        if not key:
            key = f"__untitled_{id(new_editor)}"

        if file_name is None:
            file_name = f"untitled - {self.count()}"

        index = self.addTab(new_editor, file_name)
        self.setCurrentIndex(index)

        new_editor.file_path = file_path
        new_editor.file_key = key
        new_editor.viewer_type = viewer_type

        self.opened_files[key] = index

        self.setFocus()
        self._parent.update_editor_visibility()

        print(self.opened_files)

        return new_editor

    def close_editor(self, index):
        editor = self.widget(index)
        if not editor:
            return
        if hasattr(editor, "textChanged"):
            try:
                editor.textChanged.disconnect()
            except (TypeError, RuntimeError):
                pass

        key = getattr(editor, "file_key", None)
        if key and key in self.opened_files:
            del self.opened_files[key]

        self.removeTab(index)
        editor.deleteLater()

        for k in list(self.opened_files.keys()):
            if self.opened_files[k] > index:
                self.opened_files[k] -= 1

        print(self.opened_files)

    def close_tab(self):
        index = self.currentIndex()
        if index == -1:
            return

        self.close_editor(index)
        self._parent.update_editor_visibility()

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            self.currentDirectory,
            "All Supported Files (*.py *.pyw *.pyi *.c *.h *.cpp *.cc *.cxx *.hpp *.hh *.hxx);;"
            "Python Files (*.py *.pyw *.pyi);;"
            "C Files (*.c *.h);;"
            "C++ Files (*.cpp *.cc *.cxx *.hpp *.hh *.hxx);;"
            "Text/Config Files (*.txt *.json *.xml *.yaml *.yml);;"
            "All Files (*)",
        )

        if not file_path:
            return

        file_name = pathlib.Path(file_path).name
        file_extn = pathlib.Path(file_path).suffix

        try:
            self.add_new_editor(
                file_name=file_name,
                file_path=file_path,
                language=self.set_language(file_extn),
            )
        except Exception as e:
            print("Open file failed:", e)

    def resolve_viewer_type(self, file_path):
        ext = pathlib.Path(file_path).suffix.lower()

        if ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
            return "image"

        if ext in [".pdf"]:
            return "pdf"

        if ext in [
            ".txt",
            ".py",
            ".pyi",
            ".pyw",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".cxx",
            ".hh",
            ".cc",
            ".hxx",
            ".json",
        ]:
            return "code"

        if ext == ".md":
            return "metadata"

        return "default"

    def set_language(self, lang):
        match lang:
            case ".py" | ".pyi" | ".pyw":
                return "Python"
            case ".c" | ".h" | ".hpp" | ".cpp" | ".cxx" | ".cc" | ".hh" | ".hxx":
                return "CPP"
            case ".txt":
                return None
            case ".md":
                return "METADATA"
            case _:
                return None

    def open_new_workspace(self, path):
        self._parent.currentDirectory = path

    def resolve_key(self, file_path):
        if not file_path:
            return None
        return os.path.normcase(os.path.normpath(file_path))


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
        # JEDI
        #####################################
        self.jedi_enabled = True
        self.current_file_path = None

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

        ##### EDGES FOR TEXTEDITOR

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

            QListWidget::item {
                padding: 4px 8px;
            }

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

        # Caret
        self.setCaretForegroundColor(QColor("white"))
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#323232"))
        self.setCaretWidth(2)

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
        self.setLanguage(self.language)

        ### Enable AutoCompletion:
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsNone)
        self.setAutoCompletionThreshold(0)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(True)

        self.SCN_CHARADDED.connect(self._on_char_added)

        # # KEYBINDINGS
        # self.new_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        # self.new_tab_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        # self.new_tab_shortcut.activated.connect(self.hello)

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
        if len(self.text()) < 5:
            return
        self.imported_modules.clear()
        self.imported_symbols.clear()

        text = self.text()
        class_body_pattern = r"class\s+([A-Za-z_]\w*).*?:((?:\n[ \t]+.*)+)"

        variables = set()
        functions = set()
        classes = set()

        for m in re.finditer(r"\bdef\s+([A-Za-z_]\w*)", text):
            functions.add(m.group(1))

        for m in re.finditer(r"\bclass\s+([A-Za-z_]\w*)", text):
            classes.add(m.group(1))

        for m in re.finditer(r"\b([A-Za-z_]\w*)\s*=", text):
            name = m.group(1)
            if name not in self.keyword_map:
                variables.add(name)

        for m in re.finditer(r"import\s+([A-Za-z_]\w*)", text):
            self.imported_modules.add(m.group(1))

        for m in re.finditer(r"from\s+([A-Za-z_]\w+)\s+import\s+([A-Za-z_,\s]+)", text):
            module = m.group(1)
            symbols = [s.strip() for s in m.group(2).split(",")]
            self.imported_modules.add(module)
            self.imported_symbols.update(symbols)

        for match in re.finditer(class_body_pattern, text):
            class_block = match.group(2)

            for m in re.finditer(r"def\s+([A-Za-z_]\w*)", class_block):
                functions.add(m.group(1))

            for m in re.finditer(r"self\.([A-Za-z_]\w*)", class_block):
                variables.add(m.group(1))

        self.document_symbols["variables"] = variables
        self.document_symbols["functions"] = functions
        self.document_symbols["classes"] = classes

    def show_completion_popup(self, items):
        self.completion_popup.clear()

        if not items:
            self.completion_popup.hide()
            return

        for item in items:
            item_type = item.get("type", "")
            display_text = self.build_completion_display(item)
            list_item = QListWidgetItem("   " + display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.completion_popup.addItem(list_item)

            icon = self.completion_icons.get(item_type)

            if icon:
                list_item.setIcon(icon)

        self.position_completion_popup()
        self.completion_popup.setCurrentRow(0)
        self.completion_popup.show()

    def _complete_current_item(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        self.insert_completion(data["label"])

    def position_completion_popup(self):
        pos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
        x = self.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, pos)
        y = self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, pos)

        global_pos = self.mapToGlobal(QPoint(x, y + 24))
        self.completion_popup.move(global_pos)

    def _on_char_added(self, char_number):
        ch = chr(char_number)

        if ch.isalnum() or ch in "._":
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

        if item["source"] == "jedi":
            if context.get("type") == "attribute":
                base += 500
            else:
                base += 150
        if item["source"] == "local":
            base += 20
        if item["source"] == "imported":
            base += 15
        if item["source"] == "keywords":
            base += 5
        if context.get("scope") == "class" and item["type"] == "function":
            base += 10
        if item["type"] == "variable":
            base += 5

        return base

    def normalize_jedi_items(self, items):
        seen = set()
        result = []

        for item in items:
            key = (
                item.get("label"),
                item.get("type"),
                item.get("module"),
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(item)

        return result

    def get_completion_items(self, context):
        prefix = context["prefix"]
        context_type = context.get("type")
        items_by_label = {}

        def add_item(item):
            label = item["label"]

            existing = items_by_label.get(label)

            if existing is None:
                items_by_label[label] = item
                return

            old_score = self.score_item(existing, context)
            new_score = self.score_item(item, context)

            if new_score > old_score:
                items_by_label[label] = item

        ############################################################
        # JEDI COMPLETIONS
        ############################################################
        jedi_items = self.get_jedi_completions(context)
        for item in jedi_items:
            add_item(item)

        if context_type == "attribute":
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

        ############################################################
        # GLOBAL CONTEXT
        ############################################################
        if context_type != "attribute":
            for word, word_type in self.keyword_map.items():
                if not word.lower().startswith(prefix.lower()):
                    continue
                add_item(
                    {
                        "label": word,
                        "type": word_type,
                        "source": "keywords",
                        "score": 20,
                    }
                )

        ############################################################
        # FUNCTIONS
        ############################################################
        for func_name in self.document_symbols["functions"]:
            if not func_name.lower().startswith(prefix.lower()):
                continue
            add_item(
                {
                    "label": func_name,
                    "type": "function",
                    "source": "local",
                    "score": 80,
                }
            )

        ############################################################
        # CLASSES
        ############################################################
        for class_name in self.document_symbols["classes"]:
            if not class_name.lower().startswith(prefix.lower()):
                continue
            add_item(
                {
                    "label": class_name,
                    "type": "class",
                    "source": "local",
                    "score": 75,
                }
            )

        ############################################################
        # VARIABLES
        ############################################################
        for variable_name in self.document_symbols["variables"]:
            if not variable_name.lower().startswith(prefix.lower()):
                continue
            add_item(
                {
                    "label": variable_name,
                    "type": "variable",
                    "source": "local",
                    "score": 70,
                }
            )

        ############################################################
        # IMPORTED MODULES
        ############################################################
        for module_name in self.imported_modules:
            if not module_name.lower().startswith(prefix.lower()):
                continue
            add_item(
                {
                    "label": module_name,
                    "type": "module",
                    "source": "imported",
                    "score": 72,
                }
            )

        ############################################################
        # IMPORTED SYMBOLS
        ############################################################
        for symbol_name in self.imported_symbols:
            if not symbol_name.lower().startswith(prefix.lower()):
                continue
            add_item(
                {
                    "label": symbol_name,
                    "type": "imported_symbol",
                    "source": "imported",
                    "score": 74,
                }
            )

        ############################################################
        # FINAL SORT
        ############################################################
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

    def get_jedi_completions(self, context):
        if self.language != "Python" or not self.jedi_enabled:
            return []

        try:
            prefix = context.get("prefix", "")
            source = self.text()
            line, index = self.getCursorPosition()

            script = jedi.Script(code=source, path=self.current_file_path)
            completions = script.complete(line + 1, index)

            items = []
            seen = set()

            for completion in completions:
                name = completion.name or ""

                if prefix and not name.lower().startswith(prefix.lower()):
                    continue

                key = (name, completion.type)
                if key in seen:
                    continue
                seen.add(key)

                try:
                    ctype = self.normalize_type(completion.type)
                except Exception:
                    ctype = "variable"

                try:
                    description = completion.description
                except Exception:
                    description = ""

                try:
                    module_name = completion.module_name
                except Exception:
                    module_name = ""

                try:
                    signatures = completion.get_signatures()
                    signature_text = signatures[0].to_string() if signatures else name
                except Exception:
                    signature_text = name

                try:
                    doc = completion.docstring()
                except Exception:
                    doc = ""

                items.append(
                    {
                        "label": name,
                        "type": ctype,
                        "source": "jedi",
                        "score": 200,
                        "description": description,
                        "signature": signature_text,
                        "module": module_name,
                        "doc": doc,
                    }
                )

            return items

        except Exception as e:
            print("Jedi completion error:", e)
            return []

    def load_from_file(self, file_path):
        self.current_file_path = file_path

        with open(file_path, "r", encoding="utf-8") as f:
            self.setText(f.read())

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

            elif e.key() == Qt.Key.Key_Up:
                row = self.completion_popup.currentRow()
                if row > 0:
                    self.completion_popup.setCurrentRow(row - 1)
                return

            elif e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                item = self.completion_popup.currentItem()
                if item:
                    data = item.data(Qt.ItemDataRole.UserRole)
                    self.insert_completion(data["label"])
                return

            elif e.key() == Qt.Key.Key_Escape:
                self.current_completion_context = None
                self.completion_popup.hide()
                return

        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            line, index = self.getCursorPosition()
            current_line_text = self._get_line_text(line)
            stripped = current_line_text.rstrip()

            base_indent = ""
            for char in current_line_text:
                if char in (" ", "\t"):
                    base_indent += char
                else:
                    break

            if stripped.endswith((":", "{", "(")):
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

        if not self._lexer:
            return

        self._lexer.setDefaultColor(QColor("#D4D4D4"))

        for style in range(128):
            self._lexer.setPaper(QColor("#1E1E1E"), style)

    def load_language_keywords(self, lang: str):
        configs = {
            "Python": ("editor/texteditor/keywords/python.json", CustomPythonLexer),
            "CPP": ("editor/texteditor/keywords/cpp.json", CustomCppLexer),
        }

        if lang not in configs:
            return None

        path, lexer_class = configs[lang]

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading language file {path}: {e}")
            return None

        classification_map = {}
        # Using .get() with empty dict handles missing keys in JSON gracefully
        for category in ["words", "types", "iterators", "exceptions"]:
            items = data.get(category, {})
            classification_map.update(items)

        lexer = lexer_class(self, data)

        if hasattr(self, "api") and self.api is not None and hasattr(self.api, "clear"):
            self.api.clear()

        self.api = QsciAPIs(lexer)
        for word in classification_map.keys():
            self.api.add(word)
        self.api.prepare()

        self.keyword_map = classification_map
        return lexer


class MarkdownViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Markdown Editor Engine")
        self.setMinimumSize(900, 600)

        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
        """)

        # ---- Layout ----
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # ---- Editor ----
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("# Markdown...\nStart typing here")

        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1f22;
                color: #dcdcdc;
                border: 1px solid #3c3f41;
                border-radius: 6px;
                padding: 10px;
                font-family: JetBrains Mono;
                font-size: 14px;
                selection-background-color: #264f78;
                selection-color: #ffffff;
            }

            QScrollBar:vertical {
                background: #2b2b2b;
                width: 10px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 4px;
                min-height: 25px;
            }

            QScrollBar::handle:vertical:hover {
                background: #6a6a6a;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # ---- Preview ----
        self.preview = QWebEngineView()
        self.preview.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.preview.setHtml(self._base_html())

        # ---- Splitter ----
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(6)

        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3c3f41;
            }

            QSplitter::handle:hover {
                background-color: #4a4d50;
            }
        """)

        layout.addWidget(splitter)

        # ---- Debounce ----
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(300)

        self.editor.textChanged.connect(self.schedule_updates)
        self.timer.timeout.connect(self.update_preview)

        self.update_preview()

    def _base_html(self):
        return """
        <html>
        <head>
            <style>
                :root {
                    --bg: #1e1f22;
                    --panel: #26292c;
                    --text: #d4d4d4;
                    --muted: #9aa0a6;
                    --accent: #4fc1ff;
                    --border: #3c3f41;
                }

                body {
                    font-family: JetBrains Mono, Consolas, monospace;
                    background-color: var(--bg);
                    color: var(--text);
                    padding: 22px;
                    margin: 0;
                    line-height: 1.6;
                    font-size: 14px;
                }

                h1, h2, h3 {
                    color: #ffffff;
                    border-bottom: 1px solid var(--border);
                    padding-bottom: 6px;
                    margin-top: 18px;
                }

                h1 { font-size: 24px; }
                h2 { font-size: 20px; }
                h3 { font-size: 17px; }

                p {
                    color: var(--text);
                }

                code {
                    background: #2b2d30;
                    color: #dcdcaa;
                    padding: 2px 6px;
                    border-radius: 4px;
                }

                pre {
                    background: var(--panel);
                    border: 1px solid var(--border);
                    padding: 12px;
                    border-radius: 8px;
                    overflow-x: auto;
                }

                pre code {
                    background: none;
                }

                blockquote {
                    border-left: 4px solid var(--accent);
                    padding: 8px 12px;
                    margin: 12px 0;
                    color: var(--muted);
                    background: #222427;
                }

                a {
                    color: var(--accent);
                    text-decoration: none;
                }

                a:hover {
                    text-decoration: underline;
                }

                /* Scrollbar */
                ::-webkit-scrollbar {
                    width: 10px;
                    height: 10px;
                }

                ::-webkit-scrollbar-track {
                    background: var(--bg);
                }

                ::-webkit-scrollbar-thumb {
                    background: #4a4d52;
                    border-radius: 6px;
                }

                ::-webkit-scrollbar-thumb:hover {
                    background: #5a5d62;
                }
            </style>
        </head>
        <body>
            <div id="content"></div>
        </body>
        </html>
        """

    def load_file(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self.update_preview()
        except Exception as e:
            self.editor.setPlainText(f"Error loading file:\n{e}")

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Markdown File", "", "Markdown Files (*.md);;All Files (*)"
        )
        if path:
            self.load_file(path)

    def schedule_updates(self):
        self.timer.start()

    def update_preview(self):
        text = self.editor.toPlainText()

        html = markdown.markdown(text, extensions=["fenced_code", "tables", "toc"])

        html = html.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

        js = f"""
            document.getElementById('content').innerHTML = '{html}';
        """

        self.preview.page().runJavaScript(js)


class FallBack(QWidget):
    """A fallback frame widget if the file to open is not supported."""

    def __init__(self, _parent=None):
        super().__init__(_parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.setSpacing(12)

        self.icon_label = QLabel()
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
        self.icon_label.setPixmap(icon.pixmap(64, 64))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.page_label = QLabel(
            "This file cannot be opened because it uses unsupported data types."
        )
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setWordWrap(True)
        self.page_label.setMinimumSize(400, 100)

        self.action_button = QPushButton("Open Anyway")
        self.action_button.setFixedWidth(160)

        self._layout.addWidget(self.icon_label)
        self._layout.addWidget(self.page_label)
        self._layout.addWidget(
            self.action_button, alignment=Qt.AlignmentFlag.AlignCenter
        )

    def setText(self, text: str):
        self.page_label.setText(text)
