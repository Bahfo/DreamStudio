from editor import *

from editor.utils.panel_shell import PanelShell
from editor.widgets.QToolBox import ToolbarButton

logger = logging.getLogger(__name__)


class TODOSearch(PanelShell):
    PANEL_OBJECT_NAME = "TODOSearch"
    FRAME_OBJECT_NAME = "TODOSearchFrame"
    TITLE_OBJECT_NAME = "TODOSearchTitle"
    TABLE_OBJECT_NAME = "TODOSearchTable"
    TITLE_TEXT = "TODO Search"

    def __init__(self, _parent=None):
        self._theme = None
        super().__init__(_parent)

        # Make the title bold
        title_font = QFont()
        title_font.setBold(True)
        self.title.setFont(title_font)

        main_window = self.window()
        self._base_dir = getattr(main_window, "currentDirectory", os.getcwd())
        self.path_input.setText(self._base_dir)
        self.setMinimumWidth(235)

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

    def _build_body(self) -> None:
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter root directory path here...")
        self.path_input.setFixedHeight(32)
        top_layout.addWidget(self.path_input)

        self.scan_btn = QPushButton("Search TODOs")
        self.scan_btn.setFixedSize(110, 32)
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self.execute_search)
        top_layout.addWidget(self.scan_btn)

        self._frame_layout.addLayout(top_layout)

        self.table = QTableWidget(0, 3)
        self.table.setObjectName(self.TABLE_OBJECT_NAME)
        self.table.setHorizontalHeaderLabels(["File Path", "Line", "TODO Text"])
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.cellDoubleClicked.connect(self.goto_definition)

        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setObjectName("TODOSearchHeader")
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setFixedHeight(28)

        self._frame_layout.addWidget(self.table)

    _TODO_RE = re.compile(r"\btodo\b", re.IGNORECASE)
    _COMMENT_RE = re.compile(r"(?:#|//|--|<!--|%|;|/\*)")
    _TRIPLE_DOUBLE_RE = re.compile(r'"""')
    _TRIPLE_SINGLE_RE = re.compile(r"'''")

    _SKIP_DIRS = frozenset(
        {
            "venv",
            ".venv",
            "env",
            ".env",
            "virtualenv",
            "__pycache__",
            ".git",
            ".svn",
            ".hg",
            "node_modules",
            "bower_components",
            ".idea",
            ".vscode",
            ".tox",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "dist",
            "build",
            ".egg-info",
            "eggs",
            ".eggs",
        }
    )

    def set_base_dir(self, path: str) -> None:
        self._base_dir = os.path.normpath(path)
        self.path_input.setText(self._base_dir)
        self.table.setRowCount(0)

    def _apply_error_border(self) -> None:
        self.path_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid #E81123;
                border-radius: 4px;
            }}
        """)

    def execute_search(self):
        root_dir = os.path.normpath(self.path_input.text().strip())
        base_dir = os.path.normpath(self._base_dir)

        if not os.path.isdir(root_dir):
            self._apply_error_border()
            return

        try:
            common = os.path.commonpath([base_dir, root_dir])
        except ValueError:
            self._apply_error_border()
            return
        if common != base_dir:
            self._apply_error_border()
            return

        self.table.setRowCount(0)
        results = self._search_for_todos(root_dir)
        self.table.setRowCount(len(results))

        import pathlib

        for row_idx, (file_path, line_num, text) in enumerate(results):
            display_path = pathlib.Path(file_path).name
            path_item = QTableWidgetItem(display_path)
            path_item.setData(Qt.ItemDataRole.UserRole, file_path)
            path_item.setToolTip(file_path)
            self.table.setItem(row_idx, 0, path_item)
            line_item = QTableWidgetItem(str(line_num))
            line_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 1, line_item)
            self.table.setItem(row_idx, 2, QTableWidgetItem(text))

    def _search_for_todos(self, root_dir: str) -> list:
        found_todos: list = []
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in self._SKIP_DIRS]
            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    in_triple_double = False
                    in_triple_single = False

                    for line_num, line in enumerate(lines, start=1):
                        stripped = line.strip()

                        is_comment = bool(self._COMMENT_RE.search(stripped))

                        dq_count = stripped.count('"""')
                        sq_count = stripped.count("'''")
                        if is_comment:
                            dq_count = 0
                            sq_count = 0

                        has_todo = bool(self._TODO_RE.search(stripped))
                        on_triple_line = dq_count > 0 or sq_count > 0
                        in_docstring = (
                            in_triple_double or in_triple_single or on_triple_line
                        )

                        if has_todo and (is_comment or in_docstring):
                            found_todos.append((file_path, line_num, stripped))

                        if dq_count % 2 == 1:
                            in_triple_double = not in_triple_double
                        if sq_count % 2 == 1:
                            in_triple_single = not in_triple_single

                except (IOError, OSError, UnicodeDecodeError):
                    pass
        return found_todos

    def goto_definition(self, row: int, column: int) -> None:
        path_item = self.table.item(row, 0)
        file_path = (
            path_item.data(Qt.ItemDataRole.UserRole) or path_item.toolTip() or ""
        )
        line_num = int(self.table.item(row, 1).text())
        main_window = self.window()
        if hasattr(main_window, "tab_editors"):
            main_window.tab_editors.open_file_at_line(file_path, line_num - 1)
