import os

from PyQt6.QtCore import QSortFilterProxyModel, Qt, QTimer, QModelIndex
from PyQt6.QtWidgets import QTreeView


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
        self._show_hidden = False
        self._root_path = ""

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
        self.invalidateFilter()

    def show_hidden(self) -> bool:
        return self._show_hidden

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

        if not self._show_hidden:
            name = file_info.fileName()
            if name not in (".", "..") and file_info.isHidden():
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

        # Directories first, then case-insensitive alphabetical order.
        if left_info.isDir() != right_info.isDir():
            return left_info.isDir() and not right_info.isDir()

        left_name = source_model.fileName(left).casefold()
        right_name = source_model.fileName(right).casefold()
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
