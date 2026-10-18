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

