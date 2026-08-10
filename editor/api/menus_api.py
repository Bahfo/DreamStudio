"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Menu callback implementations for the DreamStudio title bar.

This module provides the ``MenusAPI`` mixin that wires every
File-menu action to the correct editor or window operation.
It is designed to be mixed into the DreamStudio QMainWindow alongside
``EditorAPI`` so that ``getattr(self, action_str)`` resolution works.
"""

import pathlib

from PyQt6.QtWidgets import QFileDialog

from editor.Ironica.utils.minimap import MiniMapHostWidget


class MenusAPI:
    """Mixin that implements all File-menu callbacks.

    Expected to be mixed into the main ``DreamStudio`` window which
    provides ``self.hero_window`` (the ``WorkspaceContainer``) and
    ``self.tab_editors`` (the ``DreamTabbedEditor``).

    Lifecycle methods (save, close) consult the tab editor directly
    rather than wrapping ``EditorAPI`` methods, keeping the call
    chain flat and the intent clear.
    """

    # ------------------------------------------------------------------
    # New
    # ------------------------------------------------------------------

    def set_new_file(self) -> None:
        """Open a new untitled file in the tab editor."""
        self.hero_window._text_editor_center.methods.open_new_tab()
        self._defer_menu_sync()

    def set_new_project(self) -> None:
        """Placeholder — not yet implemented."""

    def set_new_window(self) -> None:
        """Placeholder — not yet implemented."""

    # ------------------------------------------------------------------
    # Open
    # ------------------------------------------------------------------

    def set_open_file(self) -> None:
        """Open a file from the system via a file chooser dialog."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "All Files (*)"
        )
        if path:
            self.hero_window._text_editor_center.methods.open_file(path)
            self._defer_menu_sync()

    def set_open_recent_project(self) -> None:
        """Placeholder — not yet implemented."""

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

            dlg = UnsavedChangesDialog(
                parent=self, dirty_files=dirty_files
            )
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
