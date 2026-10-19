from editor import *

from editor.utils.resource_path import resource_path
from editor.utils.icons import get_qicon


class ToolbarButton(QPushButton):
    """A small, flat icon button used to construct DreamStudio menus."""

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

        self.setIcon(get_qicon(icon_path) if icon_path else QIcon())
        self.setIconSize(QSize(*icon_size))
        self.setToolTip(tooltip)

        if fixed_size is not None:
            self.setFixedSize(QSize(*fixed_size))
        elif not text:
            self.setFixedSize(QSize(26, 26))

        if callback:
            self.clicked.connect(callback)
