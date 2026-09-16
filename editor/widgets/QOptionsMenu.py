from editor import *

from editor.utils.resource_path import resource_path

class ToolbarMenuButton(QPushButton):
    """
    A custom dropdown menu button with a far-right arrow indicator
    that updates its text to show the currently selected option.
    """

    def __init__(
        self,
        text: str = "",
        icon_path: str = None,
        tooltip: str = "",
        fixed_size: tuple[int, int] = (65, 26),
        icon_size: tuple[int, int] = (16, 16),
    ) -> None:
        super().__init__()
        self.setFixedSize(QSize(*fixed_size))
        self.setToolTip(tooltip)

        self.setStyleSheet("QPushButton::menu-indicator { image: none; }")

        button_layout = QHBoxLayout(self)
        button_layout.setContentsMargins(6, 0, 6, 0)
        button_layout.setSpacing(4)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        if icon_path and os.path.exists(resource_path(icon_path)):
            self.icon_label = QLabel()
            self.icon_label.setPixmap(QIcon(resource_path(icon_path)).pixmap(QSize(*icon_size)))
            button_layout.addWidget(self.icon_label)
            icon_w = icon_size[0]
        else:
            self.icon_label = None
            icon_w = 0

        self.text_label = QLabel()
        button_layout.addWidget(self.text_label)

        button_layout.addStretch(1)

        self.arrow_label = QLabel("▸")
        button_layout.addWidget(self.arrow_label)

        arrow_w = self.fontMetrics().horizontalAdvance("▸")
        margins_and_spacing = 12 + 4 * (2 if icon_w > 0 else 1) + 4
        self.max_text_width = fixed_size[0] - icon_w - arrow_w - margins_and_spacing

        if text:
            self.update_button_text(text)

        self.menu = QMenu(self)
        self.setMenu(self.menu)

        self.menu.aboutToShow.connect(self._on_menu_open)
        self.menu.aboutToHide.connect(self._on_menu_close)
        self.menu.triggered.connect(self._on_action_triggered)

    def update_button_text(self, text: str) -> None:
        """Safely elides text if it exceeds the maximum safe display boundary size."""
        fm = self.fontMetrics()
        elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, self.max_text_width)
        self.text_label.setText(elided)

    def _on_action_triggered(self, action: QAction) -> None:
        """Intercepts selected item triggers and overrides main button display face text."""
        if action and not action.isSeparator():
            self.update_button_text(action.text())

    def _on_menu_open(self) -> None:
        self.arrow_label.setText("▾")

    def _on_menu_close(self) -> None:
        self.arrow_label.setText("▸")
