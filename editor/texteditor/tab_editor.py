"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved
Developed and Maintained Mainly by DreamStudio Maintainers and Contributors, and
Supervised by EXcellent TechStacks Co.

A Custom editor tab changer and code editor for DreamStudio.
"""

# Written by Bahaa Nofal

from PyQt6.QtCore import Qt, QSize, QTimer, QRect, QPoint, QEvent
from PyQt6.Qsci import QsciScintilla
from PyQt6.QtWidgets import (
    QStyle,
    QLabel,
    QFrame,
    QTabBar,
    QWidget,
    QCheckBox,
    QTabWidget,
    QFileDialog,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QVBoxLayout,
    QStyleOptionTab,
    QGraphicsOpacityEffect,
)
from PyQt6.QtGui import (
    QPen,
    QColor,
    QPixmap,
    QPainter,
    QPalette,
    QShortcut,
    QPainterPath,
    QKeySequence,
)
from PyQt6.QtSvg import QSvgRenderer

import os
import logging
import pathlib

logger = logging.getLogger(__name__)

### LOCAL IMPORTS
from editor.texteditor.code_editor import CodeEditor
from editor.texteditor.markdown_editor import MarkdownViewer
from editor.texteditor.json_editor import EditConfigurationsTab

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
        self._dirty_indices: set = set()
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
        win = self.window()
        if win is not None and hasattr(win, "update_editor_visibility"):
            win.update_editor_visibility()

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

        selected_bg = getattr(self, "selected_bg", QColor("#25324D"))
        hover_bg = getattr(self, "hover_bg", QColor("#2D2D2D"))
        inactive_bg = getattr(self, "inactive_bg", QColor("#1E1E1E"))
        border_color = getattr(self, "border_color", QColor("#35538F"))
        hover_border_color = getattr(self, "hover_border_color", QColor("#3C3F41"))
        inactive_border_color = getattr(
            self, "inactive_border_color", QColor("#1E1E1E")
        )

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

        text_sel = getattr(self, "_text_selected", QColor("white"))
        text_inactive = getattr(self, "_text_inactive", QColor("#AFB1B3"))
        option.palette.setColor(
            QPalette.ColorRole.WindowText, text_sel if selected else text_inactive
        )

        if index in self._dirty_indices:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            dirty_color = getattr(self, "_dirty_dot", QColor("#FFFFFF"))
            painter.setBrush(dirty_color)
            dot_radius = 4
            dot_x = r.left() + 8
            dot_y = r.center().y()
            painter.drawEllipse(QPoint(dot_x, dot_y), dot_radius, dot_radius)
            painter.restore()

        right_reserve = 32 if self.tabsClosable() else 10
        left_margin = 20 if index in self._dirty_indices else 10
        option.rect = r.adjusted(left_margin, 0, -right_reserve, 0)

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

    def mark_dirty(self, index: int, is_dirty: bool) -> None:
        if is_dirty:
            self._dirty_indices.add(index)
        else:
            self._dirty_indices.discard(index)
        rect = self.tabRect(index)
        if not rect.isNull():
            self.update(rect)

    def retheme(self, t) -> None:
        self.selected_bg = QColor(t.color("tab.selected_bg"))
        self.hover_bg = QColor(t.color("tab.hover_bg"))
        self.inactive_bg = QColor(t.color("tab.inactive_bg"))
        self.border_color = QColor(t.color("tab.selected_border"))
        self.hover_border_color = QColor(t.color("tab.hover_border"))
        self.inactive_border_color = QColor(t.color("tab.inactive_border"))
        self._text_selected = QColor(t.color("tab.text_selected"))
        self._text_inactive = QColor(t.color("tab.text_inactive"))
        self._dirty_dot = QColor(t.color("tab.dirty_dot"))
        self._dirty_indices.clear()
        self.rebuild_dirty_indices()
        self.update()

    def rebuild_dirty_indices(self) -> None:
        self._dirty_indices.clear()
        for i in range(self._parent.count()):
            w = self._parent.widget(i)
            if w is not None and hasattr(w, "is_dirty"):
                try:
                    if w.is_dirty():
                        self._dirty_indices.add(i)
                except RuntimeError:
                    pass

    def on_double_click(self, index):
        logger.debug("double click triggered")
        if index == -1:
            self._parent.add_new_editor()


class DreamTabbedEditor(QTabWidget):
    def __init__(self, _parent, dirty_tracker=None):
        super().__init__(_parent)

        self.setTabBar(DreamStudioIDETabBar(self))
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self._parent = _parent
        self.currentDirectory = self._parent.currentDirectory
        self.opened_files = {}
        self._dirty_tracker = dirty_tracker

        if dirty_tracker is not None:
            dirty_tracker.dirty_state_changed.connect(self._on_dirty_state_changed)

        self.tab_counter = self.count()

        self._base_tab_style = """
        QTabBar::tab {{
            padding: 6px 12px;
            margin-right: 2px;
        }}

        QTabBar::tab:selected {{
            color: {};
        }}

        QTabBar::close-button {{
            image: url(assets/system/close.png);
            background: transparent;
        }}"""
        self._apply_tab_style("white")

        self._close_interceptors = []
        self.tabCloseRequested.connect(self._on_close_requested)
        self._save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self._save_shortcut.activated.connect(self.save_current_file)
        self._save_as_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self._save_as_shortcut.activated.connect(self.save_current_file_as)
        self._save_all_shortcut = QShortcut(QKeySequence("Ctrl+Alt+S"), self)
        self._save_all_shortcut.activated.connect(self.save_all_files)

    def _apply_tab_style(self, selected_color: str) -> None:
        self.setStyleSheet(self._base_tab_style.format(selected_color))

    def retheme(self, t) -> None:
        self._apply_tab_style(t.color("tab.text_selected"))

    def _on_dirty_state_changed(self, editor: object, is_dirty: bool) -> None:
        for i in range(self.count()):
            if self.widget(i) is editor:
                self.tabBar().mark_dirty(i, is_dirty)
                break

    def set_font_size(self, value):
        main_win = self.window()
        tabs = getattr(main_win, "tab_editors", None)
        if not tabs:
            return

        for i in range(tabs.count()):
            editor = tabs.widget(i)
            if editor and hasattr(editor, "_set_font_size_"):
                editor._set_font_size_(value)

    def add_new_editor(
        self,
        file_name=None,
        content="",
        language=None,
        file_path=None,
        welcome: bool = False):

        if welcome:
            new_editor = FastTutorialFrame(self._parent)
            key = f"__welcome_{id(new_editor)}"
            index = self.addTab(new_editor, "Welcome")
            self.setCurrentIndex(index)
            new_editor.file_path = None
            new_editor.file_key = key
            new_editor.viewer_type = "welcome"
            self.opened_files[key] = index
            self.setFocus()
            self._parent.update_editor_visibility()
            return new_editor

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
                new_editor.clear_dirty()

        elif viewer_type == "image":
            try:
                from editor.texteditor.ImageViewer import ImageViewer

                new_editor = ImageViewer(self)

                if file_path:
                    new_editor.load_image(file_path)
                else:
                    new_editor = FallBack(self)

            except ImportError:
                new_editor = FallBack(self)

        elif viewer_type == "pdf":
            try:
                from editor.texteditor.PDFViewer import PDFViewer

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
                new_editor.clear_dirty()

        t = getattr(self._parent, "theme_manager", None)
        if t is not None:
            if isinstance(new_editor, CodeEditor):
                new_editor.apply_theme(t)
            elif isinstance(new_editor, FastTutorialFrame):
                new_editor.retheme(t)
            elif hasattr(new_editor, "apply_theme"):
                new_editor.apply_theme(t)
            elif hasattr(new_editor, "retheme"):
                new_editor.retheme(t)

        st = getattr(self._parent, "syntax_theme_manager", None)
        if st is not None and isinstance(new_editor, CodeEditor):
            new_editor.apply_syntax_only(st)

        if isinstance(new_editor, CodeEditor):
            new_editor.position_changed.connect(self._parent.update_position_status)

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

        if self._dirty_tracker is not None and hasattr(new_editor, "is_dirty"):
            self._dirty_tracker.watch(new_editor)

        self.tabBar().rebuild_dirty_indices()

        self.setFocus()
        self._parent.update_editor_visibility()

        logger.debug(f"Opened files: {self.opened_files}")

        self._parent.update_position_status()
        self.return_file_info()

        return new_editor

    def add_close_interceptor(self, callback):
        self._close_interceptors.append(callback)

    def remove_close_interceptor(self, callback):
        if callback in self._close_interceptors:
            self._close_interceptors.remove(callback)

    def _on_close_requested(self, index):
        editor = self.widget(index)
        for cb in self._close_interceptors:
            try:
                result = cb(index, editor)
                if result is False:
                    return
            except Exception as e:
                logger.debug(f"Close interceptor error: {e}")
        self.close_editor(index)

    def close_editor(self, index):
        editor = self.widget(index)
        if not editor:
            return

        if self._dirty_tracker is not None:
            self._dirty_tracker.unwatch(editor)

        if hasattr(editor, "textChanged"):
            try:
                editor.textChanged.disconnect()
            except (TypeError, RuntimeError):
                pass

        lexer = getattr(editor, "_lexer", None)
        if lexer is not None and hasattr(lexer, "shutdown"):
            try:
                lexer.shutdown()
            except Exception:
                pass

        key = getattr(editor, "file_key", None)
        if key and key in self.opened_files:
            del self.opened_files[key]

        self.removeTab(index)
        editor.deleteLater()
        self.tabBar().rebuild_dirty_indices()

        for k in list(self.opened_files.keys()):
            if self.opened_files[k] > index:
                self.opened_files[k] -= 1

        logger.debug(f"Opened files after close: {self.opened_files}")

    def close_tab(self):
        index = self.currentIndex()
        if index < 0 or index >= self.count():
            return

        self.close_editor(index)
        self._parent.update_editor_visibility()

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            self.currentDirectory,
            "All Supported Files (*.py *.pyw *.pyi *.txt *.json *.xml *.yaml *.yml *.md);;"
            "Python Files (*.py *.pyw *.pyi);;"
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

        if ext in [".py", ".pyi", ".pyw"]:
            return "code"

        if ext == ".md":
            return "metadata"

        return "default"

    def set_language(self, lang):
        match lang:
            case ".py" | ".pyi" | ".pyw":
                return "Python"
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
        if not editor or not hasattr(editor, "save"):
            return
        was_unsaved = not getattr(editor, "current_file_path", None)
        editor.save()
        if was_unsaved and getattr(editor, "current_file_path", None):
            self._reopen_saved_tab(editor)
            return
        if self._dirty_tracker is not None and hasattr(editor, "is_dirty"):
            self._dirty_tracker.sync_state(editor)
        self.tabBar().rebuild_dirty_indices()

    def save_current_file_as(self):
        editor = self.currentWidget()
        if not editor or not hasattr(editor, "save_as"):
            return
        old_path = getattr(editor, "current_file_path", None)
        editor.save_as()
        new_path = getattr(editor, "current_file_path", None)
        if new_path and new_path != old_path:
            self._reopen_saved_tab(editor)
            return
        if self._dirty_tracker is not None and hasattr(editor, "is_dirty"):
            self._dirty_tracker.sync_state(editor)
        self.tabBar().rebuild_dirty_indices()

    def _reopen_saved_tab(self, editor):
        file_path = editor.current_file_path
        current_idx = self.currentIndex()
        self.close_editor(current_idx)
        self.add_new_editor(
            file_name=pathlib.Path(file_path).name,
            file_path=file_path,
            language=self.set_language(pathlib.Path(file_path).suffix),
        )

    def save_all_files(self):
        for i in range(self.count()):
            editor = self.widget(i)
            if editor and hasattr(editor, "save") and editor.current_file_path:
                editor.save()
                if self._dirty_tracker is not None and hasattr(editor, "is_dirty"):
                    self._dirty_tracker.sync_state(editor)
        self.tabBar().rebuild_dirty_indices()

    def return_file_info(self):
        editor = self._parent._get_current_editor()
        if editor is None:
            return

        eol_mode = editor.eolMode()
        if eol_mode == QsciScintilla.EolMode.EolWindows:
            line_ending = "CRLF"
        elif eol_mode == QsciScintilla.EolMode.EolMac:
            line_ending = "CR"
        else:
            line_ending = "LF"

        tab_width = editor.indentationWidth()
        uses_tabs = editor.indentationsUseTabs()

        if uses_tabs:
            indentation_width = f"Tabs"
        else:
            indentation_width = f"{tab_width}"

        self._parent.status_bar.EOL.setText(f"{line_ending}")
        self._parent.status_bar.spacing_options.setText(
            f"Indent {indentation_width} Spaces"
        )


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


class WelcomeAction(QPushButton):
    def __init__(self, text, parent=None, _event=None):
        super().__init__(text, parent)
        self._event = _event

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(200)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                color: #3794ef;
                background: transparent;
                border: none;
                font-size: 14px;
                padding-left: 10px;
                padding-top: 10px;
            }
            QPushButton:hover {
                text-decoration: underline;
                color: #4daafc;
            }
        """)
        if self._event is not None:
            self.clicked.connect(self._event)


class FastTutorialFrame(QFrame):
    def __init__(self, _parent=None):
        super().__init__(_parent)

        self.background_img = QPixmap("assets/logos/welcome_icon.png").scaled(
            150,
            150,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._parent = _parent

        self.bg_svg = QSvgRenderer("assets/logos/welcome_mountains.svg")

        self.setStyleSheet("background-color: transparent; border: none;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 20)
        main_layout.setSpacing(10)

        title = QLabel("DreamStudio 2026")
        title.setStyleSheet("""color: #ffffff; 
            font-size: 42px; 
            font-weight: 300; 
            font-family: montserrat, Arial; 
            padding-left: 120px;""")

        subtitle = QLabel("Get Started with")
        subtitle.setStyleSheet("""
            color: #cccccc; 
            font-size: 20px;
            padding-left: 130px;""")

        main_layout.addWidget(subtitle)
        main_layout.addWidget(title)
        main_layout.addSpacing(20)

        start_label = QLabel("Start")
        start_label.setStyleSheet("""
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            padding-left: 5px;
            padding-top: 20px;
        """)

        main_layout.addWidget(start_label)
        main_layout.addSpacing(6)
        main_layout.addWidget(
            WelcomeAction("New File...", _event=self._parent.ui_build_add_new_editor)
        )
        main_layout.addWidget(
            WelcomeAction("Open File...", _event=self._parent.ui_build_open_file)
        )
        main_layout.addWidget(
            WelcomeAction("Open Folder...", _event=self._parent.open_directory)
        )
        main_layout.addWidget(WelcomeAction("Clone Git Repository..."))
        main_layout.addSpacing(12)
        main_layout.addStretch()

        main_layout.addStretch()

        footer = QHBoxLayout()
        footer.setSpacing(0)
        footer.setContentsMargins(0, 0, 0, 0)

        startup_check = QCheckBox("Show welcome page on startup")
        startup_check.setChecked(True)
        startup_check.setStyleSheet("color: #cccccc; font-size: 12px;")

        footer.addStretch()
        footer.addWidget(startup_check)
        footer.addStretch()

        main_layout.addLayout(footer)

    def retheme(self, t) -> None:
        self.setStyleSheet(
            f"background-color: {t.color('welcome.background_dark')}; border: none;"
        )
        for child in self.findChildren(QLabel):
            txt = child.text()
            if txt == "DreamStudio 2026":
                child.setStyleSheet(
                    f"""color: {t.color('welcome.title')}; font-size: 42px; 
                    font-weight: 300; font-family: montserrat, Arial; padding-left: 120px;"""
                )
            elif txt == "Get Started with":
                child.setStyleSheet(
                    f"color: {t.color('welcome.subtitle')}; font-size: 20px; padding-left: 130px;"
                )
            elif txt == "Start":
                child.setStyleSheet(
                    f"""color: {t.color('welcome.start_label')}; font-size: 18px; 
                    font-weight: bold; padding-left: 5px; padding-top: 20px;"""
                )
        for child in self.findChildren(QCheckBox):
            child.setStyleSheet(f"color: {t.color('welcome.footer')}; font-size: 12px;")
        for child in self.findChildren(WelcomeAction):
            child.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    color: {t.color('welcome.action')};
                    background: transparent;
                    border: none;
                    font-size: 14px;
                    padding-left: 10px;
                    padding-top: 10px;
                }}
                QPushButton:hover {{
                    text-decoration: underline;
                    color: {t.color('welcome.action_hover')};
                }}
            """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if not self.background_img.isNull():
            x = 10
            y = 6
            painter.drawPixmap(x, y, self.background_img)


class BackgroundHintsFrame(QFrame):
    BINDINGS = [
        ("Ctrl + Alt + T", "Open New File"),
        ("Ctrl + Alt + O", "Open Folder"),
        ("Ctrl + Alt + W", "Close Tab"),
        ("Ctrl + S", "Save File"),
        ("Ctrl + Alt + S", "Save All"),
    ]

    def __init__(self, _parent=None):
        super().__init__(_parent)
        self._parent = _parent
        self.setStyleSheet("background-color: #1E1E1E; border: none;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._center_widget = QWidget()
        self._center_widget.setFixedWidth(520)
        center_layout = QVBoxLayout(self._center_widget)
        center_layout.setSpacing(8)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hints_grid = QGridLayout()
        hints_grid.setSpacing(10)
        hints_grid.setHorizontalSpacing(40)

        self._hint_labels = []
        for row, (keys, desc) in enumerate(self.BINDINGS):
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("""
                font-family: 'inter';
                color: #CCCCCC;
                font-size: 16px;
            """)
            desc_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

            key_label = QLabel(keys)
            key_label.setStyleSheet("""
                color: #569CD6;
                font-size: 16px;
                font-family: 'JetBrains Mono', monospace;
                padding: 4px 10px;
                background-color: #2D2D2D;
                border-radius: 3px;
            """)
            key_label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            hints_grid.addWidget(desc_label, row, 0)
            hints_grid.addWidget(key_label, row, 1)
            self._hint_labels.append((key_label, desc_label))

        hints_grid.setColumnStretch(0, 0)
        hints_grid.setColumnStretch(1, 1)

        self._grid_container = QWidget()
        self._grid_container.setLayout(hints_grid)
        center_layout.addWidget(
            self._grid_container, alignment=Qt.AlignmentFlag.AlignCenter
        )
        center_layout.addStretch()

        main_layout.addWidget(
            self._center_widget, alignment=Qt.AlignmentFlag.AlignCenter
        )

    def retheme(self, t) -> None:
        bg = t.color("window.background")
        self.setStyleSheet(f"background-color: {bg}; border: none;")
        self._center_widget.setStyleSheet(f"background-color: transparent;")
        self._grid_container.setStyleSheet(f"background-color: transparent;")
        for key_label, desc_label in self._hint_labels:
            desc_label.setStyleSheet(f"""
                font-family: 'inter';
                color: {t.color('hints.desc')};
                font-size: 16px;
            """)
            key_label.setStyleSheet(f"""
                color: {t.color('hints.text')};
                font-size: 16px;
                font-family: 'JetBrains Mono', monospace;
                padding: 4px 10px;
                background-color: {t.color('hints.key_bg')};
                border-radius: 3px;
            """)
