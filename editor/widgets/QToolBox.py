"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Toolbar buttons for the DreamStudio file explorer.
"""

from editor import *

# Local Imports
from editor.widgets.QToolButton import ToolbarButton


class ExplorerToolbar(QHBoxLayout):
    """
    Explorer Toolbox with needed options for the solution explorer.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setContentsMargins(4, 2, 4, 2)
        self.setSpacing(2)
        self._buttons: list[ToolbarButton] = []
        self._directory_label = None

    def add_button(
        self,
        icon_path: str,
        tooltip: str,
        callback=None,
        fixed_size: tuple[int, int] = (24, 24),
        icon_size: tuple[int, int] = (20, 20),
    ) -> ToolbarButton:
        btn = ToolbarButton(
            icon_path,
            tooltip,
            fixed_size=fixed_size,
            icon_size=icon_size,
            callback=callback,
        )
        self._buttons.append(btn)
        self.addWidget(btn)
        return btn

    def add_separator(self, height: int) -> QFrame:
        """Add a elegant vertical divider line between button segments."""
        sep = QFrame()
        sep.setObjectName("ToolbarSeparator")
        sep.setFixedWidth(1)
        sep.setFixedHeight(height)

        self.addWidget(sep, alignment=Qt.AlignmentFlag.AlignVCenter)
        return sep

    def add_label(self, text: str = "") -> QLabel:
        """
        Adds a label within the toolbox.
        """
        self.addSpacing(10)
        self._directory_label = QLabel(text)
        self.addWidget(self._directory_label)
        return self._directory_label

    def add_menu_button(
        self,
        icon_path: str,
        tooltip: str,
        menu: QMenu,
        *,
        fixed_size: tuple[int, int] = (24, 24),
        icon_size: tuple[int, int] = (16, 16),
    ) -> ToolbarButton:
        """
        Adds a flat toolbar button that displays a dropdown QMenu directly
        beneath it.
        """
        btn = ToolbarButton(
            icon_path,
            tooltip,
            fixed_size=fixed_size,
            icon_size=icon_size,
        )

        def trigger_dropdown():
            if self.parentWidget():
                menu.setStyleSheet(self.parentWidget().styleSheet())
            bottom_left_vector = btn.rect().bottomLeft()
            global_popup_point = btn.mapToGlobal(bottom_left_vector)
            menu.exec(global_popup_point)

        btn.clicked.connect(trigger_dropdown)

        self._buttons.append(btn)
        self.addWidget(btn)
        return btn

    def add_stretch(self) -> None:
        self.addStretch()
