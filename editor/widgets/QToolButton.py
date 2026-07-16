from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon


class ToolbarButton(QPushButton):
    """
    A small, flat icon button used to construct DreamStudio menus.

    Parameters:
        - `icon_path` of type `str` points to button's icon path.
        - `icon_size` of type `tuple` sets the image sizes.
        - `fixed_size` of type `tuple` sets the button sizes.
        - `tooltip` of type `str` sets the tooltip.
        - `callback` if any function (method) is called.
    """

    def __init__(
        self,
        icon_path: str,
        tooltip: str,
        fixed_size: tuple[int, int] = (26, 26),
        icon_size: tuple[int, int] = (16, 16),
        callback=None,
    ) -> None:
        super().__init__()
        self.setFixedSize(QSize(*fixed_size))
        self.setIcon(QIcon(icon_path))
        self.setIconSize(QSize(*icon_size))
        self.setToolTip(tooltip)
        if callback:
            self.clicked.connect(callback)
