from editor import *

from editor.utils.panel_shell import PanelShell

ICONS = "assets/toolbox"

common_tools = [
    ("Label", f"{ICONS}/label.png"),
    ("Video", f"{ICONS}/video.png"),
    ("Image", f"{ICONS}/image.png"),
    ("Button", f"{ICONS}/button.png"),
    ("Switch", f"{ICONS}/switch.png"),
    ("Slider", f"{ICONS}/slider.png"),
    ("CheckBox", f"{ICONS}/checkbox.png"),
    ("Text Input", f"{ICONS}/text.png"),
    ("Progress Bar", f"{ICONS}/progress.png"),
    ("Toggle Btn", f"{ICONS}/toggle.png"),
]

layouts = [
    ("Box Layout", f"{ICONS}/newsol.png"),
    ("Page Layout", f"{ICONS}/opensol.png"),
    ("Float Layout", f"{ICONS}/opensol.png"),
    ("Stack Layout", f"{ICONS}/container.png"),
    ("Anchor Layout", f"{ICONS}/lock.png"),
    ("Scatter Layout", f"{ICONS}/find.png"),
    ("Relative Layout", f"{ICONS}/theme.png"),
]

complex_ui = [
    ("Popup", f"{ICONS}/notificaiton.png"),
    ("Bubble", f"{ICONS}/info.png"),
    ("Spinner", f"{ICONS}/replay.png"),
    ("Video Player", f"{ICONS}/run.png"),
    ("File Chooser", f"{ICONS}/folder.png"),
    ("Tabbed Panel", f"{ICONS}/config.png"),
    ("Recycle Viewer", f"{ICONS}/trash.png"),
    ("Drop-Down List", f"{ICONS}/opensol.png"),
    ("Virtual Keyboard", f"{ICONS}/terminal.png"),
]

ICON_SIZE = QSize(28, 28)


class ToolBox(PanelShell):
    PANEL_OBJECT_NAME = "ToolBox"
    TITLE_OBJECT_NAME = "PropertiesTitle"
    DIRECTORY_LABEL_OBJECT_NAME = "PropertiesObjectLabel"
    TITLE_TEXT = "Toolbox"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(104)
        self.setStyleSheet("border: 1px solid #636363;")

    def _header_right_widgets(self) -> list[QWidget]:
        return []

    def _build_shell(self) -> None:
        MAX_COLUMNS = 2
        self.section_widgets = []

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(8, 5, 5, 5)

        sections = [
            ("COMMON", common_tools),
            ("LAYOUTS", layouts),
            ("COMPLEX UI", complex_ui),
        ]

        for section_title, tool_list in sections:
            label = QLabel(section_title)
            label.setStyleSheet(
                "background-color: transparent; font-size: 12px; border: none;"
            )
            scroll_layout.addWidget(label)

            grid = QGridLayout()
            grid.setAlignment(Qt.AlignmentFlag.AlignTop)
            grid.setSpacing(4)

            section_buttons = []
            for i, (tool_name, icon_path) in enumerate(tool_list):
                row = i // MAX_COLUMNS
                col = i % MAX_COLUMNS

                btn = QToolButton()
                btn.setFixedSize(40, 40)
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(ICON_SIZE)
                btn.setStyleSheet("border: none;")
                btn.setToolTip(tool_name)
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

                grid.addWidget(btn, row, col)
                section_buttons.append((tool_name, btn))

            scroll_layout.addLayout(grid)
            self.section_widgets.append((label, grid, section_buttons))

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)
