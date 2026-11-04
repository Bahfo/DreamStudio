"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Canvas tab hosting draggable nodes over a painted grid background.
"""

from editor import *
from editor.utils.node_editor.node.nodeGUI import Node


class NodeCanvas(QWidget):
    """
    Node canvas with a painted grid background.
    """

    GRID_SPACING = 30

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("NodeCanvas")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#151515"))

        painter.setPen(QPen(QColor("#222222")))

        for x in range(0, self.width(), self.GRID_SPACING):
            painter.drawLine(x, 0, x, self.height())

        for y in range(0, self.height(), self.GRID_SPACING):
            painter.drawLine(0, y, self.width(), y)


class NodeHeaderRibbon(QWidget):
    """
    Ribbon containing the node editor's tools and settings.
    """

    VERTICAL_BUTTON_WIDTH = 62
    VERTICAL_BUTTON_HEIGHT = 90

    HORIZONTAL_BUTTON_WIDTH = 105
    HORIZONTAL_BUTTON_HEIGHT = 30

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("NodeHeaderRibbon")
        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumHeight(116)
        self.setMaximumHeight(140)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 2)
        self._layout.setSpacing(6)

        home_layout = QHBoxLayout()
        home_layout.setContentsMargins(0, 0, 0, 0)
        home_layout.setSpacing(3)

        self.add_node_btn = self.add_vertical_button(
            "Add\nNode",
            self.VERTICAL_BUTTON_WIDTH,
            self.VERTICAL_BUTTON_HEIGHT,
            "assets/menus/add.png",
        )

        self.save_json_btn = self.add_vertical_button(
            "Save\nSchema\nas JSON",
            self.VERTICAL_BUTTON_WIDTH,
            self.VERTICAL_BUTTON_HEIGHT,
            "assets/menus/save_json.png",
        )

        self.undo_btn = self.add_horizontal_button(
            "Undo Action",
            self.HORIZONTAL_BUTTON_WIDTH,
            self.HORIZONTAL_BUTTON_HEIGHT,
            "assets/menus/undo.png",
        )

        self.redo_btn = self.add_horizontal_button(
            "Redo Action",
            self.HORIZONTAL_BUTTON_WIDTH,
            self.HORIZONTAL_BUTTON_HEIGHT,
            "assets/menus/redo.png",
        )

        home_layout.addWidget(self.add_node_btn)
        home_layout.addWidget(self.save_json_btn)

        home_layout.addWidget(self.create_button_stack(self.undo_btn, self.redo_btn))
        self._layout.addWidget(self.create_group("Home", home_layout))
        self._layout.addWidget(self.create_separator())

        compile_layout = QHBoxLayout()
        compile_layout.setContentsMargins(0, 0, 0, 0)
        compile_layout.setSpacing(3)

        self.convert_cmake_btn = self.add_vertical_button(
            "Convert\nto CMake",
            self.VERTICAL_BUTTON_WIDTH,
            self.VERTICAL_BUTTON_HEIGHT,
            "assets/menus/cmake.png",
        )

        self.run_schema_btn = self.add_vertical_button(
            "Run\nSchema",
            self.VERTICAL_BUTTON_WIDTH,
            self.VERTICAL_BUTTON_HEIGHT,
            "assets/menus/run.png",
        )

        compile_layout.addWidget(self.convert_cmake_btn)
        compile_layout.addWidget(self.run_schema_btn)

        self._layout.addWidget(self.create_group("Compile", compile_layout))
        self._layout.addWidget(self.create_separator())

        view_layout = QHBoxLayout()
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(3)

        self.zoom_in_btn = self.add_horizontal_button(
            "Zoom In",
            self.HORIZONTAL_BUTTON_WIDTH,
            self.HORIZONTAL_BUTTON_HEIGHT,
            "assets/menus/zoom_in.png",
        )

        self.zoom_out_btn = self.add_horizontal_button(
            "Zoom Out",
            self.HORIZONTAL_BUTTON_WIDTH,
            self.HORIZONTAL_BUTTON_HEIGHT,
            "assets/menus/zoom_out.png",
        )

        self.reset_zoom_btn = self.add_vertical_button(
            "Reset\nZoom",
            self.VERTICAL_BUTTON_WIDTH,
            self.VERTICAL_BUTTON_HEIGHT,
            "assets/menus/zoom_reset.png",
        )

        view_layout.addWidget(self.reset_zoom_btn)
        view_layout.addWidget(
            self.create_button_stack(self.zoom_in_btn, self.zoom_out_btn)
        )

        self._layout.addWidget(self.create_group("View", view_layout))
        self._layout.addStretch(1)

    def create_group(self, name, controls_layout):
        group = QWidget(self)
        group.setObjectName("RibbonGroup")

        group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(2, 0, 2, 0)
        group_layout.setSpacing(2)

        group_layout.addLayout(controls_layout, 1)

        label = QLabel(name, group)
        label.setObjectName("RibbonGroupLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedHeight(17)

        group_layout.addWidget(label)
        return group

    def create_separator(self):
        separator = QFrame(self)

        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setLineWidth(1)
        separator.setFixedWidth(2)

        separator.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        return separator

    def create_button_stack(self, *buttons):
        container = QWidget(self)
        container.setFixedHeight(self.VERTICAL_BUTTON_HEIGHT)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        for button in buttons:
            layout.addWidget(button)

        return container

    def add_vertical_button(self, name, width, height, image):
        button = QToolButton(self)

        button.setText(name)
        button.setIcon(QIcon(image))
        button.setObjectName("VerticalRibbonButton")

        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        button.setIconSize(QSize(32, 32))
        button.setFixedSize(width, height)

        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAutoRaise(True)

        self.apply_button_style(button)
        return button

    def add_horizontal_button(self, name, width, height, image):
        button = QToolButton(self)

        button.setText(name)
        button.setIcon(QIcon(image))
        button.setObjectName("HorizontalRibbonButton")

        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        button.setIconSize(QSize(20, 20))
        button.setFixedSize(width, height)

        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAutoRaise(True)

        self.apply_button_style(button)

        return button

    def apply_button_style(self, button):
        """Apply ribbon button styling."""

        button.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 4px;
                font-size: 9pt;
            }

            QToolButton:hover {
                background-color: palette(alternate-base);
                border: 1px solid palette(mid);
            }

            QToolButton:pressed {
                background-color: palette(highlight);
                color: palette(highlighted-text);
                border: 1px solid palette(highlight);
            }

            QToolButton:disabled {
                color: palette(mid);
                background-color: transparent;
                border: 1px solid transparent;
            }
        """)


class NodeBuilder(QWidget):
    """
    Node-graph canvas tab with a grid background and draggable nodes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._ribbon = NodeHeaderRibbon(self)
        self._canvas = NodeCanvas(self)

        self._layout.addWidget(self._ribbon)
        self._layout.addWidget(self._canvas, 1)

        self.node = Node("Graphical Test", parent=self._canvas)
        self.node.setGeometry(50, 50, 220, 120)
        self.node.show()
