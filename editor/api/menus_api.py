"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.
Menu callback implementations for the DreamStudio title bar.
"""

from editor import *

from editor.Ironica.utils.minimap import MiniMapHostWidget
from editor.utils.notifications.notification_manager import get_notification_manager
from editor.utils.resource_path import resource_path

logger = logging.getLogger(__name__)

_HASH_COMMENT_SUFFIXES = frozenset(
    {
        ".py",
        ".pyw",
        ".sh",
        ".bash",
        ".zsh",
        ".yaml",
        ".yml",
        ".toml",
        ".rb",
        ".pl",
        ".cmake",
        ".cfg",
        ".ini",
        ".conf",
        ".r",
        ".jl",
        ".ps1",
    }
)
_HTML_COMMENT_SUFFIXES = frozenset(
    {".html", ".htm", ".xhtml", ".xml", ".svg", ".md", ".vue"}
)
_DASH_COMMENT_SUFFIXES = frozenset({".sql", ".lua", ".hs"})

_COPYRIGHT_PATTERN = re.compile(r"\(C\)\s*COPYRIGHT\s+(\d{4})", re.IGNORECASE)
_COPYRIGHT_TEXT = "(C) COPYRIGHT {year} Gizmo Microsystems - All Rights Reserved."


class MenusAPI:
    """Mixin that implements the File/Edit/View/Code menu callbacks."""

    def set_new_file(self) -> None:
        """Open a new untitled file in the tab editor."""
        self.hero_window._text_editor_center.methods.open_new_tab()
        self._defer_menu_sync()

    def set_new_project(self) -> None:
        """Open the solution start window on the Create tab."""
        self._invoke_start_window(preferred_tab=0)

    def set_new_window(self) -> None:
        """Placeholder — not yet implemented."""

    def set_open_recent_project(self) -> None:
        """Open the solution start window on the Open/Recent tab."""
        self._invoke_start_window(preferred_tab=1)

    def _invoke_start_window(self, preferred_tab: int = 0) -> None:
        """Run the start window over this main window and apply its choice."""
        from editor.utils.solution.startup_window import (
            SolutionStartWindow,
            run_start_window_selection,
        )

        window = SolutionStartWindow(registry=self._registry)
        window.set_tab(preferred_tab)
        selection, scaffold = run_start_window_selection(window)
        if not selection or not selection.get("path"):
            return

        path = selection["path"]
        workspace = self._registry.get("workspace") if self._registry else None
        if workspace is not None:
            workspace.open_workspace(path)
        else:
            self.currentDirectory = path
            explorer = getattr(self.hero_window, "_solution_explorer", None)
            if explorer is not None and hasattr(explorer, "set_root_path"):
                explorer.set_root_path(path)

        if scaffold:
            from editor.utils.solution.QScafoldController import ScaffoldController

            controller = ScaffoldController(self, scaffold)
            controller.run_blocking()

    def set_open_file(self) -> None:
        """Open a file from the system via a file chooser dialog."""
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)")
        if path:
            self.hero_window._text_editor_center.methods.open_file(path)
            self._defer_menu_sync()

    def set_save_current_file(self) -> None:
        """Save the currently active editor's buffer."""
        tabs = self.hero_window._text_editor_center.tabs
        if tabs.count() == 0:
            return
        tabs.save_current_file()

    def set_save_file_as(self) -> None:
        """Prompt for a new path and save the active editor."""
        tabs = self.hero_window._text_editor_center.tabs
        if tabs.count() == 0:
            return
        tabs.save_current_file_as()

    def set_save_all_files(self) -> None:
        """Save every open editor that has a file path."""
        tabs = self.hero_window._text_editor_center.tabs
        if tabs.count() == 0:
            return
        tabs.save_all_files()

    def set_save_all_and_close(self) -> None:
        """Save every open file and close the main window."""
        tabs = self.hero_window._text_editor_center.tabs
        if tabs.count() > 0:
            tabs.save_all_files()
        self.close()

    def set_close_editor(self) -> None:
        """Close all open editor tabs."""
        tabs = self.hero_window._text_editor_center.tabs
        if tabs.count() == 0:
            return

        dirty_files = self._collect_dirty_files(tabs)
        if dirty_files:
            from editor.widgets.QExitDialog import UnsavedChangesDialog

            dlg = UnsavedChangesDialog(parent=self, dirty_files=dirty_files)
            dlg.exec()
            choice = dlg.result

            if choice == UnsavedChangesDialog.RESULT_CANCEL:
                return
            if choice == UnsavedChangesDialog.RESULT_SAVE:
                tabs.save_all_files()

        self._close_all_tabs(tabs)
        self._defer_menu_sync()

    def _collect_dirty_files(self, tabs):
        """Return a list of tab names for every dirty editor."""
        dirty = []
        for i in range(tabs.count()):
            widget = tabs.widget(i)
            if widget is None:
                continue
            editor = self._unwrap_editor(widget)
            if editor is not None and editor.isModified():
                dirty.append(tabs.tabText(i))
        return dirty

    @staticmethod
    def _unwrap_editor(widget):
        """Unwrap tab container to get the underlying editor."""
        try:
            from editor.Ironica.utils.minimap import ensure_inner

            return ensure_inner(widget)
        except Exception:
            return None

    def _close_all_tabs(self, tabs):
        """Close every tab from last to first."""
        for i in range(tabs.count() - 1, -1, -1):
            tabs.close_editor(i)

    def set_close_dreamstudio(self) -> None:
        """Close the DreamStudio main window."""
        self.close()

    def set_exit(self) -> None:
        """Exit the application."""
        from PyQt6.QtWidgets import QApplication

        QApplication.quit()

    def set_open_settings(self) -> None:
        """Open the Settings and Preferences window."""
        self._toggle_settings_window()

    def set_undo(self) -> None:
        """Undo the last edit in the active editor."""
        self._run_editor_command("Undo", lambda api: api.undo())

    def set_redo(self) -> None:
        """Redo the last undone edit in the active editor."""
        self._run_editor_command("Redo", lambda api: api.redo())

    def set_cut(self) -> None:
        """Cut the active editor's selection to the clipboard."""
        self._run_editor_command("Cut Selection", lambda api: api.cut())

    def set_copy(self) -> None:
        """Copy the active editor's selection to the clipboard."""
        self._run_editor_command("Copy Selection", lambda api: api.copy())

    def set_copy_as_plain_text(self) -> None:
        """Copy the active selection without syntax formatting."""
        self._run_editor_command(
            "Copy Selection as Plain Text", lambda api: api.copy_as_plain_text()
        )

    def set_paste(self) -> None:
        """Paste the clipboard into the active editor."""
        self._run_editor_command("Paste Clipboard", lambda api: api.paste())

    def set_delete_selection(self) -> None:
        """Delete the active editor's selection."""
        self._run_editor_command("Delete Selection", lambda api: api.delete())

    def set_select_all(self) -> None:
        """Select the whole buffer of the active editor."""
        self._run_editor_command("Select All", lambda api: api.select_all())

    def set_unselect_all(self) -> None:
        """Clear the active editor's selection."""
        self._run_editor_command("Unselect All", lambda api: api.select_none())

    def set_indent_selection(self) -> None:
        """Indent the selected lines of the active editor."""
        self._run_editor_command("Indent Selection", lambda api: api.indent())

    def set_unindent_selection(self) -> None:
        """Unindent the selected lines of the active editor."""
        self._run_editor_command("Unindent Selection", lambda api: api.unindent())

    def set_find_replace_in_files(self) -> None:
        """Open the solution-wide Find/Replace widget for the workspace."""
        directory = getattr(self.title_bar, "directory", "") or ""
        if not directory or not os.path.isdir(directory):
            self._notify_menu_error(
                "Find and Replace in Files",
                f"The workspace directory is not available: {directory or '(empty)'}.",
            )
            return
        self._toggle_search_widget()

    def set_full_screen(self) -> None:
        """Toggle full screen and return to the previous window state."""
        if self.isFullScreen():
            if getattr(self, "_pre_full_screen_maximized", False):
                self.showMaximized()
            else:
                self.showNormal()
            return

        self._pre_full_screen_maximized = self.isMaximized()
        self.showFullScreen()

    def set_toggle_options_bar(self) -> None:
        """Toggle the options bar through its menu owner."""
        self.title_bar.set_toggle_options_bar()

    def toggle_options_bar(self) -> Optional[bool]:
        """Toggle the options bar visibility."""
        bar = getattr(self, "options_menu", None)
        if bar is None:
            self._notify_menu_error(
                "View", "The options bar is not available in this window."
            )
            return None

        visible = not bar.isVisible()
        bar.setVisible(visible)
        return visible

    def set_zen_mode(self) -> None:
        """Toggle the distraction-free Zen presentation."""
        if getattr(self, "_zen_mode_active", False):
            self._leave_zen_mode()
        else:
            self._enter_zen_mode()

    def _zen_surrounding_widgets(self) -> list:
        """Return the surrounding chrome widgets Zen Mode hides."""
        hero = getattr(self, "hero_window", None)
        widgets = []
        for owner, name in (
            (self, "options_menu"),
            (self, "status_bar"),
            (self, "left_sidebar"),
            (self, "right_sidebar"),
            (hero, "_left_utils_manager"),
            (hero, "_right_utils_manager"),
            (hero, "_lower_widget"),
        ):
            widget = getattr(owner, name, None) if owner is not None else None
            if widget is not None:
                widgets.append(widget)
        return widgets

    def _enter_zen_mode(self) -> None:
        """Hide the surrounding chrome, remembering its previous visibility."""
        targets = self._zen_surrounding_widgets()
        if not targets:
            self._notify_menu_error("Zen Mode", "No Zen Mode target is available.")
            return

        self._zen_visibility_snapshot = [(w, w.isVisible()) for w in targets]
        for widget, _was_visible in self._zen_visibility_snapshot:
            widget.setVisible(False)
        self._zen_mode_active = True
        self._refresh_titlebar_state()

    def _leave_zen_mode(self) -> None:
        """Restore the exact chrome visibility active before Zen Mode."""
        for widget, was_visible in getattr(self, "_zen_visibility_snapshot", []):
            try:
                widget.setVisible(was_visible)
            except RuntimeError:
                continue

        self._zen_visibility_snapshot = []
        self._zen_mode_active = False
        self._refresh_titlebar_state()

    def _refresh_titlebar_state(self) -> None:
        """Ask the title bar to re-evaluate its action states."""
        title_bar = getattr(self, "title_bar", None)
        if title_bar is not None:
            title_bar.refresh_action_states()

    def set_format_code(self) -> None:
        """Run the active provider's formatter over the current file."""
        self._run_editor_command("Format Code", lambda api: api.format_code())

    def set_comment_current_line(self) -> None:
        """Comment out the line under the cursor."""
        self._run_editor_command("Comment Current Line", lambda api: api.comment_line())

    def set_comment_current_selection(self) -> None:
        """Comment out every line touched by the selection."""
        self._run_editor_command("Comment Current Selection", lambda api: api.comment())

    def set_uncomment_current_line(self) -> None:
        """Remove the comment marker from the line under the cursor."""
        self._run_editor_command(
            "Uncomment Current Line", lambda api: api.uncomment_line()
        )

    def set_uncomment_current_selection(self) -> None:
        """Remove the comment marker from every selected line."""
        self._run_editor_command(
            "Uncomment Current Selection", lambda api: api.uncomment()
        )

    def set_duplicate_current_line(self) -> None:
        """Duplicate the line under the cursor."""
        self._run_editor_command(
            "Duplicate Current Line", lambda api: api.duplicate_line()
        )

    def set_duplicate_current_selection(self) -> None:
        """Duplicate the selected text below itself."""
        self._run_editor_command(
            "Duplicate Current Selection", lambda api: api.duplicate_selection()
        )

    def set_goto_definition(self) -> None:
        """Jump to the definition of the symbol under the cursor."""
        self._run_editor_command("Go to Definition", lambda api: api.goto_definition())

    def set_goto_declaration(self) -> None:
        """Jump to the declaration of the symbol under the cursor."""
        self._run_editor_command(
            "Go to Declaration", lambda api: api.goto_declaration()
        )

    def set_goto_implementation(self) -> None:
        """Jump to the implementation of the symbol under the cursor."""
        self._run_editor_command(
            "Go to Implementation", lambda api: api.goto_implementation()
        )

    def set_expand_current_fold(self) -> None:
        """Expand the fold region at the cursor."""
        self._run_editor_command("Expand Current", lambda api: api.expand_current())

    def set_expand_all_folds(self) -> None:
        """Expand every fold region."""
        self._run_editor_command("Expand All", lambda api: api.expand_all())

    def set_collapse_current_fold(self) -> None:
        """Collapse the fold region at the cursor."""
        self._run_editor_command("Collapse Current", lambda api: api.collapse_current())

    def set_collapse_all_folds(self) -> None:
        """Smart collapse:"""
        self._run_editor_command("Collapse All", lambda api: api.smart_collapse())

    def set_collapse_includes(self) -> None:
        """Collapse grouped C++ header includes."""
        self._run_editor_command(
            "Collapse Includes", lambda api: api.collapse_includes()
        )

    # ------------------------------------------------------------------
    # Edit — search and indentation
    # ------------------------------------------------------------------
    def set_find_replace(self) -> None:
        """Open the Find and Replace popup for the active workspace."""
        self._toggle_search_widget()

    def set_search_in_selected(self) -> None:
        """Open Find and Replace pre-filled with the current selection."""
        api = self.hero_window._text_editor_center.current_editor()
        selected = ""
        if api is not None:
            selected = api.editor.selectedText() or ""

        widget = self._ensure_search_widget()
        if selected:
            widget.search_input.setText(selected)

        widget._show()
        if selected:
            widget.start_search()

    def set_manage_indentation(self) -> None:
        """Edit the indentation width and tab policy of the active editor."""
        api = self.hero_window._text_editor_center.current_editor()
        if api is None:
            self._notify_menu_error(
                "Manage Indentation", "No active code editor is available."
            )
            return

        width, accepted = QInputDialog.getInt(
            self,
            "Manage Indentation",
            "Indent width (spaces):",
            max(1, api.indentation_width()),
            1,
            16,
        )
        if not accepted:
            return

        mode, accepted = QInputDialog.getItem(
            self,
            "Manage Indentation",
            "Indent with:",
            ["Spaces", "Tabs"],
            1 if api.uses_tabs() else 0,
            False,
        )
        if not accepted:
            return

        api.set_indentation(width, mode == "Tabs")

    # ------------------------------------------------------------------
    # View — sidebar / appearance
    # ------------------------------------------------------------------
    def set_toggle_left_bar(self) -> None:
        """Show or hide the left vertical sidebar."""
        bar = getattr(self, "left_sidebar", None)
        if bar is not None:
            bar.setVisible(not bar.isVisible())

    def set_toggle_right_bar(self) -> None:
        """Show or hide the right services sidebar."""
        bar = getattr(self, "right_sidebar", None)
        if bar is not None:
            bar.setVisible(not bar.isVisible())

    def set_toggle_sidebar_side(self) -> None:
        """Move the left sidebar to the opposite side of the window."""
        layout = getattr(self, "body_layout", None)
        left = getattr(self, "left_sidebar", None)
        right = getattr(self, "right_sidebar", None)
        hero = getattr(self, "hero_window", None)
        if layout is None or left is None or right is None or hero is None:
            return

        left_index = layout.indexOf(left)
        right_index = layout.indexOf(right)
        if left_index < 0 or right_index < 0:
            return

        layout.removeWidget(left)
        layout.removeWidget(right)

        if left_index < right_index:
            layout.insertWidget(0, right)
            layout.insertWidget(layout.count(), left)
        else:
            layout.insertWidget(0, left)
            layout.insertWidget(layout.count(), right)

        left.setVisible(True)
        right.setVisible(True)

    def set_reset_appearance(self) -> None:
        """Restore the default theme and font family."""
        from config.config import DEFAULT_CONFIG

        self._set_theme_by_name("dark")
        self.set_global_font(DEFAULT_CONFIG["editor"]["font_family"])
        self._notify_menu_success(
            "Reset Appearance", "Theme and font restored to their defaults."
        )

    # ------------------------------------------------------------------
    # Tools — panels and windows
    # ------------------------------------------------------------------
    def _show_command_window(self) -> None:
        """Open the command palette anchored under the title-bar search field."""
        window = getattr(self.title_bar, "_commands_window", None)
        if window is None:
            from editor.utils.tools.commands_window import CommandWindow

            window = CommandWindow(self.title_bar._ide_search, self.title_bar)
            self.title_bar._commands_window = window
        window._show()

    def set_tasks_todo(self) -> None:
        """Reveal the TODO search panel."""
        self._toggle_panel("todo_search", self.hero_window._right_utils_manager)

    def set_show_analysis_manager(self) -> None:
        """Reveal the Problems panel as the code-analysis manager."""
        self._toggle_problems()

    # ------------------------------------------------------------------
    # Code — symbol navigation and copyright headers
    # ------------------------------------------------------------------
    def set_find_usages(self) -> None:
        """Find every reference to the symbol under the cursor."""
        self._run_editor_command("Find Usages", lambda api: api.find_usages())

    def set_goto_symbol(self) -> None:
        """Reveal the outline panel listing the symbols of the active file."""
        self._toggle_panel("file_outline", self.hero_window._left_utils_manager)

    def set_add_copyright(self) -> None:
        """Insert the copyright header at the top of the active file."""
        self._apply_copyright(replace_existing=False)

    def set_update_copyright(self) -> None:
        """Refresh the copyright year, inserting a header when absent."""
        self._apply_copyright(replace_existing=True)

    def _apply_copyright(self, replace_existing: bool) -> None:
        """Insert or refresh the copyright header of the active buffer."""
        api = self.hero_window._text_editor_center.current_editor()
        if api is None:
            self._notify_menu_error("Copyright", "No active code editor is available.")
            return

        editor = api.editor
        if editor.isReadOnly():
            self._notify_menu_error("Copyright", "The active file is read-only.")
            return

        prefix, suffix = self._comment_markers(
            getattr(editor, "current_file_path", "") or ""
        )
        header = prefix + _COPYRIGHT_TEXT.format(year=time.strftime("%Y")) + suffix

        for line_no in range(min(10, editor.lines())):
            line_text = editor.text(line_no)
            if not _COPYRIGHT_PATTERN.search(line_text):
                continue
            if replace_existing:
                editor.setSelection(line_no, 0, line_no, len(line_text))
                editor.replaceSelectedText(header)
            return

        editor.insertAt(header + "\n", 0, 0)

    @staticmethod
    def _comment_markers(path: str) -> tuple[str, str]:
        """Return the line-comment prefix and suffix for *path*."""
        suffix = os.path.splitext(path or "")[1].lower()
        if suffix in _HASH_COMMENT_SUFFIXES:
            return "# ", ""
        if suffix in _HTML_COMMENT_SUFFIXES:
            return "<!-- ", " -->"
        if suffix in _DASH_COMMENT_SUFFIXES:
            return "-- ", ""
        return "// ", ""

    # ------------------------------------------------------------------
    # Run / Debug
    # ------------------------------------------------------------------
    def set_run_current_file(self) -> None:
        """Run the active Python file in a new terminal session."""
        self._run_current_file()

    def set_run_without_debugging(self) -> None:
        """Run the active Python file without attaching the debugger."""
        self._run_current_file()

    def set_run_with_arguments(self) -> None:
        """Run the active file with a saved run configuration."""
        self._get_run_menu_controller().run_with_configured_arguments()

    def set_toggle_breakpoint(self) -> None:
        """Toggle a breakpoint on the cursor line of the active editor."""
        api = self.hero_window._text_editor_center.current_editor()
        if api is None:
            return

        editor = api.editor
        if editor.isReadOnly():
            return

        line = editor.getCursorPosition()[0]
        marker = 1 << editor.MARKER_BREAKPOINT
        if editor.markersAtLine(line) & marker:
            editor.markerDelete(line, editor.MARKER_BREAKPOINT)
        else:
            editor.markerAdd(line, editor.MARKER_BREAKPOINT)
            editor._disabled_breakpoints.discard(line)

        self._refresh_titlebar_state()

    def set_enable_all_breakpoints(self) -> None:
        """Re-arm every breakpoint that was disabled."""
        self._set_breakpoints_enabled(True)

    def set_disable_all_breakpoints(self) -> None:
        """Disarm every breakpoint while remembering its line."""
        self._set_breakpoints_enabled(False)

    def set_remove_all_breakpoints(self) -> None:
        """Delete every breakpoint marker in the active editor."""
        api = self.hero_window._text_editor_center.current_editor()
        if api is None:
            return

        editor = api.editor
        editor.markerDeleteAll(editor.MARKER_BREAKPOINT)
        editor._disabled_breakpoints.clear()
        self._refresh_titlebar_state()

    def _set_breakpoints_enabled(self, enabled: bool) -> None:
        """Enable or disable every breakpoint marker of the active editor."""
        api = self.hero_window._text_editor_center.current_editor()
        if api is None:
            return

        editor = api.editor
        marker = 1 << editor.MARKER_BREAKPOINT

        if enabled:
            for line in sorted(editor._disabled_breakpoints):
                editor.markerAdd(line, editor.MARKER_BREAKPOINT)
            editor._disabled_breakpoints.clear()
        else:
            disabled = set()
            for line in range(editor.lines()):
                if editor.markersAtLine(line) & marker:
                    disabled.add(line)
            for line in disabled:
                editor.markerDelete(line, editor.MARKER_BREAKPOINT)
            editor._disabled_breakpoints.update(disabled)

        self._refresh_titlebar_state()

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------
    def show_welcome(self) -> None:
        """Open the IDE welcome / start page tab."""
        self.hero_window._text_editor_center.tabs.open_welcome_window()

    def set_show_about(self) -> None:
        """Show product and version information."""
        version = "unknown"
        registry = getattr(self, "_registry", None)
        if registry is not None and registry.has("config"):
            config = registry.get("config")
            if isinstance(config, dict):
                version = (config.get("general_info") or {}).get("version", version)

        QMessageBox.about(
            self,
            "About DreamStudio",
            "<h3>DreamStudio IDE</h3>"
            f"<p>Version {version}</p>"
            "<p>(C) 2026 Gizmo Microsystems - All Rights Reserved.</p>"
            "<p>Built with PyQt6 and QScintilla.</p>",
        )

    # ------------------------------------------------------------------
    # Configuration import / export
    # ------------------------------------------------------------------
    def set_import_configurations(self) -> None:
        """Import a DreamStudio configuration JSON file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Configuration", "", "Configuration (*.json);;All Files (*)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as handle:
                imported = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            self._notify_menu_error(
                "Import Configuration", f"Cannot read '{path}': {exc}"
            )
            return

        if not isinstance(imported, dict):
            self._notify_menu_error(
                "Import Configuration",
                "The selected file does not contain a configuration object.",
            )
            return

        service = self._config_service()
        if service is None:
            self._notify_menu_error(
                "Import Configuration",
                "The configuration service is not available.",
            )
            return

        for key, value in imported.items():
            if key == "version":
                continue
            service.set(key, value)

        self._apply_imported_appearance(imported)
        self._notify_menu_success(
            "Import Configuration",
            f"Imported settings from '{os.path.basename(path)}'.",
        )

    def set_export_configurations(self) -> None:
        """Export the current configuration to a JSON file."""
        service = self._config_service()
        if service is None:
            self._notify_menu_error(
                "Export Configuration",
                "The configuration service is not available.",
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Configuration",
            "dreamstudio-config.json",
            "Configuration (*.json)",
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(service.data, handle, indent=2)
                handle.write("\n")
        except OSError as exc:
            self._notify_menu_error(
                "Export Configuration", f"Cannot write '{path}': {exc}"
            )
            return

        self._notify_menu_success(
            "Export Configuration",
            f"Saved configuration to '{os.path.basename(path)}'.",
        )

    def _config_service(self):
        """Return the bootstrap ``ConfigurationService``, or ``None``."""
        registry = getattr(self, "_registry", None)
        if registry is not None and registry.has("config_service"):
            return registry.get("config_service")
        return None

    def _apply_imported_appearance(self, imported: dict) -> None:
        """Re-apply theme and font values taken from an imported config."""
        editor_cfg = imported.get("editor")
        if not isinstance(editor_cfg, dict):
            return

        theme = editor_cfg.get("theme")
        if theme:
            self._set_theme_by_name(str(theme))

        family = editor_cfg.get("font_family")
        if family:
            self.set_global_font(str(family))

    def _run_editor_command(self, operation: str, command) -> None:
        """Run an editor command against the active editor."""
        editor_api = self.hero_window._text_editor_center.current_editor()
        if editor_api is None:
            self._notify_menu_error(operation, "No active code editor is available.")
            return
        command(editor_api)

    @staticmethod
    def _notify_menu_error(title: str, message: str) -> None:
        """Report a menu precondition failure through DreamStudio notifications."""
        logger.error("%s: %s", title, message)
        get_notification_manager().add_error(title, message, source="Menu")

    @staticmethod
    def _notify_menu_success(title: str, message: str) -> None:
        """Report a completed menu operation through DreamStudio notifications."""
        logger.info("%s: %s", title, message)
        get_notification_manager().add_success(title, message, source="Menu")
