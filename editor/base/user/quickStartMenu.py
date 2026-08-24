from editor import *

class QuickStartMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)

        self.set_main_menu()

    def set_main_menu(self):
        """Initializes the main shortcuts menu"""

        self._layout.addStretch()

        self.dreamstudio_logo = QLabel()
        self.dreamstudio_logo.setPixmap(QPixmap("assets/ds_gray.png"))
        self.dreamstudio_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.dreamstudio_logo)

        self._layout.addSpacing(24)

        self.shortcuts_container = QWidget()
        container_layout = QVBoxLayout(self.shortcuts_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)

        shortcuts_data = [
            ("Open File", "Ctrl + O"),
            ("Open Folder", "Ctrl + Shift + O"),
            ("Show All Commands", "Ctrl + Shift + P"),
            ("New Project", "Ctrl + Alt + P"),
        ]

        for text, key in shortcuts_data:
            item = ShortCutLabel(text, key)
            container_layout.addWidget(item)

        self.shortcuts_container.setFixedWidth(320)

        self._layout.addWidget(
            self.shortcuts_container, alignment=Qt.AlignmentFlag.AlignCenter
        )

        self._layout.addStretch()


class ShortCutLabel(QWidget):
    """
    Quickly-made shortcut label for showing data with shortcut
    """

    def __init__(self, text: str = "", shortcut: str = "", parent=None):
        super().__init__(parent)
        self._init_ui()
        self.setText(text)
        self.setShortcut(shortcut)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.label = QLabel()
        self.label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        self.shortcut_label = QLabel()
        self.shortcut_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.shortcut_label.setStyleSheet("""
            QLabel {
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 2px 6px;
                font-family: monospace;
            }
        """)

        layout.addWidget(self.label)
        layout.addWidget(self.shortcut_label)

    def setText(self, text: str):
        self.label.setText(text)

    def setShortcut(self, shortcut: str):
        self.shortcut_label.setText(shortcut)
        self.shortcut_label.setVisible(bool(shortcut))

    def text(self) -> str:
        return self.label.text()

    def shortcut(self) -> str:
        return self.shortcut_label.text()
