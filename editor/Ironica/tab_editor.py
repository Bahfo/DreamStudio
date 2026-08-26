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

from editor import *

from editor.widgets.QDreamTabEditor import QDreamTabEditor

logger = logging.getLogger(__name__)

from editor.Ironica.code_editor import CodeEditor
from editor.Ironica.process_manager import process_manager
from editor.Ironica.utils.minimap import MiniMapHostWidget
from designer.toolbox.designer import DesignerTab
from editor.base.user.trial import FreeTrialWindow


def _webviewer_cls():
    """Lazy import of WebViewer to avoid early QtWebEngine init."""
    from editor.Ironica.supportive.web_browser import WebViewer

    return WebViewer


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
        self.setStyleSheet("""QTabWidget::corner-widget {
            margin-right: -30px;
            padding: 0px;
        }""")

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
        self._minimap_toggle = QPushButton()
        self._minimap_toggle.setIcon(QIcon("assets/editor/minimap.png"))
        self._minimap_toggle.setIconSize(QSize(20, 20))
        self._minimap_toggle.setFixedSize(24, 24)
        self._minimap_toggle.setCheckable(True)
        self._minimap_toggle.setChecked(True)
        self._minimap_toggle.setToolTip("Hide Minimap")
        self._minimap_toggle.clicked.connect(self._toggle_minimap)
        self._minimap_toggle.setVisible(False)
        self.setCornerWidget(self._minimap_toggle, Qt.Corner.TopRightCorner)

        self.currentChanged.connect(self._on_editor_tab_changed)

        # --- Corner Widget Container ---
        self._corner_container = QWidget()
        self._corner_layout = QHBoxLayout(self._corner_container)
        self._corner_layout.setContentsMargins(0, 0, 0, 0)
        self._corner_layout.setSpacing(4)

        # HTML Preview Button
        self._preview_tabs: dict[str, int] = {}
        self._preview_button = QPushButton()
        self._preview_button.setIcon(QIcon("assets/menus/browser.png"))
        self._preview_button.setIconSize(QSize(20, 20))
        self._preview_button.setFixedSize(24, 24)
        self._preview_button.setToolTip("Open HTML Preview")
        self._preview_button.setStyleSheet(
            "QPushButton { background: rgba(128,128,128,40); "
            "border: none; border-radius: 4px; }"
            "QPushButton:hover { background: rgba(128,128,128,90); }"
        )
        self._preview_button.clicked.connect(self.open_preview_tab)
        self._preview_button.setVisible(False)
        self._corner_layout.addWidget(self._preview_button)

        # Minimap toggle
        self._minimap_visible = True
        self._minimap_toggle = QPushButton()
        self._minimap_toggle.setIcon(QIcon("assets/editor/minimap.png"))
        self._minimap_toggle.setIconSize(QSize(20, 20))
        self._minimap_toggle.setFixedSize(24, 24)
        self._minimap_toggle.setCheckable(True)
        self._minimap_toggle.setChecked(True)
        self._minimap_toggle.setToolTip("Hide Minimap")
        self._minimap_toggle.clicked.connect(self._toggle_minimap)
        self._minimap_toggle.setVisible(False)
        self._corner_layout.addWidget(self._minimap_toggle)

        # Set the unified container as the top-right corner widget
        self.setCornerWidget(self._corner_container, Qt.Corner.TopRightCorner)

        self.currentChanged.connect(self._update_preview_button_visibility)
        self.add_close_interceptor(self._on_preview_close_interceptor)

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

        self._minimap_toggle.setChecked(self._minimap_visible)
        self._minimap_toggle.setToolTip(
            "Hide Minimap" if self._minimap_visible else "Show Minimap"
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
        """Update the status bar and route analysis focus on tab change.

        Only the focused editor's requests are allowed through to the
        shared analysis process; switching focus is a cheap ownership swap
        (no process spawn / kill).  The newly focused editor re-queues its
        analysis so its overlays repaint immediately.
        """
        self.return_file_info()
        should_show = self.count() > 0 and index >= 0
        if self._minimap_toggle.isVisible() != should_show:
            self._minimap_toggle.setVisible(should_show)
            QTimer.singleShot(0, self.updateGeometry)

        # Deactivate every non-focused editor first so their pending and
        # future requests are dropped / suppressed.
        for i in range(self.count()):
            if i == index:
                continue
            widget = self.widget(i)
            code = self._unwrap_code_editor(widget)
            if code is not None:
                code.set_analysis_active(False)

        code = None
        if 0 <= index < self.count():
            code = self._unwrap_code_editor(self.widget(index))
        if code is not None:
            process_manager.set_active(code._analysis_owner_id)
            code.set_analysis_active(True)
        else:
            process_manager.set_active(None)

    def _on_editor_dirty_changed(self, is_dirty: bool) -> None:
        editor = self.sender()
        if editor is None:
            return
        for i in range(self.count()):
            if self.widget(i) is editor:
                self.tabBar().mark_dirty(i, is_dirty)
                break

    # ------------------------------------------------------------------
    # HTML Preview
    # ------------------------------------------------------------------

    def _update_preview_button_visibility(self) -> None:
        """Show the preview button when any open tab is an HTML editor."""
        has_html = False
        for i in range(self.count()):
            code_editor = self._unwrap_code_editor(self.widget(i))
            if (
                code_editor is not None
                and getattr(code_editor, "current_lang", None) == "html"
            ):
                has_html = True
                break
        self._preview_button.setVisible(has_html)
        self._reposition_preview_button()

    def _reposition_preview_button(self) -> None:
        """Place the preview button at the top-right of the editor area."""
        if not self._preview_button.isVisible():
            return
        tab_bar_height = self.tabBar().height()
        btn_w = self._preview_button.width()
        x = self.width() - btn_w - 4
        self._preview_button.move(x, tab_bar_height + 4)
        self._preview_button.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_preview_button()

    def open_preview_tab(self) -> None:
        """Open or focus an HTML preview tab for the active editor.

        If a preview for the same file is already open the existing
        preview tab is raised instead of creating a duplicate.
        """
        index = self.currentIndex()
        if index < 0 or index >= self.count():
            return

        widget = self.widget(index)
        if isinstance(widget, _webviewer_cls()):
            return

        code_editor = self._unwrap_code_editor(widget)
        if code_editor is None:
            return
        if getattr(code_editor, "current_lang", None) != "html":
            return

        file_path = code_editor.current_file_path
        if not file_path:
            return

        norm_path = os.path.normcase(os.path.normpath(file_path))
        if norm_path in self._preview_tabs:
            existing = self._preview_tabs[norm_path]
            if existing < self.count() and isinstance(
                self.widget(existing), _webviewer_cls()
            ):
                self.setCurrentIndex(existing)
                return
            del self._preview_tabs[norm_path]

        file_name = pathlib.Path(file_path).name
        preview = _webviewer_cls()(file_path, parent=self)
        preview.file_key = f"__preview_{norm_path}"

        index = self.addTab(preview, f"Preview: {file_name}")
        self.setCurrentIndex(index)
        self._preview_tabs[norm_path] = index
        self._update_preview_button_visibility()

    def _on_preview_close_interceptor(self, index: int, editor) -> bool | None:
        """Clean up preview tracking when a preview tab is closed."""
        if isinstance(editor, _webviewer_cls()):
            for path, preview_idx in list(self._preview_tabs.items()):
                if preview_idx == index:
                    del self._preview_tabs[path]
                    break
            self._update_preview_button_visibility()
        return None

    # ------------------------------------------------------------------
    # Font
    # ------------------------------------------------------------------

    def set_font_size(self, value: int) -> None:
        """Propagate a font-size change to every open editor."""
        for i in range(self.count()):
            editor = self.widget(i)
            if editor and hasattr(editor, "font_size"):
                editor.font_size = value

    def set_editor_font_by_name(self, font_name: str, size: int = 10) -> None:
        """Set the monospace font across all code editors."""
        for i in range(self.count()):
            widget = self.widget(i)
            if isinstance(widget, CodeEditor):
                widget.set_editor_font(font_name)
                widget.font_size = size

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

        code_editor = None
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

        # Wire the threaded file-analysis spinner into the status bar.
        if code_editor is not None:
            status = getattr(self._parent, "status_bar", None)
            if status is not None:
                start_handler = getattr(status, "start_analysis_spinner", None)
                finish_handler = getattr(status, "stop_analysis_spinner", None)
                if start_handler is not None:
                    code_editor.analysis_started.connect(start_handler)
                if finish_handler is not None:
                    code_editor.analysis_finished.connect(finish_handler)

        # Attach background diagnostics for languages that provide them.
        if isinstance(new_editor, MiniMapHostWidget) and language:
            from editor.Ironica.language_engine import LanguageRegistry

            provider = LanguageRegistry.get_provider(language)
            if provider and provider.has_diagnostics():
                code_editor._diag_manager = provider.create_diagnostic_manager(
                    editor=code_editor,
                    file_path=file_path,
                    parent=code_editor,
                )

            if provider and hasattr(provider, "create_completion_manager"):
                provider.create_completion_manager(
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

    def open_free_trial_tab(self) -> None:
        """
        Opens the tab responsible for subscriptions and free trials.
        """
        for i in range(self.count()):
            if isinstance(self.widget(i), FreeTrialWindow):
                self.setCurrentIndex(i)
                return

        tab = FreeTrialWindow(self)
        index = self.addTab(tab, "DreamStudio Subscriptions")
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
        """Handle the ``tabCloseRequested`` signal.

        If the editor is dirty, prompt the user to save, discard,
        or cancel before proceeding with the close.
        """
        editor = self.widget(index)
        if editor is None:
            return

        code_editor = self._unwrap_code_editor(editor)
        if code_editor is not None and code_editor.isModified():
            from editor.widgets.QExitDialog import UnsavedChangesDialog

            tab_name = self.tabText(index)
            dlg = UnsavedChangesDialog(parent=self, dirty_files=[tab_name])
            dlg.exec()
            choice = dlg.result

            if choice == UnsavedChangesDialog.RESULT_CANCEL:
                return
            if choice == UnsavedChangesDialog.RESULT_SAVE:
                code_editor.save()

        self.close_editor(index)

    @staticmethod
    def _unwrap_code_editor(widget):
        """Unwrap MiniMapHostWidget to get the underlying CodeEditor."""
        from editor.Ironica.utils.minimap import MiniMapHostWidget

        if isinstance(widget, MiniMapHostWidget):
            return widget.editor
        return None

    def close_editor(self, index: int) -> None:
        """Close the tab at *index* and clean up all associated state.

        Runs close interceptors first; if any return ``False`` the close
        is aborted.  Removes the dirty-tracker watch, disconnects signals,
        deletes the widget, and adjusts the ``opened_files`` index map.
        """
        editor = self.widget(index)
        if not editor:
            return

        code_editor = self._unwrap_code_editor(editor)

        for cb in self._close_interceptors:
            try:
                result = cb(index, editor)
                if result is False:
                    return
            except Exception as e:
                logger.debug("Close interceptor error: %s", e)

        # Stop any active debug session whose target file is being closed.
        closing_path = getattr(code_editor, "current_file_path", None)
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

        if hasattr(code_editor, "_diag_manager"):
            code_editor._diag_manager.shutdown()

        if code_editor is not None:
            if hasattr(code_editor, "_analysis_manager"):
                try:
                    code_editor._analysis_manager.shutdown()
                except Exception:
                    pass
            for sig_name in ("analysis_started", "analysis_finished"):
                sig = getattr(code_editor, sig_name, None)
                if sig is not None:
                    try:
                        sig.disconnect()
                    except (TypeError, RuntimeError):
                        pass

        if code_editor is not None and hasattr(code_editor, "textChanged"):
            try:
                code_editor.textChanged.disconnect()
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

        win = self.window()
        if hasattr(win, "_defer_menu_sync"):
            win._defer_menu_sync()

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
        code_editor = self._unwrap_code_editor(editor) or editor
        was_unsaved = not getattr(code_editor, "current_file_path", None)
        code_editor.save()
        if was_unsaved and getattr(code_editor, "current_file_path", None):
            self._reopen_saved_tab(code_editor)
            return
        self.tabBar().rebuild_dirty_indices()

    def save_current_file_as(self) -> None:
        """Prompt for a new path and save the active editor."""
        editor = self.currentWidget()
        if not editor or not hasattr(editor, "save_as"):
            return
        code_editor = self._unwrap_code_editor(editor) or editor
        old_path = getattr(code_editor, "current_file_path", None)
        code_editor.save_as()
        new_path = getattr(code_editor, "current_file_path", None)
        if new_path and new_path != old_path:
            self._reopen_saved_tab(code_editor)
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
            code_editor = self._unwrap_code_editor(editor) or editor
            if (
                code_editor
                and hasattr(code_editor, "save")
                and code_editor.current_file_path
            ):
                code_editor.save()
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
