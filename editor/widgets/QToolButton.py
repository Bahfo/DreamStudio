from editor import *

from editor.utils.resource_path import resource_path

class ToolbarButton(QPushButton):
    """
    A small, flat icon button used to construct DreamStudio menus.

    Parameters:
        - `icon_path` of type `str` points to button's icon path.
        - `tooltip` of type `str` sets the tooltip.
        - `text` of type `str` sets text displayed to the right of the icon.
        - `fixed_size` of type `tuple` sets fixed dimensions (width, height).
        - `icon_size` of type `tuple` sets the image sizes.
        - `callback` if any function (method) is called.
    """

    def __init__(
        self,
        icon_path: str,
        tooltip: str,
        fixed_size: Optional[tuple[int, int]] = None,
        icon_size: tuple[int, int] = (16, 16),
        callback=None,
        text: str = "",
    ) -> None:
        super().__init__()

        if text:
            self.setText(text)

        self.setIcon(QIcon(resource_path(icon_path)))
        self.setIconSize(QSize(*icon_size))
        self.setToolTip(tooltip)

        if fixed_size is not None:
            self.setFixedSize(QSize(*fixed_size))
        elif not text:
            self.setFixedSize(QSize(26, 26))

        if callback:
            self.clicked.connect(callback)
