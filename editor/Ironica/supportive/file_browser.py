"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

File Browser Hierarchy that appears above the code editor - showing
file path and file hierarchy relative to the project root.
"""

from editor import *
from editor.utils.workspace import get_workspace_dir
from editor.utils.explorer.proxy import DreamTreeView


class FileBrowser(QWidget):
    """
    A breadcrumb-style file path widget showing the hierarchy of the current file
    relative to the project root. Each segment is a clickable button that opens
    a minimalistic context menu with a tree view of that folder's contents.
    """

    def __init__(self, parent=None, opened_file=""):
        super().__init__(parent)

        self.setContentsMargins(4, 2, 4, 2)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        # path string expected here
        self.opened_file = opened_file
        self._buttons: list[QPushButton] = []
        self._separators: list[QLabel] = []
        self._build_tree()

        self.setFixedHeight(22)

        self.setStyleSheet("""
            FileBrowser {
                background-color: transparent;
                border: none;
            }
            QPushButton {
                border: none;
                background-color: transparent;
                font-size: 12px;
                padding: 0px 4px;
                color: #CCCCCC;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.2);
                border-radius: 2px;
            }
            QPushButton:pressed {
                background-color: rgba(128, 128, 128, 0.4);
            }
        """)

    def addButtonIndicator(self, text: str, full_path: str, relative_path: str, icon=None) -> QPushButton:
        """
        Create a clickable breadcrumb segment button.

        Args:
            text: Label shown on the button.
            full_path: Absolute path used to root the context-menu tree.
            relative_path: Project-relative path used as the tooltip.
            icon: Optional icon path rendered on the button.

        Returns:
            The configured breadcrumb button.
        """
        btn = QPushButton()
        btn.setText(text)
        btn.setToolTip(relative_path if relative_path else full_path)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("full_path", full_path)

        if icon is not None:
            btn.setIcon(QIcon(icon))

        btn.clicked.connect(lambda checked, b=btn: self._open_context_menu(b))
        return btn

    def _get_project_root(self) -> str:
        """Get the project root directory from the workspace."""
        return get_workspace_dir(self) or ""

    def _populate(self) -> list[tuple[str, str, str]]:
        """
        Populate the widget with hierarchy relative to project root.
        Returns list of (display_name, full_path, relative_path) tuples.
        """
        if not self.opened_file:
            return []

        path = Path(self.opened_file).resolve()
        project_root = self._get_project_root()
        root = Path(project_root).resolve() if project_root else None

        # File inside the project: show only the project-relative segments.
        if root is not None and path.is_relative_to(root):
            parts = []
            current = root
            relative_parts = path.relative_to(root).parts
            for part in relative_parts:
                current = current / part
                rel_path = os.path.relpath(str(current), str(root))
                parts.append((part, str(current), rel_path))
            return parts

        # File outside the project (or no workspace): show only the file name.
        return [(path.name, str(path), path.name)]

    def _open_context_menu(self, btn: QPushButton) -> None:
        """Open a minimalistic context menu with a tree view of the folder."""
        folder_path = btn.property("full_path") or ""
        if not folder_path:
            return

        # Files show their parent folder's contents (VS Code behaviour).
        if os.path.isfile(folder_path):
            folder_path = os.path.dirname(folder_path)
        if not os.path.isdir(folder_path):
            return

        menu = QMenu(self)
        menu.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setFixedSize(250, 260)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        treeview = DreamTreeView()
        treeview.setHeaderHidden(True)
        treeview.setRootIsDecorated(True)
        treeview.setAlternatingRowColors(False)
        treeview.setUniformRowHeights(True)
        treeview.setIndentation(12)
        treeview.setFrameStyle(QFrame.Shape.NoFrame)
        treeview.setStyleSheet("""
            QTreeView {
                background-color: transparent;
                border: none;
                font-size: 11px;
                outline: none;
            }
            QTreeView::item {
                min-height: 18px;
                padding: 1px 4px;
                border: none;
            }
        """)

        model = QFileSystemModel(treeview)
        model.setRootPath(folder_path)
        model.setFilter(
            QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot
        )

        treeview.setModel(model)
        treeview.setRootIndex(model.index(folder_path))

        # Hide the size/type/date columns.
        for col in range(1, model.columnCount()):
            treeview.hideColumn(col)

        layout.addWidget(treeview)

        widget_action = QWidgetAction(menu)
        widget_action.setDefaultWidget(container)
        menu.addAction(widget_action)
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _build_tree(self) -> None:
        """Build the breadcrumb hierarchy buttons relative to project root."""
        for btn in self._buttons:
            self._layout.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()

        for sep in self._separators:
            self._layout.removeWidget(sep)
            sep.deleteLater()
        self._separators.clear()

        hierarchy = self._populate()

        for i, (name, full_path, relative_path) in enumerate(hierarchy):
            is_dir = Path(full_path).is_dir()
            icon = "assets/types/folder.png" if is_dir else "assets/types/file.png"

            btn = self.addButtonIndicator(name, full_path, relative_path, icon)
            self._buttons.append(btn)
            self._layout.addWidget(btn)

            if i < len(hierarchy) - 1:
                sep = QLabel("›")
                sep.setStyleSheet("color: #888888; font-size: 14px; padding: 0px 2px;")
                self._separators.append(sep)
                self._layout.addWidget(sep)

    def set_file_path(self, file_path: str) -> None:
        """
        Update the displayed file path and rebuild the breadcrumb.

        Args:
            file_path: Absolute path of the file to display.
        """
        if file_path == self.opened_file:
            return
        self.opened_file = file_path
        self._build_tree()

    def clear(self) -> None:
        """Remove every breadcrumb segment (used for untitled files)."""
        self.opened_file = ""
        self._build_tree()
