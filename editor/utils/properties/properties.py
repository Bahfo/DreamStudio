from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QFrame,
    QPushButton,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QLabel,
)

from editor.utils.panel_shell import PanelShell
from editor.widgets.QToolBox import ExplorerToolbar, ToolbarButton
from editor.utils.properties.get_env import (
    get_interpreter_info,
    get_interpreter_path,
    get_env_variables,
)


class PropertiesExplorer(PanelShell):
    PANEL_OBJECT_NAME = "PropertiesExplorer"
    FRAME_OBJECT_NAME = "PropertiesFrame"
    TITLE_OBJECT_NAME = "PropertiesTitle"
    DIRECTORY_LABEL_OBJECT_NAME = "PropertiesObjectLabel"
    SEARCH_BAR_OBJECT_NAME = ""
    TREE_VIEW_OBJECT_NAME = ""
    RENAME_EDITOR_OBJECT_NAME = ""
    TITLE_TEXT = "Properties"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_focus_tracking()
        self.setMinimumWidth(350)

    def _setup_focus_tracking(self) -> None:
        QApplication.instance().focusChanged.connect(self._on_app_focus_changed)

    def _on_app_focus_changed(self, old, new) -> None:
        focused = False
        if new is not None:
            w = new
            while w is not None:
                if w is self:
                    focused = True
                    break
                w = w.parent()
        self._frame.setProperty("focused", focused)
        self._frame.style().unpolish(self._frame)
        self._frame.style().polish(self._frame)

        if not focused and hasattr(self, "env_tree"):
            self.env_tree.clearSelection()

    def _build_shell(self) -> None:
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._frame = QFrame(self)
        self._frame.setObjectName(self.FRAME_OBJECT_NAME)
        self._frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._frame_layout = QVBoxLayout(self._frame)
        self._frame_layout.setContentsMargins(10, 10, 10, 10)
        self._frame_layout.setSpacing(8)

        self._main_layout.addWidget(self._frame)

        self._build_header_row()
        self._build_toolbar_row()
        self._build_body()

    def _header_right_widgets(self) -> list[QWidget]:
        return [
            ToolbarButton(
                "editor/utils/explorer/assets/icons/dropdown.png",
                "View more widget options",
                (20, 20),
                (15, 15),
            ),
        ]

    def _build_toolbar_row(self) -> None:
        self._toolbar_row = QHBoxLayout()
        self._toolbar_row.setContentsMargins(0, 0, 0, 0)
        self._toolbar_row.setSpacing(8)
        self._toolbar_row.addStretch(1)

        self._explr_toolbox = ExplorerToolbar()
        self._toolbar_row.addLayout(self._explr_toolbox)

        self._frame_layout.addLayout(self._toolbar_row)

    def _build_body(self) -> None:
        tab_nav_layout = QHBoxLayout()
        tab_nav_layout.setContentsMargins(0, 0, 0, 0)
        tab_nav_layout.setSpacing(4)

        self.btn_python_info = QPushButton("Python Info")
        self.btn_project_info = QPushButton("Project Info")

        tab_nav_layout.addWidget(self.btn_python_info)
        tab_nav_layout.addWidget(self.btn_project_info)
        tab_nav_layout.addStretch()
        self._frame_layout.addLayout(tab_nav_layout)

        self.body_stack = QStackedWidget(self)
        self._frame_layout.addWidget(self.body_stack)

        self.btn_python_info.clicked.connect(
            lambda: self.body_stack.setCurrentIndex(0)
        )
        self.btn_project_info.clicked.connect(
            lambda: self.body_stack.setCurrentIndex(1)
        )

        self._build_python_info_tab()
        self._build_project_info_tab()

    def _build_python_info_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        self.env_tree = QTreeWidget()
        self.env_tree.setObjectName("PropertiesEnvTree")
        self.env_tree.setHeaderLabels(["Property", "Value"])
        self.env_tree.setAnimated(True)
        self.env_tree.setIndentation(4)
        self.env_tree.setRootIsDecorated(True)
        self.env_tree.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.env_tree.setMouseTracking(True)

        hdr = self.env_tree.header()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.env_tree.installEventFilter(self)

        self._populate_python_info()

        layout.addWidget(self.env_tree)
        self.body_stack.addWidget(page)

    def eventFilter(self, source, event) -> bool:
        if source is self.env_tree and event.type() == QEvent.Type.MouseButtonPress:
            click_pos = event.position().toPoint()
            item = self.env_tree.itemAt(click_pos)
            if item is None:
                self.env_tree.clearSelection()
                return True
        return super().eventFilter(source, event)

    def _populate_python_info(self) -> None:
        sections = [
            ("Interpreter", get_interpreter_info()),
            ("Paths", get_interpreter_path()),
            ("Environment", get_env_variables()),
        ]

        for section_title, data in sections:
            parent = QTreeWidgetItem(self.env_tree)
            parent.setText(0, section_title)
            parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            parent.setExpanded(True)

            for key, value in data.items():
                child = QTreeWidgetItem(parent)
                child.setText(0, key)
                if isinstance(value, list):
                    display = self._elide_path_list(value)
                    child.setText(1, display)
                    child.setToolTip(1, "\n".join(value) if value else "--")
                else:
                    text = str(value) if value is not None else "--"
                    if any(
                        term in key.lower()
                        for term in ("executable", "prefix", "stdlib", "purelib", "path", "dir")
                    ):
                        child.setText(1, self._elide_string(text))
                        child.setToolTip(1, text)
                    else:
                        child.setText(1, text)
                        child.setToolTip(1, text)

    @staticmethod
    def _elide_path_list(paths: list[str]) -> str:
        return "\n".join(PropertiesExplorer._elide_string(p) for p in paths)

    @staticmethod
    def _elide_path(parent_path: str) -> str:
        parts = parent_path.replace("\\", "/").split("/")
        if len(parts) <= 3:
            return parent_path
        return parts[0] + "/.../" + parts[-1]

    @staticmethod
    def _elide_string(text: str, max_len: int = 60) -> str:
        if len(text) <= max_len:
            return text
        head = text[:30]
        tail = text[-20:]
        return f"{head}...{tail}"

    def _build_project_info_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        placeholder = QLabel("Project info settings are coming soon.")
        placeholder.setStyleSheet("color: #888888;")
        layout.addWidget(placeholder)

        self.body_stack.addWidget(page)
