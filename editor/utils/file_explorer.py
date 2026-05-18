"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved
Developed and Maintained Mainly by DreamStudio Maintainers and Contributors, and
Supervised by EXcellent TechStacks Co.

A Custom Treeview hierarchy for DreamStudio.
"""

# Written by Bahaa Nofal - April/2026

from PyQt6.QtWidgets import (
    QTreeView,
    QLineEdit,
    QVBoxLayout,
    QFrame,
    QMenu,
    QSizePolicy,
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import QSortFilterProxyModel, Qt

from editor.widgets.QIconsProvider import DreamStudioIconProvider


class DreamTreeViewProxy(QSortFilterProxyModel):
    def lessThan(self, source_left, source_right):
        left_data = self.sourceModel().data(source_left)
        right_data = self.sourceModel().data(source_right)

        # Get file info to check if it is a directory
        left_is_dir = self.sourceModel().isDir(source_left)
        right_is_dir = self.sourceModel().isDir(source_right)

        # If one is a directory and the other is not
        if left_is_dir != right_is_dir:
            if self.sortOrder() == Qt.SortOrder.AscendingOrder:
                return left_is_dir
            else:
                return not left_is_dir

        # If both are same type, fall back to default sorting (e.g., by name)
        return super().lessThan(source_left, source_right)


class DreamFileTreeWindow(QFrame):
    def __init__(self, _parent):
        super().__init__(_parent)
        self._parent = _parent
        path = self._parent.currentDirectory
        self.setFrameShape(QFrame.Shape.Panel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setObjectName("mainFileTreeFrame")

        # System Architecture
        self.treeview_layout = QVBoxLayout(self)
        self.treeview_layout.setContentsMargins(10, 10, 10, 10)

        # Treeview System
        self.model = QFileSystemModel()
        self.icon_provider = DreamStudioIconProvider()
        self.model.setIconProvider(self.icon_provider)

        # Search Bar
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText("Search for a file or directory")

        self.proxy_model = DreamTreeViewProxy()
        self.proxy_model.setSourceModel(self.model)

        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setRecursiveFilteringEnabled(True)

        # Model Treeview
        self.tree = QTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setStyleSheet("""
            QTreeView {
                background-color: #171717;
                color: #afb1b3;
                border none;
                outline: 0;
            }
            QTreeView::item {
                height: 20px;
                padding-left: 5px;
                padding-top:2px;
                padding-bottom:2px;
            }
            QTreeView::item:hover {
                background-color: #323232;
            }
            QTreeView::item:selected {
                background-color: #2d476d;
                color: white;
            }
            QHeaderView::section {
                background-color: #313335;
                color: #afb1b3;
                padding: 4px;
                border: 1px solid #1e1e1e;
            }

            QScrollBar:vertical {
            background: #1E1E1E;
            width: 12px;
            margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: #3A3A3A;
                min-height: 20px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical:hover {
                background: #4A4A4A;
            }""")

        self.tree.setUniformRowHeights(True)
        self.tree.header().setStretchLastSection(True)
        self.tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)

        # Right-clicking opens a menu
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.header().setVisible(False)  # First row

        self.tree.setColumnHidden(1, True)  # Size
        self.tree.setColumnHidden(2, True)  # Type
        self.tree.setColumnHidden(3, True)  # Date Modified
        self.tree.header().setStretchLastSection(True)

        # Filtering based on search results
        self.searchBar.textChanged.connect(self.proxy_model.setFilterFixedString)

        self.set_treeview_directory(path)

        self.tree.setAnimated(True)
        self.tree.setIndentation(18)
        self.tree.setSortingEnabled(True)

        self.treeview_layout.addWidget(self.searchBar)
        self.treeview_layout.setSpacing(10)
        self.treeview_layout.addWidget(self.tree)

    def show_context_menu(self, position):
        proxy_index = self.tree.indexAt(position)
        proxy_menu = QMenu(self)
        proxy_menu.setFixedWidth(240)
        proxy_menu.setStyleSheet("""
            background-color: #1E1E1E; 
            color: #afb1b3;
            width: 150px;
            border-radius: 10px;
            font-family: inter, Arial;
            font-size: 12px;""")

        if proxy_index.isValid():
            # Actions for specific files/folders
            source_index = self.proxy_model.mapToSource(proxy_index)
            path = self.model.filePath(source_index)

            proxy_menu.addAction("Toggle Header Info", self.toggle_details)
            rename_act = proxy_menu.addAction("Rename")
            delete_act = proxy_menu.addAction("Delete")
            proxy_menu.addSeparator()
            copy_path_act = proxy_menu.addAction("Copy Path")

            # Execute menu and capture choice
            action = proxy_menu.exec(self.tree.viewport().mapToGlobal(position))

            if action == delete_act:
                self.confirm_delete(path)
            elif action == rename_act:
                self.tree.edit(proxy_index)
        else:
            # Actions for clicking on empty space
            new_file_act = proxy_menu.addAction("New File")
            new_dir_act = proxy_menu.addAction("New Directory")

            action = proxy_menu.exec(self.tree.viewport().mapToGlobal(position))

    def toggle_details(self):
        show = not self.tree.header().isVisible()
        self.tree.header().setVisible(show)

        self.tree.setColumnHidden(1, not show)
        self.tree.setColumnHidden(2, not show)
        self.tree.setColumnHidden(3, not show)

        if show:
            self.tree.resizeColumnToContents(0)

    def set_treeview_directory(self, path):
        self.model.setRootPath(path)
        self.source_index = self.model.index(path)
        self.tree.setRootIndex(self.proxy_model.mapFromSource(self.source_index))
