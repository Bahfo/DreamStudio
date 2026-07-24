"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved
Developed and Maintained Mainly by DreamStudio Maintainers and Contributors,
and Supervised by EXcellent TechStacks Co.

Tab management for the DreamStudio code editor.

**Ownership Model:**

The tab manager (``DreamTabbedEditor``) owns:

- Tab titles, positions, and ordering.
- The ``opened_files`` deduplication map (normalised path → index).
- Keyboard shortcuts for save / save-as / save-all / format.
- Close interceptors.
- The tab bar dirty / read-only indicators.

The editor widget (``CodeEditor``) owns:

- Text content, cursor position, dirty flag.
- Language and provider state.
- The ``current_file_path`` (single source of truth for file identity).
"""

# Written by Bahaa Nofal

from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtWidgets import (
    QStyle,
    QLabel,
    QWidget,
    QFileDialog,
    QPushButton,
    QVBoxLayout,
)
from PyQt6.QtGui import QShortcut, QKeySequence, QPalette

from editor.widgets.QDreamTabEditor import QDreamTabEditor

import os
import logging
import pathlib

logger = logging.getLogger(__name__)

from editor.Ironica.code_editor import CodeEditor
from editor.Ironica.utils.minimap import MiniMapHostWidget
from editor.utils.toolbox.designer import DesignerTab

CONFIG_CODE_EDITOR = {
    "Set TextEditor Font": ("JetBrains Mono"),
    "Encoding": "UTF-8",
    "Identation_Spacing": 4,
    "Auto Ident": True,
    "Backspace Unidents": True,
    "Tab Idents": True,
    "Identation Width": 4,
    "Numbering Foreground Colors": "#1E1E1E",
}


class DreamTabbedEditor(QDreamTabEditor):
    """Tab container that manages the lifecycle of ``CodeEditor`` widgets.

    Handles opening, closing, saving, and deduplication of file tabs,
    and keeps the tab bar indicators (dirty dot, read-only lock) in
    sync with the underlying editor state.
    """

    def __init__(self, _parent):
        super().__init__(_parent)

        self.setTabsClosable(True)
        self._parent = _parent
        self.currentDirectory = self._parent.currentDirectory
        self.opened_files: dict[str, int] = {}

        self.tab_counter = self.count()

        self._base_tab_style = """
        QTabWidget::pane {{
            border: none;
            background-color: transparent;
        }}
        QTabBar::tab {{
            padding: 6px 12px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            color: {};
        }}
        QTabBar::close-button {{
            image: url(assets/menus/close_editor.png);
            background: transparent;
        }}"""
        self._apply_tab_style_from_palette()

        self._close_interceptors = []
        self.tabCloseRequested.connect(self._on_close_requested)

        # Save Current File
        self._save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self._save_shortcut.activated.connect(self.save_current_file)

        # Save Current File As
        self._save_as_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self._save_as_shortcut.activated.connect(self.save_current_file_as)

        # Save All
        self._save_all_shortcut = QShortcut(QKeySequence("Ctrl+Alt+S"), self)
        self._save_all_shortcut.activated.connect(self.save_all_files)

        # Formatting
        self._format_shortcut = QShortcut(QKeySequence("Ctrl+Alt+F"), self)
        self._format_shortcut.activated.connect(self.format_current_file)

        # Visual Designer
        self._designer_shortcut = QShortcut(QKeySequence("Ctrl+Shift+U"), self)
        self._designer_shortcut.activated.connect(self.open_designer_tab)

        # Minimap toggle (corner widget on the right side of the tab bar)
        self._minimap_visible = True
        self._minimap_toggle = QPushButton("Hide Minimap", self)
        self._minimap_toggle.setFixedHeight(24)
        self._minimap_toggle.clicked.connect(self._toggle_minimap)
        self._minimap_toggle.setVisible(False)
        self.setCornerWidget(self._minimap_toggle, Qt.Corner.TopRightCorner)

        self.currentChanged.connect(self._on_editor_tab_changed)

    # ------------------------------------------------------------------
    # Theme / style
    # ------------------------------------------------------------------

    def _apply_tab_style(self, selected_color: str) -> None:
        self.setStyleSheet(self._base_tab_style.format(selected_color))

    def _apply_tab_style_from_palette(self) -> None:
        color = self.palette().color(QPalette.ColorRole.WindowText).name()
        self._apply_tab_style(color)

    def _toggle_minimap(self) -> None:
        self._minimap_visible = not self._minimap_visible
        self._minimap_toggle.setText(
            "Show Minimap" if not self._minimap_visible else "Hide Minimap"
        )
        for i in range(self.count()):
            w = self.widget(i)
            if isinstance(w, MiniMapHostWidget):
                w.set_minimap_visible(self._minimap_visible)

    def changeEvent(self, event) -> None:
        if event.type() in (
            QEvent.Type.StyleChange,
            QEvent.Type.PaletteChange,
        ):
            if getattr(self, "_in_change_event", False):
                return
            self._in_change_event = True
            try:
                self._apply_tab_style_from_palette()
            finally:
                self._in_change_event = False
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Tab change
    # ------------------------------------------------------------------

    def _on_editor_tab_changed(self, index: int) -> None:
        """Update the status bar when the active tab changes."""
        self.return_file_info()
        self._minimap_toggle.setVisible(self.count() > 0 and index >= 0)

    def _on_editor_dirty_changed(self, is_dirty: bool) -> None:
        editor = self.sender()
        if editor is None:
            return
        for i in range(self.count()):
            if self.widget(i) is editor:
                self.tabBar().mark_dirty(i, is_dirty)
                break

    # ------------------------------------------------------------------
    # Font
    # ------------------------------------------------------------------

    def set_font_size(self, value: int) -> None:
        """Propagate a font-size change to every open editor."""
        for i in range(self.count()):
            editor = self.widget(i)
            if editor and hasattr(editor, "font_size"):
                editor.font_size = value

    # ------------------------------------------------------------------
    # Tab creation
    # ------------------------------------------------------------------

    @staticmethod
    def _is_fallback(widget) -> bool:
        """Return ``True`` if *widget* is a ``FallBack`` placeholder."""
        return isinstance(widget, FallBack)

    def add_new_editor(
        self,
        file_name=None,
        content="",
        language=None,
        file_path=None,
    ):
        """Create a new tab containing either a ``MiniMapHostWidget`` (wrapping
        a ``CodeEditor``) or a ``FallBack`` placeholder.

        If *file_path* is already open the existing tab is raised instead
        of creating a duplicate.

        Args:
            file_name: Display name for the tab.  When ``None`` a default
                ``"untitled - N"`` name is generated.
            content: Initial text for untitled (no *file_path*) tabs.
            language: Language identifier for syntax highlighting.
            file_path: Absolute path to the file on disk.

        Returns:
            The newly created widget (``MiniMapHostWidget`` or ``FallBack``).
        """
        key = self.resolve_key(file_path) if file_path else None

        if key and key in self.opened_files:
            index = self.opened_files[key]
            if index != -1 and index < self.count():
                self.setCurrentIndex(index)
                return self.widget(index)
            else:
                del self.opened_files[key]

        if file_path:
            try:
                code_editor = CodeEditor(self, language=language)
                code_editor.load_from_file(file_path)
                new_editor = MiniMapHostWidget(code_editor, parent=self)
            except (UnicodeDecodeError, OSError, ValueError) as exc:
                logger.warning("Failed to load %s: %s", file_path, exc)
                new_editor = FallBack(self)
                new_editor.setText(content)
        else:
            code_editor = CodeEditor(self, language=language)
            code_editor.setText(content)
            code_editor.clear_dirty()
            new_editor = MiniMapHostWidget(code_editor, parent=self)

        # Attach background diagnostics for Python files.
        if isinstance(new_editor, MiniMapHostWidget) and language == "python":
            from editor.Ironica.plugins.python.jedi_worker import (
                DiagnosticManager,
            )

            code_editor._diag_manager = DiagnosticManager(
                editor=code_editor,
                file_path=file_path,
                parent=code_editor,
            )

        if isinstance(new_editor, MiniMapHostWidget):
            if hasattr(self._parent, "update_position_status"):
                new_editor.position_changed.connect(self._parent.update_position_status)

        if not key:
            key = f"__untitled_{id(new_editor)}"

        if file_name is None:
            file_name = f"untitled - {self.count()}"

        index = self.addTab(new_editor, file_name)
        self.setCurrentIndex(index)

        # Stamp the tab-manager-owned key on the editor for dedup tracking.
        new_editor.file_key = key

        self.opened_files[key] = index

        if isinstance(new_editor, MiniMapHostWidget):
            new_editor.dirty_state_changed.connect(self._on_editor_dirty_changed)

        self.tabBar().rebuild_dirty_indices()

        # Sync read-only indicator from the editor's own state.
        if isinstance(new_editor, MiniMapHostWidget) and new_editor.isReadOnly():
            self.tabBar().mark_readonly(index, True)

        self.setFocus()
        if hasattr(self._parent, "update_editor_visibility"):
            self._parent.update_editor_visibility()

        logger.debug("Opened files: %s", self.opened_files)

        if hasattr(self._parent, "update_position_status"):
            self._parent.update_position_status()
        self.return_file_info()

        return new_editor

    def open_designer_tab(self) -> None:
        """Open or focus a Visual Designer tab.

        If a designer tab is already open it is raised instead of creating
        a duplicate.
        """
        for i in range(self.count()):
            if isinstance(self.widget(i), DesignerTab):
                self.setCurrentIndex(i)
                return

        tab = DesignerTab(self)
        index = self.addTab(tab, "Designer")
        self.setCurrentIndex(index)
        self.setFocus()

    # ------------------------------------------------------------------
    # Close interceptors
    # ------------------------------------------------------------------

    def add_close_interceptor(self, callback) -> None:
        """Register a callback that is invoked before a tab is closed.

        The callback receives ``(index, editor)`` and may return
        ``False`` to prevent the close.
        """
        self._close_interceptors.append(callback)

    def remove_close_interceptor(self, callback) -> None:
        """Unregister a previously registered close interceptor."""
        if callback in self._close_interceptors:
            self._close_interceptors.remove(callback)

    # ------------------------------------------------------------------
    # Tab closing
    # ------------------------------------------------------------------

    def _on_close_requested(self, index: int) -> None:
        """Handle the ``tabCloseRequested`` signal, delegating to :meth:`close_editor`."""
        self.close_editor(index)

    def close_editor(self, index: int) -> None:
        """Close the tab at *index* and clean up all associated state.

        Runs close interceptors first; if any return ``False`` the close
        is aborted.  Removes the dirty-tracker watch, disconnects signals,
        deletes the widget, and adjusts the ``opened_files`` index map.
        """
        editor = self.widget(index)
        if not editor:
            return

        for cb in self._close_interceptors:
            try:
                result = cb(index, editor)
                if result is False:
                    return
            except Exception as e:
                logger.debug("Close interceptor error: %s", e)

        # Stop any active debug session whose target file is being closed.
        closing_path = getattr(editor, "current_file_path", None)
        if closing_path:
            parent = self._parent
            while parent is not None:
                session = getattr(parent, "_active_debug_session", None)
                if session is not None:
                    if getattr(session, "file_path", None) == closing_path:
                        try:
                            session.stop()
                        except Exception:
                            pass
                        parent._active_debug_session = None
                    break
                parent = getattr(parent, "parent", lambda: None)()

        if hasattr(editor, "dirty_state_changed"):
            try:
                editor.dirty_state_changed.disconnect()
            except (TypeError, RuntimeError):
                pass

        if hasattr(editor, "_autocomplete_ext"):
            editor._autocomplete_ext.cleanup()

        if hasattr(editor, "_diag_manager"):
            editor._diag_manager.shutdown()

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
        self.tabBar().rebuild_dirty_indices()

        for k in list(self.opened_files.keys()):
            if self.opened_files[k] > index:
                self.opened_files[k] -= 1

        logger.debug("Opened files after close: %s", self.opened_files)

        if hasattr(self._parent, "update_editor_visibility"):
            self._parent.update_editor_visibility()

    def close_tab(self) -> None:
        """Close the currently active tab."""
        index = self.currentIndex()
        if index < 0 or index >= self.count():
            return

        self.close_editor(index)
        if hasattr(self._parent, "update_editor_visibility"):
            self._parent.update_editor_visibility()

    # ------------------------------------------------------------------
    # File opening
    # ------------------------------------------------------------------

    def open_file(self) -> None:
        """Open a file chooser dialog and load the selected file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            self.currentDirectory,
            "All Supported Files "
            "(*.py *.pyw *.pyi *.txt *.json *.xml "
            "*.yaml *.yml *.md);;"
            "Python Files (*.py *.pyw *.pyi);;"
            "Text/Config Files "
            "(*.txt *.json *.xml *.yaml *.yml);;"
            "All Files (*)",
        )

        if not file_path:
            return

        self.open_file_by_path(file_path)

    def open_file_by_path(self, file_path: str) -> None:
        """Open *file_path* in a new (or existing) tab.

        Args:
            file_path: Absolute path to the file.
        """
        file_name = pathlib.Path(file_path).name
        file_extn = pathlib.Path(file_path).suffix

        try:
            self.add_new_editor(
                file_name=file_name,
                file_path=file_path,
                language=self.set_language(file_extn),
            )
        except Exception as e:
            logger.error("Open file by path failed: %s", e)

    def open_file_at_line(self, file_path: str, line: int) -> None:
        """Open *file_path* and jump the cursor to *line*.

        Used by go-to-definition navigation.
        """
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
                QTimer.singleShot(
                    0,
                    lambda e=editor, l=line: (
                        e.setFocus() if hasattr(e, "setFocus") else None
                    ),
                )
        except Exception as e:
            logger.error("Open file at line failed: %s", e)

    def get_editor_for_path(self, file_path: str):
        """Return the ``CodeEditor`` widget for *file_path*, or ``None``.

        Resolves the path via the dedup key and unwraps
        ``MiniMapHostWidget`` if needed so that the caller always
        receives the underlying ``CodeEditor`` directly.
        """
        key = self.resolve_key(file_path)
        if key is None or key not in self.opened_files:
            return None

        index = self.opened_files[key]
        if index < 0 or index >= self.count():
            return None

        widget = self.widget(index)
        if widget is None:
            return None

        # Unwrap MiniMapHostWidget → CodeEditor.
        if isinstance(widget, MiniMapHostWidget):
            return widget.editor

        if isinstance(widget, CodeEditor):
            return widget

        return None

    @staticmethod
    def set_language(lang: str):
        """Resolve a file extension to a language identifier.

        Args:
            lang: File extension including the leading dot (e.g. ``".py"``).
        """
        from editor.Ironica.language_engine import LanguageRegistry

        return LanguageRegistry.get_language_by_extension(lang)

    def open_new_workspace(self, path: str) -> None:
        """Update the current working directory for the file chooser."""
        self._parent.currentDirectory = path

    @staticmethod
    def resolve_key(file_path):
        """Normalise a file path for use as a dedup key.

        Returns ``None`` when *file_path* is ``None`` or empty.
        """
        if not file_path:
            return None
        return os.path.normcase(os.path.normpath(file_path))

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------

    def save_current_file(self) -> None:
        """Save the currently active editor's buffer.

        After a successful save of a previously-untitled file, the tab is
        closed and re-opened to update the tab title and dedup key.
        """
        editor = self.currentWidget()
        if not editor or not hasattr(editor, "save"):
            return
        was_unsaved = not getattr(editor, "current_file_path", None)
        editor.save()
        if was_unsaved and getattr(editor, "current_file_path", None):
            self._reopen_saved_tab(editor)
            return
        self.tabBar().rebuild_dirty_indices()

    def save_current_file_as(self) -> None:
        """Prompt for a new path and save the active editor."""
        editor = self.currentWidget()
        if not editor or not hasattr(editor, "save_as"):
            return
        old_path = getattr(editor, "current_file_path", None)
        editor.save_as()
        new_path = getattr(editor, "current_file_path", None)
        if new_path and new_path != old_path:
            self._reopen_saved_tab(editor)
            return
        self.tabBar().rebuild_dirty_indices()

    def _reopen_saved_tab(self, editor) -> None:
        """Close the current tab and re-open the file so that the tab
        title, icon, and dedup key reflect the saved path."""
        file_path = editor.current_file_path
        current_idx = self.currentIndex()
        self.close_editor(current_idx)
        self.add_new_editor(
            file_name=pathlib.Path(file_path).name,
            file_path=file_path,
            language=self.set_language(pathlib.Path(file_path).suffix),
        )

    def save_all_files(self) -> None:
        """Save every open editor that has a file path."""
        for i in range(self.count()):
            editor = self.widget(i)
            if editor and hasattr(editor, "save") and editor.current_file_path:
                editor.save()
        self.tabBar().rebuild_dirty_indices()

    # ------------------------------------------------------------------
    # Status bar helpers
    # ------------------------------------------------------------------

    def return_file_info(self) -> None:
        """Push the active editor's EOL and indentation info to the status bar."""
        if not hasattr(self._parent, "_get_current_editor"):
            return
        editor = self._parent._get_current_editor()
        if editor is None:
            return

        from PyQt6.Qsci import QsciScintilla

        eol_mode = editor.eol_mode()
        if eol_mode == QsciScintilla.EolMode.EolWindows:
            line_ending = "CRLF"
        elif eol_mode == QsciScintilla.EolMode.EolMac:
            line_ending = "CR"
        else:
            line_ending = "LF"

        tab_width = editor.indentation_width()
        uses_tabs = editor.uses_tabs()

        if uses_tabs:
            indentation_width = "Tabs"
        else:
            indentation_width = f"{tab_width}"

        status = self._parent.status_bar
        if status is not None:
            status.EOL.setText(f"{line_ending}")
            status.spacing_options.setText(f"Indent {indentation_width} Spaces")

    def format_current_file(self) -> None:
        """Delegate formatting to the active editor's language provider."""
        editor = self.currentWidget()
        if editor and hasattr(editor, "format_current_file"):
            editor.format_current_file()


class FallBack(QWidget):
    """Fallback frame for unsupported file types."""

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
            self.action_button,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

    def setText(self, text: str) -> None:
        self.page_label.setText(text)
