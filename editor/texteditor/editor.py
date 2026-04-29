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
from PyQt6.QtCore import Qt, QSize, QTimer, QRect, QEvent
from PyQt6.QtWidgets import (
    QStyle,
    QTabBar,
    QTabWidget,
    QFileDialog,
    QStyleOptionTab,
    QGraphicsOpacityEffect,
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QToolBar,
)
from PyQt6.QtGui import (
    QPen,
    QFont,
    QColor,
    QAction,
    QPainter,
    QPalette,
    QKeyEvent,
    QPainterPath,
    QPixmap,
    QImage,
)

import os
import json
import fitz
import pathlib

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
            new_editor = ImageViewer(self)
            new_editor.load_image(file_path)

        elif viewer_type == "pdf":
            new_editor = PDFViewer(self)
            new_editor.load_pdf(file_path)

        else:
            new_editor = CodeEditor(self, language=language)
            if file_path:
                try:
                    new_editor.load_from_file(file_path)
                except UnicodeDecodeError:
                    new_editor.setText(
                        f"Cannot display '{file_name}': Unsupported binary format."
                    )
                    new_editor.setReadOnly(True)
            else:
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

        return "default"

    def set_language(self, lang):
        match lang:
            case ".py" | ".pyi" | ".pyw":
                return "Python"
            case ".c" | ".h" | ".hpp" | ".cpp" | ".cxx" | ".cc" | ".hh" | ".hxx":
                return "CPP"
            case ".txt":
                return None
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
        self._parent = _parent
        self.language = language

        ####################################
        # Texteditor Options
        ####################################
        self.font_size = 11
        self._font = QFont("JetBrains Mono", self.font_size)
        self.setFont(self._font)
        self.setUtf8(True)

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
        self.setCaretLineVisible(True)

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
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        self.setAutoCompletionThreshold(1)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(True)

        # # KEYBINDINGS
        # self.new_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        # self.new_tab_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        # self.new_tab_shortcut.activated.connect(self.hello)

    def load_from_file(self, file_path):
        with open(file_path, "r") as f:
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
            e.modifiers()
            == Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
            and e.key() == Qt.Key.Key_T
        ):
            self._parent.add_new_editor()

        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            line, index = self.getCursorPosition()
            current_line_text = self.text(line)

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
        # Clear existing API if it exists to prevent memory bloat
        if hasattr(self, "api") and self.api:
            self.api.clear()

        self.api = QsciAPIs(lexer)
        for word in classification_map.keys():
            self.api.add(word)
        self.api.prepare()

        return lexer


class ImageViewer(QWidget):
    def __init__(self, _parent=None):
        super().__init__(_parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))

        self.action_zoom_in = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp), "", self
        )
        self.action_zoom_out = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown), "", self
        )
        self.action_reset_zoom = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "", self
        )

        self.toolbar.addAction(self.action_zoom_in)
        self.toolbar.addAction(self.action_zoom_out)
        self.toolbar.addAction(self.action_reset_zoom)

        self.image_label = QLabel("No image loaded")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(200, 200)

        self._layout.addWidget(self.toolbar)
        self._layout.addWidget(self.image_label)

        self._original_pixmap = None

    def load_image(self, file_path):
        pixmap = QPixmap(file_path)

        if not pixmap.isNull():
            self._original_pixmap = pixmap
            self._update_image()
        else:
            self._original_pixmap = None
            self.image_label.setText("Failed to load image format.")

    def _update_image(self):
        if not self._original_pixmap:
            return

        label_size = self.image_label.size()
        pixmap_size = self._original_pixmap.size()

        if (
            pixmap_size.width() > label_size.width()
            or pixmap_size.height() > label_size.height()
        ):
            scaled = self._original_pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setPixmap(self._original_pixmap)

    def resizeEvent(self, event):
        self._update_image()
        super().resizeEvent(event)


class PDFViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc = None
        self.current_page = 0

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.page_label = QLabel("No PDF loaded")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setMinimumSize(400, 500)
        self._layout.addWidget(self.page_label, stretch=1)

        # Navigation Controls
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_prev = QPushButton("Previous")
        self.btn_prev.setFixedSize(80, 30)

        self.lbl_page_info = QLabel("Page: 0 / 0")

        self.btn_next = QPushButton("Next")
        self.btn_next.setFixedSize(80, 30)

        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)

        self.controls_layout.addSpacing(10)
        self.controls_layout.addWidget(self.btn_prev)
        self.controls_layout.addWidget(self.lbl_page_info)
        self.controls_layout.addWidget(self.btn_next)
        self.controls_layout.addSpacing(10)

        self._layout.addLayout(self.controls_layout)

    def load_pdf(self, file_path):
        """Opens the PDF and initializes the first page."""
        try:
            self.doc = fitz.open(file_path)
            self.current_page = 0
            self.render_page()
        except Exception as e:
            self.page_label.setText(f"Error loading PDF: {e}")

    def render_page(self):
        """Converts the current PyMuPDF page to a QPixmap."""
        if not self.doc:
            return

        page = self.doc.load_page(self.current_page)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

        fmt = (
            QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
        )

        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
        pixmap = QPixmap.fromImage(qimg)

        scaled_pixmap = pixmap.scaled(
            self.page_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.page_label.setPixmap(scaled_pixmap)

        self.lbl_page_info.setText(f"Page: {self.current_page + 1} / {len(self.doc)}")

    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()
