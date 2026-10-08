"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Canvas tab hosting draggable nodes over a painted grid background.
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from node_editor.node.nodeGUI import Node


class NodeBuilder(QWidget):
    """Node-graph canvas tab with a grid background and draggable nodes."""

    GRID_SPACING = 30

    def __init__(self, parent=None):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._canvas = QWidget()
        self._canvas.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._canvas.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._canvas.setStyleSheet("background: transparent;")
        self._canvas.setAutoFillBackground(False)
        self._layout.addWidget(self._canvas)

        self.node = Node("Graphical Test", parent=self._canvas)
        self.node.move(50, 50)
        self.node.resize(220, 120)
        self.node.show()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor("#151515"))

        pen = QPen(QColor("#222222"))
        painter.setPen(pen)

        for x in range(0, self.width(), self.GRID_SPACING):
            painter.drawLine(x, 0, x, self.height())

        for y in range(0, self.height(), self.GRID_SPACING):
            painter.drawLine(0, y, self.width(), y)
