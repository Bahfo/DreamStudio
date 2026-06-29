"""
TitleBarAPI - Wraps DreamStudioTitleBar functionality.

Provides access to title bar actions (new, open, save, edit, etc).
"""


class TitleBarAPI:
    """API for the title bar."""

    def __init__(self, main_window):
        self._main = main_window

    def _bar(self):
        return getattr(self._main, "title_bar", None)

    def newFile(self) -> None:
        """Trigger new file action."""
        self._main.ui_build_add_new_editor()

    def newProject(self) -> None:
        """Trigger new project action."""
        bar = self._bar()
        if bar is not None:
            bar.set_new_project()

    def openFile(self) -> None:
        """Trigger open file action."""
        self._main.ui_build_open_file()

    def openRecentProject(self) -> None:
        """Trigger open recent project action."""
        bar = self._bar()
        if bar is not None:
            bar.set_open_recent_project()

    def saveFile(self) -> None:
        """Trigger save file action."""
        self._main.ui_build_save_file()

    def saveAllFiles(self) -> None:
        """Trigger save all files action."""
        self._main.ui_build_save_all()

    def saveAs(self) -> None:
        """Trigger save as action."""
        self._main.ui_build_save_as()

    def closeEditor(self) -> None:
        """Trigger close editor action."""
        bar = self._bar()
        if bar is not None:
            bar.set_close_editor()

    def cut(self) -> None:
        """Trigger cut action."""
        bar = self._bar()
        if bar is not None:
            bar.set_cut()

    def copy(self) -> None:
        """Trigger copy action."""
        bar = self._bar()
        if bar is not None:
            bar.set_copy()

    def paste(self) -> None:
        """Trigger paste action."""
        bar = self._bar()
        if bar is not None:
            bar.set_paste()

    def undo(self) -> None:
        """Trigger undo action."""
        bar = self._bar()
        if bar is not None:
            bar.set_undo()

    def redo(self) -> None:
        """Trigger redo action."""
        bar = self._bar()
        if bar is not None:
            bar.set_redo()

    def selectAll(self) -> None:
        """Trigger select all action."""
        bar = self._bar()
        if bar is not None:
            bar.set_select_all()

    def deleteSelection(self) -> None:
        """Trigger delete selection action."""
        bar = self._bar()
        if bar is not None:
            bar.set_delete_selection()

    def indentSelection(self) -> None:
        """Trigger indent selection action."""
        bar = self._bar()
        if bar is not None:
            bar.set_indent_selection()

    def unindentSelection(self) -> None:
        """Trigger unindent selection action."""
        bar = self._bar()
        if bar is not None:
            bar.set_unindent_selection()

    def openSettings(self) -> None:
        """Open settings."""
        bar = self._bar()
        if bar is not None:
            bar.set_open_settings()

    def openMarketplace(self) -> None:
        """Open the marketplace."""
        bar = self._bar()
        if bar is not None:
            bar.set_open_marketplace()

    def findReplace(self) -> None:
        """Open find and replace."""
        bar = self._bar()
        if bar is not None:
            bar.set_find_replace()

    def showFileExplorer(self) -> None:
        """Toggle file explorer."""
        bar = self._bar()
        if bar is not None:
            bar.set_file_explorer()

    def showTasksTodo(self) -> None:
        """Open TODO tasks."""
        bar = self._bar()
        if bar is not None:
            bar.set_tasks_todo()
