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
    QApplication,
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
    QShortcut,
    QKeySequence,
    QFontInfo,
)

from PyQt6.QtWebEngineWidgets import QWebEngineView

import os
import re
import json
import jedi
import math
import logging
import pathlib
import markdown

logger = logging.getLogger(__name__)

### LOCAL IMPORTS
from editor.texteditor.ironica_lexer.python_lexer import CustomPythonLexer
from editor.texteditor.ironica_lexer.json_lexer import CustomJSONLexer
from editor.texteditor.ironica_lexer.cpp_lexer import CustomCppLexer
from editor.texteditor.clangd import ClangdClient

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

        ##### Here we added status bar syncronization to alert changes
        self._parent.update_position_status()
        self._parent.return_file_info()

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
        logger.debug("double click triggered")
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
        self._save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self._save_shortcut.activated.connect(self.save_current_file)
        self._save_as_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self._save_as_shortcut.activated.connect(self.save_current_file_as)
        self._save_all_shortcut = QShortcut(QKeySequence("Ctrl+Alt+S"), self)
        self._save_all_shortcut.activated.connect(self.save_all_files)

    def open_configurations_json(self):
        key = "json_user_configs"
        new_editor = EditConfigurationsTab()
        new_editor.run_text()

        index = self.addTab(new_editor, "configurations")
        self.setCurrentIndex(index)

        new_editor.file_path = ""
        new_editor.file_key = None
        new_editor.viewer_type = "json_metadata_configs_editor"
        self.opened_files[key] = index

        self.setFocus()
        self._parent.update_editor_visibility()

        logger.debug(f"Opened files: {self.opened_files}")
        return new_editor

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

        logger.debug(f"Opened files: {self.opened_files}")

        self._parent.update_position_status()
        self.return_file_info()

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

        logger.debug(f"Opened files after close: {self.opened_files}")

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
            logger.error(f"Open file failed: {e}")

    def open_file_at_line(self, file_path, line):
        file_name = pathlib.Path(file_path).name
        file_extn = pathlib.Path(file_path).suffix

        try:
            editor = self.add_new_editor(
                file_name=file_name,
                file_path=file_path,
                language=self.set_language(file_extn),
            )
            if editor and hasattr(editor, "setCursorPosition"):
                editor.setCursorPosition(line, 0)
                editor.ensureLineVisible(line)
                QTimer.singleShot(0, lambda: self._focus_and_flash(editor, line))
        except Exception as e:
            logger.error(f"Open file at line failed: {e}")

    def _focus_and_flash(self, editor, line):
        if hasattr(editor, "setFocus"):
            editor.setFocus()
        if hasattr(editor, "_flash_definition_line"):
            editor._flash_definition_line(line)

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

    def save_current_file(self):
        editor = self.currentWidget()
        if editor and hasattr(editor, "save"):
            editor.save()

    def save_current_file_as(self):
        editor = self.currentWidget()
        if editor and hasattr(editor, "save_as"):
            editor.save_as()

    def save_all_files(self):
        for i in range(self.count()):
            editor = self.widget(i)
            if editor and hasattr(editor, "save") and editor.current_file_path:
                editor.save()

    def return_file_info(self):
        editor = self._parent._get_current_editor()
        text = editor.text()

        if not text:
            return "LF", 4  # Default fallback for empty editors

        # ---------- Line Endings ----------
        if "\r\n" in text:
            line_ending = "CRLF"
        elif "\r" in text:
            line_ending = "CR"
        else:
            line_ending = "LF"

        indents = set()
        uses_tabs = False
        for line in text.splitlines():
            if not line.strip():
                continue

            if line.startswith("\t"):
                uses_tabs = True
                break

            match = re.match(r"^( +)", line)
            if match:
                indents.add(len(match.group(1)))

        if uses_tabs:
            indentation_width = "Tabs"
        elif indents:
            indentation_width = min(indents)
        else:
            indentation_width = 4

        self._parent.status_bar.EOL.setText(f"{line_ending}")
        self._parent.status_bar.spacing_options.setText(
            f"Indent {indentation_width} Spaces"
        )


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
        self._is_dirty = False
        self.textChanged.connect(self._mark_dirty)

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
            self._schedule_hyperlink_update()
        else:
            self._force_clear_hyperlink_state()

        mods = QApplication.keyboardModifiers()
        has_ctrl = bool(
            mods
            & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
        )

        if has_ctrl:
            self._last_mouse_pos = (
                event.pos()
            )  # Cache mouse coordinate point safely once
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

        # Only ask Jedi for tracking data if we moved over a distinct new token string
        definition = self._get_definition_location(word, line, start)
        if definition:
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

            self._hyperlink_target = {
                "word": word,
                "line": line,
                "start": start,
                "end": end,
                "definition": definition,
            }
            try:
                self.fillIndicatorRange(
                    line, start, line, end, self._hyperlink_indicator
                )
            except RuntimeError:
                pass
        else:
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

    def _get_definition_location(self, word, line, index):
        if self.language != "Python" or not self.jedi_enabled:
            return None
        if not self.current_file_path:
            return None
        if self._is_python_keyword(word):
            return None

        try:
            source = self.text()
            script = jedi.Script(code=source, path=self.current_file_path)
            definitions = script.goto(line + 1, index)
            if not definitions:
                return None

            for defn in definitions:
                if defn.line is None:
                    continue

                module_path = defn.module_path
                file_path = None

                if module_path is not None:
                    file_path = str(module_path)
                elif hasattr(defn, "line") and defn.line:
                    file_path = self.current_file_path

                if file_path:
                    return {
                        "file": file_path,
                        "line": defn.line - 1,
                        "column": defn.column or 0,
                        "same_file": file_path == self.current_file_path,
                    }
            return None
        except Exception:
            return None

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

        # unified insertion function (prevents inconsistent metadata)
        def add(item):
            self.add_item(items_by_label, item, context)

        if self.language == "Python":
            for item in self.get_jedi_completions(context):
                add(item)

        elif self.language in ("CPP", "C"):
            return

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

                items.append(
                    {
                        "label": name,
                        "type": self.normalize_type(completion.type),
                        "source": "jedi",
                        "score": 200,
                        "signature": name,
                        "module": completion.module_name,
                    }
                )

            return items

        except Exception:
            return []

    def load_from_file(self, file_path):
        self.current_file_path = file_path

        with open(file_path, "r", encoding="utf-8") as f:
            self.setText(f.read())

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

    def _mark_dirty(self):
        self._is_dirty = True

    def clear_dirty(self):
        self._is_dirty = False

    def is_dirty(self):
        return self._is_dirty

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

                p { color: var(--text); }

                code {
                    background: #2b2d30;
                    color: #dcdcaa;
                    padding: 2px 6px;
                    border-radius: 4px;}

                pre {
                    background: var(--panel);
                    border: 1px solid var(--border);
                    padding: 12px;
                    border-radius: 8px;
                    overflow-x: auto;
                }

                pre code { background: none; }

                blockquote {
                    border-left: 4px solid var(--accent);
                    padding: 8px 12px;
                    margin: 12px 0;
                    color: var(--muted);
                    background: #222427;
                }

                a {color: var(--accent);
                   text-decoration: none;}

                a:hover {
                    text-decoration: underline;
                }
                ::-webkit-scrollbar {
                    width: 10px;
                    height: 10px;}
                ::-webkit-scrollbar-track {background: var(--bg);}
                ::-webkit-scrollbar-thumb {
                    background: #4a4d52;
                    border-radius: 6px;}
                ::-webkit-scrollbar-thumb:hover { background: #5a5d62; }
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
