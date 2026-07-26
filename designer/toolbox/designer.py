from PyQt6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel,
)
from PyQt6.QtCore import Qt

from designer.toolbox.toolbox import ToolBox


class DesignerWidget(QWidget):
    """Visual designer canvas — empty placeholder for future work."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DesignerCanvas")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QLabel("Visual Designer")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color: #888; font-size: 14px; background-color: transparent;"
        )
        layout.addWidget(self._placeholder)


class DesignerTab(QWidget):
    """Composite tab: toolbox sidebar (left) + designer canvas (right)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DesignerTab")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._toolbox = ToolBox()
        root.addWidget(self._toolbox)

        self._canvas = DesignerWidget()
        root.addWidget(self._canvas, 1)
