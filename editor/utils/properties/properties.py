from editor import *
from editor.utils.resource_path import resource_path

from editor.utils.properties.env import *
from editor.utils.panel_shell import PanelShell
from editor.Ironica.code_editor import CodeEditor
from editor.utils.properties.env import LanguageAnalyzer
from editor.widgets.QToolBox import ExplorerToolbar, ToolbarButton
from editor.utils.properties.properties_dialog import (
    FilePropertiesGrid,
    SolutionPropertiesGrid,
)
from editor.utils.properties.project_data_engine import ProjectDataEngine


class PropertiesExplorer(PanelShell):
    PANEL_OBJECT_NAME = "PropertiesExplorer"
    FRAME_OBJECT_NAME = "PropertiesFrame"
    TITLE_OBJECT_NAME = "PropertiesTitle"
    DIRECTORY_LABEL_OBJECT_NAME = "PropertiesObjectLabel"
    TITLE_TEXT = "Properties"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(235)

        self.current_project_dir = None
        self.data_engine = ProjectDataEngine()

        self._setup_focus_tracking()

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
                try:
                    w = w.parent()
                except (TypeError, RuntimeError):
                    break
        self._frame.setProperty("focused", focused)
        self._frame.style().unpolish(self._frame)
        self._frame.style().polish(self._frame)

        if not focused and hasattr(self, "env_tree"):
            self.env_tree.clearSelection()
        if not focused and hasattr(self, "file_grid"):
            self.file_grid.clearSelection()

    def _build_shell(self) -> None:
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._frame = QFrame(self)
        self._frame.setObjectName(self.FRAME_OBJECT_NAME)
        self._frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._frame_layout = QVBoxLayout(self._frame)
        self._frame_layout.setContentsMargins(4, 4, 4, 4)
        self._frame_layout.setSpacing(4)
        self._main_layout.addWidget(self._frame)

        self._build_header_row()
        self._build_toolbar_row()
        self._build_body()

    def _header_right_widgets(self) -> list[QWidget]:
        return [
            ToolbarButton(
                resource_path("editor/utils/explorer/assets/icons/dropdown.png"),
                "View more options",
                (20, 20),
                (15, 15),
            ),
        ]

    def _build_toolbar_row(self) -> None:
        self._toolbar_row = QHBoxLayout()
        self._toolbar_row.setContentsMargins(2, 0, 2, 0)
        self._toolbar_row.setSpacing(4)
        self._toolbar_row.addStretch(1)

        self._explr_toolbox = ExplorerToolbar()
        self._toolbar_row.addLayout(self._explr_toolbox)
        self._frame_layout.addLayout(self._toolbar_row)

    def _build_body(self) -> None:
        self.tabs_container = QTabWidget(self)
        self.tabs_container.setObjectName("PropertiesTabWidget")
        self.tabs_container.setStyleSheet("QTabWidget::pane { border: 0px; }")

        self.solution_tab = QWidget()
        self.file_tab = QWidget()

        self.tabs_container.addTab(self.solution_tab, "Solution Properties")
        self.tabs_container.addTab(self.file_tab, "File Properties")
        self._frame_layout.addWidget(self.tabs_container)

        self._initialize_solution_tab()
        self._initialize_file_tab()

    def _initialize_solution_tab(self) -> None:
        tab_layout = QVBoxLayout(self.solution_tab)
        tab_layout.setContentsMargins(0, 4, 0, 0)
        tab_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet(
            "QSplitter::handle { background-color: #3E3E42; height: 2px; }"
        )

        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(4, 0, 4, 0)
        top_layout.setSpacing(4)
        top_layout.addSpacing(10)

        global_label = QLabel("Properties")
        top_layout.addWidget(global_label)

        self.env_tree = QTreeWidget()
        self.env_tree.setObjectName("PropertiesEnvTree")
        self.env_tree.setColumnCount(2)
        self.env_tree.setHeaderHidden(True)
        self.env_tree.setFrameShape(QFrame.Shape.NoFrame)
        self.env_tree.setAnimated(True)
        self.env_tree.setIndentation(12)
        self.env_tree.setRootIsDecorated(True)
        self.env_tree.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.env_tree.setMouseTracking(True)
        self.env_tree.setStyleSheet(
            "QTreeView { border: none; background: transparent; }"
        )

        hdr = self.env_tree.header()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.env_tree.setColumnWidth(0, 140)

        self.env_tree.installEventFilter(self)
        self._populate_python_info()
        top_layout.addWidget(self.env_tree)

        splitter.addWidget(top_container)
        self.config_grid = SolutionPropertiesGrid(self)
        self.config_grid.itemChanged.connect(self._on_config_property_changed)
        splitter.addWidget(self.config_grid)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        tab_layout.addWidget(splitter)

    def _initialize_file_tab(self) -> None:
        layout = QVBoxLayout(self.file_tab)
        layout.setContentsMargins(4, 4, 4, 0)
        layout.setSpacing(4)

        file_label = QLabel("Active Object Metrics")
        layout.addWidget(file_label)

        self.file_grid = FilePropertiesGrid(self.file_tab)
        layout.addWidget(self.file_grid, 1)

    def set_active_project_directory(self, project_dir: str) -> None:
        """
        Invoked by the main IDE layout infrastructure when switching workspaces.
        """
        self.current_project_dir = project_dir
        self.data_engine.set_project_dir(project_dir)

        if self.data_engine.is_valid_project() and hasattr(self, "config_grid"):
            self.config_grid.blockSignals(True)
            project_data = self.data_engine.extract_solution_properties()
            self.config_grid.load_grid_data(project_data)
            self.config_grid.blockSignals(False)

    def _on_config_property_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Listens directly to the grid inputs to save modified values straight to disk."""
        if column != 1 or not self.data_engine.is_valid_project():
            return
        if not hasattr(self, "config_grid"):
            return

        updated_payload = self.config_grid.save_grid_data()
        self.data_engine.commit_solution_properties(updated_payload)

        item.setToolTip(1, item.text(1) if item.text(1) else "--")

    def eventFilter(self, source, event) -> bool:
        if source is self.env_tree and event.type() == QEvent.Type.MouseButtonPress:
            click_pos = event.position().toPoint()
            if self.env_tree.itemAt(click_pos) is None:
                self.env_tree.clearSelection()
                return True
        return super().eventFilter(source, event)

    def analyze_languages(self) -> LanguageAnalyzer:
        analysis_widget = LanguageAnalyzer()
        analysis_widget.analyze_directory(os.curdir)
        return analysis_widget

    def _populate_python_info(self) -> None:
        sections = [
            ("Interpreter", get_interpreter_info()),
            ("Languages", self.analyze_languages()),
        ]

        for section_title, data in sections:
            parent = QTreeWidgetItem(self.env_tree)
            parent.setText(0, section_title)
            parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            parent.setExpanded(False)

            if isinstance(data, QWidget):
                child = QTreeWidgetItem(parent)
                child.setText(0, "")
                child.setSizeHint(0, QSize(200, 65))
                child.setFirstColumnSpanned(True)

                self.env_tree.setItemWidget(child, 0, data)

            elif isinstance(data, dict):
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
                            t in key.lower()
                            for t in (
                                "executable",
                                "prefix",
                                "stdlib",
                                "purelib",
                                "path",
                                "dir",
                            )
                        ):
                            child.setText(1, self._elide_string(text))
                            child.setToolTip(1, text)
                        else:
                            child.setText(1, text)
                            child.setToolTip(1, text)

    def set_active_editor(self, editor: CodeEditor | None) -> None:
        """
        Public API method for the main IDE window to update the explorer's
        active file focus.
        """
        if hasattr(self, "file_grid"):
            self.file_grid.set_active_editor(editor)

    @staticmethod
    def _elide_path_list(paths: list[str]) -> str:
        return "\n".join(PropertiesExplorer._elide_string(p) for p in paths)

    @staticmethod
    def _elide_string(text: str, max_len: int = 60) -> str:
        if len(text) <= max_len:
            return text
        return f"{text[:30]}...{text[-20:]}"
