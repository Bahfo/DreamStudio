"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved
Developed and Maintained Mainly by DreamStudio Maintainers and Contributors, and
Supervised by EXcellent TechStacks Co.

A Custom editor tab changer and code editor for DreamStudio.
"""

# Written by Bahaa Nofal

from PyQt6.QtCore import Qt, QSize, QTimer, QRect, QEvent
from PyQt6.QtWidgets import (
    QStyle,
    QLabel,
    QTabBar,
    QWidget,
    QTabWidget,
    QFileDialog,
    QPushButton,
    QVBoxLayout,
    QStyleOptionTab,
    QGraphicsOpacityEffect,
)
from PyQt6.QtGui import (
    QPen,
    QColor,
    QPainter,
    QPalette,
    QShortcut,
    QPainterPath,
    QKeySequence,
)

import os
import re
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
