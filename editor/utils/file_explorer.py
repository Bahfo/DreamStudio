"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved
Developed and Maintained Mainly by DreamStudio Maintainers and Contributors, and
Supervised by EXcellent TechStacks Co.

A Custom Treeview hierarchy for DreamStudio.
"""

# Written by Bahaa Nofal - April/2026

import os
import shutil

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QTreeView,
    QLineEdit,
    QFrame,
    QLabel,
    QMenu,
    QPushButton,
    QApplication,
    QDialog,
)
from PyQt6.QtGui import QFileSystemModel, QAction, QActionGroup, QIcon
from PyQt6.QtCore import QSortFilterProxyModel, Qt, QDir, QFileInfo, QSize, QPoint

from editor.widgets.QIconsProvider import DreamStudioIconProvider
from editor.widgets.QExitDialog import ConfirmDialog, RenameDialog


class DreamTreeViewProxy(QSortFilterProxyModel):
    SORT_DEFAULT = 0
    SORT_TYPE = 1
    SORT_MODIFIED_NEWEST = 2
    SORT_MODIFIED_OLDEST = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sort_mode = DreamTreeViewProxy.SORT_DEFAULT
        self._hide_folder_names: list[str] = []
        self._show_hidden: bool = True

    def flags(self, index):
        return (
            self.sourceModel().flags(self.mapToSource(index))
            | Qt.ItemFlag.ItemIsEditable
        )

    def set_sort_mode(self, mode: int) -> None:
        self._sort_mode = mode
        self.invalidate()

    def set_hide_folder_names(self, names: list[str]) -> None:
        self._hide_folder_names = names
        self.invalidateFilter()

    def set_show_hidden(self, show: bool) -> None:
        self._show_hidden = show
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        idx = self.sourceModel().index(source_row, 0, source_parent)
        if not idx.isValid():
            return super().filterAcceptsRow(source_row, source_parent)

        file_path = self.sourceModel().filePath(idx)
        parts = file_path.replace("\\", "/").split("/")

        for folder_name in self._hide_folder_names:
            if folder_name in parts:
                return False

        if not self._show_hidden:
            for part in parts:
                if part.startswith("."):
                    return False

        return super().filterAcceptsRow(source_row, source_parent)

    def lessThan(self, source_left, source_right):
        source_model = self.sourceModel()
        left_info = source_model.fileInfo(source_left)
        right_info = source_model.fileInfo(source_right)

        def get_rank(info: QFileInfo) -> int:
            is_dir = info.isDir()
            is_dot = info.fileName().startswith(".")

            if is_dir and is_dot:
                return 0
            elif is_dir and not is_dot:
                return 1
            elif not is_dir and is_dot:
                return 2
            else:
                return 3

        rank_left = get_rank(left_info)
        rank_right = get_rank(right_info)

        if rank_left != rank_right:
            if self.sortOrder() == Qt.SortOrder.AscendingOrder:
                return rank_left < rank_right
            else:
                return rank_left > rank_right

        if self._sort_mode == DreamTreeViewProxy.SORT_TYPE:
            left_ext = left_info.suffix().lower()
            right_ext = right_info.suffix().lower()
            if left_ext != right_ext:
                return left_ext < right_ext
            return left_info.fileName().lower() < right_info.fileName().lower()

        if self._sort_mode in (
            DreamTreeViewProxy.SORT_MODIFIED_NEWEST,
            DreamTreeViewProxy.SORT_MODIFIED_OLDEST,
        ):
            left_time = left_info.lastModified().toSecsSinceEpoch()
            right_time = right_info.lastModified().toSecsSinceEpoch()
            if left_time != right_time:
                if self._sort_mode == DreamTreeViewProxy.SORT_MODIFIED_NEWEST:
                    return left_time > right_time
                else:
                    return left_time < right_time
            return left_info.fileName().lower() < right_info.fileName().lower()

        name_left = left_info.fileName().lower()
        name_right = right_info.fileName().lower()

        if rank_left == 3:
            ext_left = left_info.suffix().lower()
            ext_right = right_info.suffix().lower()
            if ext_left != ext_right:
                return ext_left < ext_right
        return name_left < name_right


class DreamFileTreeWindow(QFrame):
    _clipboard_path: str | None = None
    _clipboard_is_cut: bool = False

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
        self.model.setFilter(
            QDir.Filter.AllDirs  # Show all directories
            | QDir.Filter.Files  # Show all files
            | QDir.Filter.NoDotAndDotDot  # Hide the generic "." and ".." relative directory links
            | QDir.Filter.Hidden  # <-- THIS LINE REVEALS THE DOT FILES/FOLDERS
        )
        self.icon_provider = DreamStudioIconProvider()
        self.model.setIconProvider(self.icon_provider)

        # Context menu theme colors
        self._menu_bg = "#1E1E1E"
        self._menu_fg = "#afb1b3"
        self._menu_border = "#3F4145"
        self._menu_sel_bg = "#2E436E"
        self._menu_sel_fg = "#ffffff"
        self._menu_disabled_fg = "#555555"
        self._menu_sep = "#3F4145"

        self.treeview_layout.addSpacing(10)
        self.search_label = QLabel("FILE EXPLORER")
        self.search_label.setStyleSheet(
            "color: #969696; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        self.treeview_layout.addWidget(self.search_label)
        self.treeview_layout.addSpacing(5)

        # Toolbar
        self.toolbar = QFrame()
        self.toolbar.setStyleSheet("background-color: transparent; border: none;")
        toolbar_layout = QHBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(2)

        self._toolbar_btn_style = """
        QPushButton {
            background-color: transparent;
            border: none;
            color: #afb1b3;
            font-size: 14px;
            padding: 2px 4px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #323232;
            color: #ffffff;
        }
        QPushButton:disabled {
            color: #555555;
        }
        """
        icon_size = QSize(16, 16)
        btn_size = QSize(26, 26)

        self.add_file_btn = QPushButton()
        self.add_file_btn.setFixedSize(btn_size)
        self.add_file_btn.setStyleSheet(self._toolbar_btn_style)
        self.add_file_btn.setIcon(QIcon("assets/menus/add.png"))
        self.add_file_btn.setIconSize(icon_size)
        self.add_file_btn.setToolTip("Create a new file")
        self.add_file_btn.clicked.connect(self._add_new_file)

        self.add_folder_btn = QPushButton()
        self.add_folder_btn.setFixedSize(btn_size)
        self.add_folder_btn.setStyleSheet(self._toolbar_btn_style)
        self.add_folder_btn.setIcon(QIcon("assets/menus/folder.png"))
        self.add_folder_btn.setIconSize(icon_size)
        self.add_folder_btn.setToolTip("Create a new folder")
        self.add_folder_btn.clicked.connect(self._add_new_folder)

        self.refresh_btn = QPushButton()
        self.refresh_btn.setFixedSize(btn_size)
        self.refresh_btn.setStyleSheet(self._toolbar_btn_style)
        self.refresh_btn.setIcon(QIcon("assets/menus/refresh.png"))
        self.refresh_btn.setIconSize(icon_size)
        self.refresh_btn.setToolTip("Refresh the file tree")
        self.refresh_btn.clicked.connect(self._refresh)

        self.expand_btn = QPushButton()
        self.expand_btn.setFixedSize(btn_size)
        self.expand_btn.setStyleSheet(self._toolbar_btn_style)
        self.expand_btn.setIcon(QIcon("assets/menus/expand.png"))
        self.expand_btn.setIconSize(icon_size)
        self.expand_btn.setToolTip("Expand the selected folder")
        self.expand_btn.setEnabled(False)
        self.expand_btn.clicked.connect(self._expand_selected)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(btn_size)
        self.collapse_btn.setStyleSheet(self._toolbar_btn_style)
        self.collapse_btn.setIcon(QIcon("assets/menus/collapse.png"))
        self.collapse_btn.setIconSize(icon_size)
        self.collapse_btn.setToolTip("Collapse all folders")
        self.collapse_btn.clicked.connect(self._collapse_all)

        self.toolbox_btn = QPushButton("···")
        self.toolbox_btn.setFixedSize(QSize(20, 26))
        self.toolbox_btn.setStyleSheet(self._toolbar_btn_style)
        self.toolbox_btn.setToolTip("More options")
        self.toolbox_btn.clicked.connect(self._show_toolbox_menu)

        toolbar_layout.addWidget(self.add_file_btn)
        toolbar_layout.addWidget(self.add_folder_btn)
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.expand_btn)
        toolbar_layout.addWidget(self.collapse_btn)
        toolbar_layout.addWidget(self.toolbox_btn)
        toolbar_layout.addStretch()

        toolbar_layout.addSpacing(20)
        self.maindirectory = QLabel(f"Directory: {os.path.basename(os.getcwd())}")
        self.maindirectory.setStyleSheet("color: #969696; font-size: 13px;")
        toolbar_layout.addWidget(self.maindirectory)
        self.treeview_layout.addWidget(self.toolbar)
        toolbar_layout.addSpacing(10)

        # Search Bar
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText("Search for a file or directory")
        self.searchBar.setStyleSheet("""
            QLineEdit {
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px 8px;
                color: #ffffff;
            }
            QLineEdit:focus {border: 1px solid #007acc;}
        """)
        self.searchBar.textChanged.connect(self._on_search)

        self.treeview_layout.addWidget(self.searchBar)
        self.treeview_layout.addSpacing(5)

        self.proxy_model = DreamTreeViewProxy()
        self.proxy_model.setSourceModel(self.model)

        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setRecursiveFilteringEnabled(True)

        self._show_hidden_files = True

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
                color: #afb1b3;
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
        self.set_treeview_directory(path)

        self.tree.setAnimated(True)
        self.tree.setIndentation(18)
        self.tree.setSortingEnabled(True)
        self.tree.selectionModel().selectionChanged.connect(self._on_selection_changed)

        self.treeview_layout.setSpacing(10)
        self.treeview_layout.addWidget(self.tree)

    def show_context_menu(self, position):
        proxy_index = self.tree.indexAt(position)

        proxy_menu = QMenu(self)
        proxy_menu.setStyleSheet(self._build_menu_style())

        if proxy_index.isValid():
            source_index = self.proxy_model.mapToSource(proxy_index)
            file_path = self.model.filePath(source_index)
            is_dir = self.model.fileInfo(source_index).isDir()

            # Open
            open_act = QAction("Open")
            if is_dir:
                open_act.triggered.connect(
                    lambda checked, idx=proxy_index: self.tree.expand(idx)
                )
            else:
                open_act.triggered.connect(
                    lambda checked, idx=proxy_index: self._open_file_in_editor(idx)
                )
            proxy_menu.addAction(open_act)
            proxy_menu.addSeparator()

            # Cut
            cut_act = QAction("Cut")
            cut_act.triggered.connect(lambda checked, p=file_path: self._cut_file(p))
            proxy_menu.addAction(cut_act)

            # Copy
            copy_act = QAction("Copy")
            copy_act.triggered.connect(lambda checked, p=file_path: self._copy_file(p))
            proxy_menu.addAction(copy_act)

            # Paste
            paste_act = QAction("Paste")
            paste_target = file_path if is_dir else os.path.dirname(file_path)
            paste_act.setEnabled(DreamFileTreeWindow._clipboard_path is not None)
            paste_act.triggered.connect(
                lambda checked, target=paste_target: self._paste_file(target)
            )
            proxy_menu.addAction(paste_act)
            proxy_menu.addSeparator()

            # Copy Path
            copy_path_act = QAction("Copy Path")
            copy_path_act.triggered.connect(
                lambda checked, p=file_path: self._copy_path(p)
            )
            proxy_menu.addAction(copy_path_act)

            # Copy Relative Path
            copy_rel_act = QAction("Copy Relative Path")
            copy_rel_act.triggered.connect(
                lambda checked, p=file_path: self._copy_relative_path(p)
            )
            proxy_menu.addAction(copy_rel_act)
            proxy_menu.addSeparator()

            # Delete
            delete_act = QAction("Delete")
            delete_act.triggered.connect(
                lambda checked, p=file_path: self.confirm_delete(p)
            )
            proxy_menu.addAction(delete_act)

            # Rename
            rename_act = QAction("Rename")
            rename_act.triggered.connect(
                lambda checked, idx=proxy_index: self._rename_item(idx)
            )
            proxy_menu.addAction(rename_act)
            proxy_menu.addSeparator()

            # Toggle Header Info
            proxy_menu.addAction("Toggle Header Info", self.toggle_details)
        else:
            # Paste
            paste_act = QAction("Paste")
            paste_target = self._parent.currentDirectory
            paste_act.setEnabled(DreamFileTreeWindow._clipboard_path is not None)
            paste_act.triggered.connect(
                lambda checked, target=paste_target: self._paste_file(target)
            )
            proxy_menu.addAction(paste_act)
            proxy_menu.addSeparator()

            # New File
            new_file_act = QAction("New File")
            new_file_act.triggered.connect(lambda checked: self._add_new_file())
            proxy_menu.addAction(new_file_act)

            # New Directory
            new_dir_act = QAction("New Directory")
            new_dir_act.triggered.connect(lambda checked: self._add_new_folder())
            proxy_menu.addAction(new_dir_act)

        proxy_menu.exec(self.tree.viewport().mapToGlobal(position))

    def toggle_details(self):
        show = not self.tree.header().isVisible()
        self.tree.header().setVisible(show)

        self.tree.setColumnHidden(1, not show)
        self.tree.setColumnHidden(2, not show)
        self.tree.setColumnHidden(3, not show)

        if show:
            self.tree.resizeColumnToContents(0)

    def _on_search(self, text: str) -> None:
        self.proxy_model.setFilterFixedString(text)
        if hasattr(self, "source_index") and self.source_index.isValid():
            root = self.proxy_model.mapFromSource(self.source_index)
            if root.isValid():
                self.tree.setRootIndex(root)

    def _on_selection_changed(self) -> None:
        indexes = self.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            source_index = self.proxy_model.mapToSource(index)
            if source_index.isValid() and self.model.fileInfo(source_index).isDir():
                self.expand_btn.setEnabled(True)
                return
        self.expand_btn.setEnabled(False)

    def _add_new_file(self) -> None:
        path = self._parent.currentDirectory
        dialog = RenameDialog(
            self,
            title="New File",
            message="Enter file name:",
            current_text="",
            confirm_text="CREATE",
            cancel_text="CANCEL",
        )
        if hasattr(self._parent, "theme_manager"):
            dialog.retheme(self._parent.theme_manager)
        name = dialog.get_name()
        if name:
            file_path = os.path.join(path, name)
            try:
                open(file_path, "w").close()
            except Exception as e:
                print(f"Error creating file: {e}")

    def _add_new_folder(self) -> None:
        path = self._parent.currentDirectory
        dialog = RenameDialog(
            self,
            title="New Folder",
            message="Enter folder name:",
            current_text="",
            confirm_text="CREATE",
            cancel_text="CANCEL",
        )
        if hasattr(self._parent, "theme_manager"):
            dialog.retheme(self._parent.theme_manager)
        name = dialog.get_name()
        if name:
            dir_path = os.path.join(path, name)
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                print(f"Error creating folder: {e}")

    def _refresh(self) -> None:
        path = self._parent.currentDirectory
        self.model.setRootPath("")
        self.model.setRootPath(path)

    def _expand_selected(self) -> None:
        indexes = self.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            source_index = self.proxy_model.mapToSource(index)
            if source_index.isValid() and self.model.fileInfo(source_index).isDir():
                self.tree.expand(index)

    def _collapse_all(self) -> None:
        self.tree.collapseAll()

    def _open_file_in_editor(self, proxy_index) -> None:
        if hasattr(self._parent, "open_file_from_treeview"):
            self._parent.open_file_from_treeview(proxy_index)

    def _cut_file(self, file_path: str) -> None:
        DreamFileTreeWindow._clipboard_path = file_path
        DreamFileTreeWindow._clipboard_is_cut = True

    def _copy_file(self, file_path: str) -> None:
        DreamFileTreeWindow._clipboard_path = file_path
        DreamFileTreeWindow._clipboard_is_cut = False

    def _paste_file(self, target_dir: str) -> None:
        src = DreamFileTreeWindow._clipboard_path
        if not src or not os.path.exists(src):
            return
        dst = os.path.join(target_dir, os.path.basename(src))
        base, ext = os.path.splitext(os.path.basename(src))
        counter = 1
        while os.path.exists(dst):
            dst = os.path.join(target_dir, f"{base}_{counter}{ext}")
            counter += 1
        try:
            if DreamFileTreeWindow._clipboard_is_cut:
                shutil.move(src, dst)
                DreamFileTreeWindow._clipboard_path = None
            else:
                shutil.copy2(src, dst)
        except Exception as e:
            print(f"Error pasting: {e}")

    def _copy_path(self, file_path: str) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(file_path)

    def _copy_relative_path(self, file_path: str) -> None:
        rel = os.path.relpath(file_path, self._parent.currentDirectory)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(rel)

    def _rename_item(self, proxy_index) -> None:
        source_index = self.proxy_model.mapToSource(proxy_index)
        source_col0 = source_index.siblingAtColumn(0)
        old_path = self.model.filePath(source_col0)
        old_name = self.model.fileName(source_col0)
        dialog = RenameDialog(
            self,
            title="Rename",
            message="Enter new name:",
            current_text=old_name,
            confirm_text="RENAME",
            cancel_text="CANCEL",
        )
        if hasattr(self._parent, "theme_manager"):
            dialog.retheme(self._parent.theme_manager)
        new_name = dialog.get_name()
        if new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                os.rename(old_path, new_path)
            except Exception as e:
                print(f"Error renaming: {e}")

    def confirm_delete(self, file_path: str) -> None:
        dialog = ConfirmDialog(
            self,
            title="Confirm Delete",
            message=f"Are you sure you want to delete '{os.path.basename(file_path)}'?",
            confirm_text="DELETE",
            cancel_text="CANCEL",
            destructive=True,
        )
        if hasattr(self._parent, "theme_manager"):
            dialog.retheme(self._parent.theme_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Error deleting: {e}")

    def _build_menu_style(self) -> str:
        return f"""
        QMenu {{
            background-color: {self._menu_bg};
            color: {self._menu_fg};
            border: 1px solid {self._menu_border};
            border-radius: 0px;
            padding: 4px 0px;
            font-family: 'Inter', Arial;
            font-size: 13px;
        }}
        QMenu::item {{
            padding: 6px 24px 6px 32px;
            background-color: transparent;
        }}
        QMenu::item:selected {{
            background-color: {self._menu_sel_bg};
            color: {self._menu_sel_fg};
        }}
        QMenu::item:disabled {{
            color: {self._menu_disabled_fg};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {self._menu_sep};
            margin: 4px 0px;
        }}
        """

    def _show_toolbox_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(self._build_menu_style())

        cache_act = QAction("Clear Directory Cache")
        cache_act.triggered.connect(self._clear_cache)
        menu.addAction(cache_act)

        ai_menu = QMenu("Add to A.I Chat", menu)
        add_file_act = QAction("Add File to Chat")
        add_file_act.setEnabled(False)
        add_file_act.setToolTip("Coming soon")
        ai_menu.addAction(add_file_act)
        menu.addMenu(ai_menu)

        menu.addSeparator()

        sort_menu = QMenu("Sort by", menu)
        sort_items = [
            ("Default", DreamTreeViewProxy.SORT_DEFAULT),
            ("Type", DreamTreeViewProxy.SORT_TYPE),
            (
                "Modification Time (Newest First)",
                DreamTreeViewProxy.SORT_MODIFIED_NEWEST,
            ),
            (
                "Modification Time (Oldest First)",
                DreamTreeViewProxy.SORT_MODIFIED_OLDEST,
            ),
        ]
        for label, mode in sort_items:
            act = QAction(label, sort_menu)
            act.setCheckable(True)
            act.setChecked(self.proxy_model._sort_mode == mode)
            act.triggered.connect(lambda checked, m=mode: self._set_sort_mode(m))
            sort_menu.addAction(act)
        menu.addMenu(sort_menu)

        menu.addSeparator()

        show_hidden_act = QAction("Show Hidden Files")
        show_hidden_act.setCheckable(True)
        show_hidden_act.setChecked(self._show_hidden_files)
        show_hidden_act.triggered.connect(self._toggle_hidden_files)
        menu.addAction(show_hidden_act)

        btn_pos = self.toolbox_btn.mapToGlobal(QPoint(0, self.toolbox_btn.height()))
        menu.exec(btn_pos)

    def _clear_cache(self) -> None:
        root = self._parent.currentDirectory
        if not root or not os.path.isdir(root):
            return
        deleted = 0
        cache_dirs = {"__pycache__", ".mypy_cache", ".pytest_cache"}
        cache_exts = (".pyc", ".pyo")
        for dirpath, dirnames, filenames in os.walk(root):
            for d in list(dirnames):
                if d in cache_dirs or d.endswith(".egg-info"):
                    full = os.path.join(dirpath, d)
                    try:
                        shutil.rmtree(full)
                        deleted += 1
                    except Exception:
                        pass
                    dirnames.remove(d)
            for f in filenames:
                if f.endswith(cache_exts):
                    full = os.path.join(dirpath, f)
                    try:
                        os.remove(full)
                        deleted += 1
                    except Exception:
                        pass
        print(f"Cache clearing: deleted {deleted} items")

    def _toggle_hidden_files(self) -> None:
        self._show_hidden_files = not self._show_hidden_files
        self.proxy_model.set_show_hidden(self._show_hidden_files)

    def _set_sort_mode(self, mode: int) -> None:
        self.proxy_model.set_sort_mode(mode)

    def retheme(self, t) -> None:
        self._menu_bg = t.color("menu.background", "#1E1E1E")
        self._menu_fg = t.color("menu.text", "#afb1b3")
        self._menu_border = t.color("menu.border", "#3F4145")
        self._menu_sel_bg = t.color("menu.selection_bg", "#2E436E")
        self._menu_sel_fg = t.color("menu.selection_fg", "#ffffff")
        self._menu_disabled_fg = t.color("menu.disabled_fg", "#555555")
        self._menu_sep = t.color("menu.separator", "#3F4145")

        bg = t.color("treeview.background")
        txt = t.color("treeview.text")
        hl = t.color("treeview.highlight")
        hdr_bg = t.color("treeview.header_bg")
        hdr_txt = t.color("treeview.header_text")
        self.setStyleSheet(f"""
            QFrame{{background-color: {bg}; border: none;}}
        """)
        self.tree.setStyleSheet(f"""
            QTreeView {{
                background-color: {bg};
                color: {txt};
                border: none;
                outline: 0;
            }}
            QTreeView::item {{
                height: 20px;
                padding-left: 5px;
                padding-top:2px;
                padding-bottom:2px;
            }}
            QTreeView::item:hover {{
                background-color: {t.color("treeview.hover")};
                color: {txt};
            }}
            QTreeView::item:selected {{
                background-color: {hl};
                color: {t.color("window.text")};
            }}
            QHeaderView::section {{
                background-color: {hdr_bg};
                color: {hdr_txt};
                padding: 4px;
                border: 1px solid {t.color("window.background")};
            }}
            QScrollBar:vertical {{
                background: {t.color("scrollbar.bg")};
                width: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {t.color("scrollbar.fg")};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t.color("scrollbar.hover")};
            }}
        """)
        self.search_label.setStyleSheet(
            f"color: {txt}; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )

        btn_style = f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            color: {txt};
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {t.color("treeview.hover")};
            color: {t.color("window.text")};
        }}
        QPushButton:disabled {{
            color: {t.color("scrollbar.bg")};
        }}
        """
        for btn in self.findChildren(QPushButton):
            btn.setStyleSheet(btn_style)

    def set_treeview_directory(self, path):
        self.model.setRootPath(path)
        self.source_index = self.model.index(path)
        self.tree.setRootIndex(self.proxy_model.mapFromSource(self.source_index))
