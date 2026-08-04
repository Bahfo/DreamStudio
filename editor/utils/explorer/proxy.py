import os

from PyQt6.QtCore import QDir, QSortFilterProxyModel, Qt, QTimer, QModelIndex
from PyQt6.QtWidgets import QTreeView

from editor.utils.explorer.collapsable_menu import SortMode


class ExplorerFilterProxy(QSortFilterProxyModel):
    """
    Tree filter for the explorer.

    It filters by file name and full path, while preserving parent folders when a
    descendant matches. This is the key fix for the old search behavior: clearing
    the search only clears the proxy filter, it never changes the workspace root.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._search_text = ""
        self._show_hidden = True
        self._root_path = ""
        self._sort_mode: SortMode = SortMode.ALPHA_ASC

        self.setRecursiveFilteringEnabled(True)
        self.setAutoAcceptChildRows(True)
        self.setDynamicSortFilter(True)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_root_path(self, root_path: str) -> None:
        self._root_path = os.path.normpath(root_path)

    def set_search_text(self, text: str) -> None:
        normalized = (text or "").strip()
        if normalized == self._search_text:
            return
        self._search_text = normalized
        self.invalidateFilter()

    def search_text(self) -> str:
        return self._search_text

    def set_show_hidden(self, show_hidden: bool) -> None:
        if self._show_hidden == show_hidden:
            return
        self._show_hidden = show_hidden
        source_model = self.sourceModel()
        if source_model is not None:
            current = source_model.filter()
            if show_hidden:
                current |= QDir.Filter.Hidden
            else:
                current &= ~QDir.Filter.Hidden
            source_model.setFilter(current)
        self.invalidateFilter()

    def show_hidden(self) -> bool:
        return self._show_hidden

    def set_sort_mode(self, mode: SortMode) -> None:
        if self._sort_mode == mode:
            return
        self._sort_mode = mode
        self.invalidate()

    def sort_mode(self) -> SortMode:
        return self._sort_mode

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        source_model = self.sourceModel()
        if source_model is None:
            return False

        index = source_model.index(source_row, 0, source_parent)
        if not index.isValid():
            return False

        file_info = source_model.fileInfo(index)
        file_name = source_model.fileName(index)
        file_path = source_model.filePath(index)

        if not self._show_hidden and file_info.isHidden():
            return False

        if not self._search_text:
            return True

        query = self._search_text.casefold()
        haystack = f"{file_name} {file_path}".casefold()
        return query in haystack

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        source_model = self.sourceModel()
        if source_model is None:
            return super().lessThan(left, right)

        left_info = source_model.fileInfo(left)
        right_info = source_model.fileInfo(right)

        if left_info.isDir() != right_info.isDir():
            return left_info.isDir() and not right_info.isDir()

        left_name = source_model.fileName(left).casefold()
        right_name = source_model.fileName(right).casefold()

        if self._sort_mode == SortMode.EXTENSION:
            left_ext = left_info.completeSuffix().casefold()
            right_ext = right_info.completeSuffix().casefold()
            if left_ext != right_ext:
                return left_ext < right_ext
            if left_name != right_name:
                return left_name < right_name

        if self._sort_mode in (SortMode.MODIFIED_NEWEST, SortMode.MODIFIED_OLDEST):
            left_mtime = left_info.lastModified().toSecsSinceEpoch()
            right_mtime = right_info.lastModified().toSecsSinceEpoch()
            if left_mtime != right_mtime:
                if self._sort_mode == SortMode.MODIFIED_NEWEST:
                    return left_mtime > right_mtime
                return left_mtime < right_mtime

        if self._sort_mode == SortMode.ALPHA_DESC:
            return left_name > right_name

        if left_name != right_name:
            return left_name < right_name

        return (
            source_model.filePath(left).casefold()
            < source_model.filePath(right).casefold()
        )


class DreamTreeView(QTreeView):
    """
    Base class for the treeview of solution explorer in DreamStudio.
    """

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if not self.indexAt(event.pos()).isValid():
            self.clearSelection()
            self.selectionModel().clearCurrentIndex()

    def keyPressEvent(self, event):
        """
        Intercept IDE shortcuts to trigger an action.
        """
        if event.key() == Qt.Key.Key_F2:
            current_index = self.currentIndex()
            if current_index.isValid():
                self.edit(current_index)
                QTimer.singleShot(0, lambda idx=current_index: self._resize_editor(idx))
                event.accept()
                return

        super().keyPressEvent(event)

    def _resize_editor(self, index) -> None:
        """Find the active editor widget and enforce a readable minimum width."""
        editor = self.indexWidget(index)
        if editor is None:
            return
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        text_width = self.fontMetrics().horizontalAdvance(text)
        editor.setMinimumWidth(max(text_width + 24, 150))
