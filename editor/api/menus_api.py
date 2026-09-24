"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Menu callback implementations for the DreamStudio title bar.

This module provides the ``MenusAPI`` mixin that wires every
File-menu action to the correct editor or window operation.
It is designed to be mixed into the DreamStudio QMainWindow alongside
``EditorAPI`` so that ``getattr(self, action_str)`` resolution works.
"""

from editor import *

from editor.Ironica.utils.minimap import MiniMapHostWidget
from editor.utils.notifications.notification_manager import get_notification_manager

logger = logging.getLogger(__name__)


class MenusAPI:
    """Mixin that implements the File/Edit/View/Code menu callbacks.

    Expected to be mixed into the main ``DreamStudio`` window which
    provides ``self.hero_window`` (the ``WorkspaceContainer``) and
    ``self.tab_editors`` (the ``DreamTabbedEditor``).

    Lifecycle methods (save, close) consult the tab editor directly
    rather than wrapping ``EditorAPI`` methods, keeping the call
    chain flat and the intent clear.  Editor commands are routed through
    the active editor's ``EditorAPI`` facade so the menu never manipulates
    editor internals itself.
    """

    # ------------------------------------------------------------------
    # New
    # ------------------------------------------------------------------

    def set_new_file(self) -> None:
        """Open a new untitled file in the tab editor."""
        self.hero_window._text_editor_center.methods.open_new_tab()
        self._defer_menu_sync()

    def set_new_project(self) -> None:
        """Open the solution start window on the Create tab.

        When a new solution is created, the window switches the workspace to
        it and scaffolds the project behind a blocking progress dialog.
        """
        self._invoke_start_window(preferred_tab=0)

    def set_new_window(self) -> None:
        """Placeholder — not yet implemented."""

    def set_open_recent_project(self) -> None:
        """Open the solution start window on the Open/Recent tab."""
        self._invoke_start_window(preferred_tab=1)

    def _invoke_start_window(self, preferred_tab: int = 0) -> None:
        """Run the start window over this main window and apply its choice.

        Args:
            preferred_tab: Which landing tab to preselect (0 create, 1 open).
        """
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

    # ------------------------------------------------------------------
    # Open
    # ------------------------------------------------------------------

    def set_open_file(self) -> None:
        """Open a file from the system via a file chooser dialog."""
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)")
        if path:
            self.hero_window._text_editor_center.methods.open_file(path)
            self._defer_menu_sync()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def set_save_current_file(self) -> None:
        """Save the currently active editor's buffer.

        No-op when no editor tabs are open.
        """
        tabs = self.hero_window._text_editor_center.tabs
        if tabs.count() == 0:
            return
        tabs.save_current_file()

    def set_save_file_as(self) -> None:
        """Prompt for a new path and save the active editor.

        No-op when no editor tabs are open.
        """
        tabs = self.hero_window._text_editor_center.tabs
        if tabs.count() == 0:
            return
        tabs.save_current_file_as()

    def set_save_all_files(self) -> None:
        """Save every open editor that has a file path.

        No-op when no editor tabs are open.
        """
        tabs = self.hero_window._text_editor_center.tabs
        if tabs.count() == 0:
            return
        tabs.save_all_files()

    def set_save_all_and_close(self) -> None:
        """Save every open file and close the main window.

        No-op when no editor tabs are open.
        """
        tabs = self.hero_window._text_editor_center.tabs
        if tabs.count() == 0:
            return
        tabs.save_all_files()
        self.close()

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def set_close_editor(self) -> None:
        """Close all open editor tabs.

        If any tab has unsaved changes, a single dialog lists all dirty
        files and asks the user to Save All, Don't Save, or Cancel.
        """
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
        """Unwrap MiniMapHostWidget to get the underlying CodeEditor."""
        if isinstance(widget, MiniMapHostWidget):
            return widget.editor
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

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def set_import_configurations(self) -> None:
        """Placeholder — not yet implemented."""

    def set_export_configurations(self) -> None:
        """Placeholder — not yet implemented."""

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def set_open_settings(self) -> None:
        """Placeholder — settings and preferences dialog."""

    # ------------------------------------------------------------------
    # Edit
    # ------------------------------------------------------------------

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
        """Open the solution-wide Find/Replace widget for the workspace.

        Reuses the existing file-level search widget: it searches the
        working directory and performs the replacements on disk.  Reports
        through the notification manager when there is no directory to
        search instead of opening an empty widget.
        """
        directory = getattr(self.title_bar, "directory", "") or ""
        if not directory or not os.path.isdir(directory):
            self._notify_menu_error(
                "Find and Replace in Files",
                f"The workspace directory is not available: {directory or '(empty)'}.",
            )
            return
        self._toggle_search_widget()

    # ------------------------------------------------------------------
    # View
    # ------------------------------------------------------------------

    def set_full_screen(self) -> None:
        """Toggle full screen and return to the previous window state.

        The maximized state active before entering full screen is remembered
        so leaving it restores exactly what the user had.
        """
        if self.isFullScreen():
            if getattr(self, "_pre_full_screen_maximized", False):
                self.showMaximized()
            else:
                self.showNormal()
            return

        self._pre_full_screen_maximized = self.isMaximized()
        self.showFullScreen()

    def toggle_options_bar(self) -> Optional[bool]:
        """Toggle the options bar visibility.

        Returns:
            ``True`` when the bar is now visible, ``False`` when it was
            hidden, or ``None`` when this window has no options bar.
        """
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
        """Return the surrounding chrome widgets Zen Mode hides.

        Returns:
            The existing widgets of this window, in the order they are
            hidden; pieces missing from this build are skipped.
        """
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

    # ------------------------------------------------------------------
    # Code
    # ------------------------------------------------------------------

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
        """Collapse every fold region."""
        self._run_editor_command("Collapse All", lambda api: api.collapse_all())

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _run_editor_command(self, operation: str, command) -> None:
        """Run an editor command against the active editor.

        Args:
            operation: Menu label, used when the command cannot run.
            command: Callable receiving the active ``EditorAPI``.
        """
        editor_api = self.hero_window._text_editor_center.current_editor()
        if editor_api is None:
            self._notify_menu_error(operation, "No active code editor is available.")
            return
        command(editor_api)

    @staticmethod
    def _notify_menu_error(title: str, message: str) -> None:
        """Report a menu precondition failure through DreamStudio notifications.

        Args:
            title: Short notification title.
            message: Detailed explanation of the failed precondition.
        """
        logger.error("%s: %s", title, message)
        get_notification_manager().add_error(title, message, source="Menu")
