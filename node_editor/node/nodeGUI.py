from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class Node(QWidget):
    """Graphical node in the Nodes Designer canvas.

    Main attributes:
        title_widget: Gradient header bar showing the node name.
        tool_combo: Tool selector (Compile, Run Test, Link, Package,
            Deploy, Debug).
    """

    TOOL_OPTIONS: tuple = (
        "Compile",
        "Run Test",
        "Link",
        "Package",
        "Deploy",
        "Debug",
    )

    tool_changed = pyqtSignal(str)

    def __init__(
        self,
        node_title: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("Node")

        self.setStyleSheet(
            "QWidget#Node { border: 1px solid #888888; border-radius: 6px;"
            " background-color: #1E1E1E; }"
        )

        self._drag_position = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(6)

        self.title_widget = QWidget()
        self._set_gradient()
        self.title_widget_layout = QHBoxLayout(self.title_widget)

        self.title = QLabel(node_title)
        self.title.setStyleSheet("background: transparent; color: white; border: none;")
        self.title_widget_layout.addWidget(self.title)

        self._layout.addWidget(self.title_widget)

        self._build_tool_row()

        self._layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.position().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_position is not None:
            delta = event.position().toPoint() - self._drag_position
            self.move(self.pos() + delta)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _build_tool_row(self) -> None:
        """Build the Tool selector row beneath the title bar.

        Creates a ``Tool:`` label paired with a themed combo box
        offering the six pipeline actions. The selection is exposed
        via :attr:`selected_tool` and the :attr:`tool_changed` signal.
        """
        self.tool_row = QWidget()
        self.tool_row.setObjectName("ToolRow")
        self.tool_row.setStyleSheet(
            "QWidget#ToolRow { background: transparent; border: none; }"
        )
        row_layout = QHBoxLayout(self.tool_row)
        row_layout.setContentsMargins(2, 0, 2, 0)
        row_layout.setSpacing(8)

        self.tool_label = QLabel("Tool:")
        self.tool_label.setStyleSheet(
            "background: transparent; color: #C9C9C9; border: none;"
        )
        row_layout.addWidget(self.tool_label)

        self.tool_combo = QComboBox()
        self.tool_combo.setObjectName("ToolCombo")
        self.tool_combo.addItems(list(self.TOOL_OPTIONS))
        self.tool_combo.setStyleSheet(
            "QComboBox#ToolCombo {"
            " background-color: #1F1F1F; color: #F1F1F1;"
            " border: none; border-radius: 5px;"
            " padding: 4px 8px; min-height: 22px;"
            "}"
            "QComboBox#ToolCombo:hover { background-color: #2A2A2A; }"
            "QComboBox#ToolCombo:focus { background-color: #2A2A2A; }"
            "QComboBox#ToolCombo::drop-down {"
            " border: none;"
            " border-top-right-radius: 5px; border-bottom-right-radius: 5px;"
            " background: #2D2D30; width: 22px;"
            "}"
            "QComboBox#ToolCombo QAbstractItemView {"
            " background-color: #252526; color: #F1F1F1;"
            " selection-background-color: #4D2E2E;"
            " selection-color: #FFFFFF; border: none;"
            " outline: none; padding: 2px;"
            "}"
        )
        self.tool_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tool_combo.currentTextChanged.connect(self._on_tool_changed)
        row_layout.addWidget(self.tool_combo, 1)

        self._layout.addWidget(self.tool_row)

    @property
    def selected_tool(self) -> str:
        """Return the currently selected tool name."""
        try:
            return self.tool_combo.currentText()
        except Exception:
            return ""

    def setTool(self, name: str) -> None:
        """Select *name* in the tool combo when it is a valid option.

        Args:
            name: One of :attr:`TOOL_OPTIONS`. Unknown values are ignored.
        """
        try:
            index = list(self.TOOL_OPTIONS).index(name)
        except ValueError:
            return
        self.tool_combo.setCurrentIndex(index)

    def _on_tool_changed(self, name: str) -> None:
        """Forward combo changes through the ``tool_changed`` signal.

        Args:
            name: Newly selected tool name.
        """
        self.tool_changed.emit(name)

    def _set_gradient(self) -> None:
        """Apply the title-bar gradient via stylesheet.

        Args:
            None. Kept for backwards compatibility; the gradient is
            stylesheet-driven so it persists across repaints.
        """
        self.title_widget.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
            stop: 0 #272222, stop: 1 #4D2E2E);
            border: none;
            border-radius: 5px;
        """)
