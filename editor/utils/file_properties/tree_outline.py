"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

File Outline panel for DreamStudio.  Displays a tree of symbols parsed
from the currently active editor's source code.  The panel is agnostic
about the data source — it receives ``OutlineResult`` objects from the
backend and renders them.
"""

from editor import *
from editor.utils.resource_path import resource_path
from editor.utils.panel_shell import PanelShell
from editor.utils.file_properties.outline import (
    OutlineNode,
    OutlineResult,
    SymbolKind,
)

_ASSETS_DIR = Path(resource_path("assets/editor"))


class _OutlineTreeWidget(QTreeWidget):
    """QTreeWidget that clears selection when clicked on empty space."""

    def mousePressEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.pos())
        if item is None:
            self.clearSelection()
            self.setCurrentItem(None)
        super().mousePressEvent(event)


class TreeOutline(PanelShell):
    """Sidebar panel that renders the file outline tree.

    The outline is populated by calling :meth:`update_outline` with an
    ``OutlineResult`` produced by the backend.  Clicking a symbol scrolls
    the editor to the corresponding line.
    """

    TITLE_TEXT = "File Outline"

    symbol_clicked = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        self._init_icons()
        super().__init__(parent)

    def _init_icons(self) -> None:
        self._icons: dict[SymbolKind, QIcon] = {
            SymbolKind.FILE: self._load_icon("path.png"),
            SymbolKind.CLASS: self._load_icon("class.png"),
            SymbolKind.FUNCTION: self._load_icon("function.png"),
            SymbolKind.METHOD: self._load_icon("function.png"),
            SymbolKind.VARIABLE: self._load_icon("variable.png"),
            SymbolKind.CONSTANT: self._load_icon("variable.png"),
            SymbolKind.DECORATOR: self._load_icon("snippet.png"),
            SymbolKind.PROPERTY: self._load_icon("property.png"),
            SymbolKind.IMPORT: self._load_icon("module.png"),
            SymbolKind.MODULE: self._load_icon("module.png"),
        }

    def _load_icon(self, filename: str) -> QIcon:
        path = _ASSETS_DIR / filename
        if path.exists():
            return QIcon(str(path))
        return QIcon()

    def _build_body(self) -> None:
        self.filter_input = QLineEdit()
        self.filter_input.setFrame(False)
        self.filter_input.setPlaceholderText("Filter symbols...")
        self.filter_input.textChanged.connect(self._filter_tree)
        self._frame_layout.addWidget(self.filter_input)

        self.outline_tree = _OutlineTreeWidget()
        self.outline_tree.setFrameShape(QFrame.Shape.NoFrame)
        self.outline_tree.setHeaderHidden(True)
        self.outline_tree.setAnimated(True)
        self.outline_tree.setIndentation(14)
        self.outline_tree.setRootIsDecorated(True)
        self.outline_tree.itemClicked.connect(self._on_item_clicked)
        self.outline_tree.itemDoubleClicked.connect(self._on_item_clicked)
        self._frame_layout.addWidget(self.outline_tree, stretch=1)

        self._current_result: Optional[OutlineResult] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_outline(self, result: Optional[OutlineResult]) -> None:
        """Populate the tree from an ``OutlineResult``.

        Args:
            result: Parsed outline data, or ``None`` to clear the tree.
        """
        self._current_result = result
        self.outline_tree.clear()

        if result is None:
            return

        root_item = QTreeWidgetItem(self.outline_tree)
        root_name = Path(result.root.name or "Outline").stem
        root_item.setText(0, root_name)
        root_item.setIcon(0, self._icons.get(SymbolKind.FILE, QIcon()))
        root_item.setData(0, Qt.ItemDataRole.UserRole + 1, SymbolKind.FILE.value)
        root_item.setToolTip(0, SymbolKind.FILE.value)
        root_item.setExpanded(True)

        for child in result.root.children:
            self._add_node(root_item, child)

        self.outline_tree.expandToDepth(1)

    def clear_outline(self) -> None:
        """Clear the outline tree."""
        self._current_result = None
        self.outline_tree.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _add_node(self, parent_item: QTreeWidgetItem, node: OutlineNode) -> None:
        """Recursively add an ``OutlineNode`` to the tree."""
        item = QTreeWidgetItem(parent_item)

        item.setText(0, node.name)
        item.setIcon(0, self._icons.get(node.kind, QIcon()))
        item.setData(0, Qt.ItemDataRole.UserRole, node.line_start)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, node.kind.value)
        item.setToolTip(0, f"Line {node.line_start + 1} \u2022 {node.kind.value}")

        for child in node.children:
            self._add_node(item, child)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Emit the line number when a symbol is clicked."""
        line = item.data(0, Qt.ItemDataRole.UserRole)
        if line is not None:
            self.symbol_clicked.emit(int(line))

    def _filter_tree(self, text: str) -> None:
        """Show/hide items based on the filter text."""
        query = text.lower()

        def _filter(item: QTreeWidgetItem) -> bool:
            match = query in item.text(0).lower()
            child_match = False
            for i in range(item.childCount()):
                if _filter(item.child(i)):
                    child_match = True
            visible = match or child_match
            item.setHidden(not visible)
            return visible

        for i in range(self.outline_tree.topLevelItemCount()):
            _filter(self.outline_tree.topLevelItem(i))


