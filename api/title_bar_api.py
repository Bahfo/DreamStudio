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

    def addMenu(self, title: str):
        """Add a new top-level menu to the menubar.

        Args:
            title: The display name for the new menu.

        Returns:
            The created QMenu instance, or None if unavailable.
        """
        bar = self._bar()
        if bar is None:
            return None
        from PyQt6.QtWidgets import QMenu

        menu = bar.menubar.addMenu(title)
        if menu is not None:
            bar._menus[title] = menu
        return menu

    def addMenuItem(self, menu_title: str, text: str, callback=None):
        """Add an action to an existing menu.

        Args:
            menu_title: The title of the menu to add the item to.
            text: The display text for the menu item.
            callback: Optional callable to invoke when the item is triggered.

        Returns:
            The created QAction, or None if the menu was not found.
        """
        bar = self._bar()
        if bar is None:
            return None
        from PyQt6.QtGui import QAction

        menu = bar._menus.get(menu_title)
        if menu is None:
            return None
        action = QAction(text, bar)
        if callback:
            action.triggered.connect(lambda: callback())
        menu.addAction(action)
        return action

    def addSeparator(self, menu_title: str):
        """Add a separator to an existing menu.

        Args:
            menu_title: The title of the menu to add the separator to.
        """
        bar = self._bar()
        if bar is None:
            return None

        menu = bar._menus.get(menu_title)
        if menu is not None:
            menu.addSeparator()
