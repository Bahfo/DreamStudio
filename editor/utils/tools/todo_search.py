import os
import re
import logging
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

logger = logging.getLogger(__name__)


class TODOSearch(QWidget):
    def __init__(self, _parent=None):
        super().__init__(_parent)
        self._parent = _parent
        self._theme = None

        main_window = self.window()
        self._base_dir = getattr(main_window, "currentDirectory", os.getcwd())

        self.container = QVBoxLayout(self)
        self.container.setContentsMargins(12, 12, 12, 12)
        self.container.setSpacing(8)

        self.init_ui()

    def init_ui(self):
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)

        self.path_input = QLineEdit()
        self.path_input.setText(self._base_dir)
        self.path_input.setPlaceholderText("Enter root directory path here...")
        self.path_input.setFixedHeight(32)
        top_layout.addWidget(self.path_input)

        self.scan_btn = QPushButton("Search TODOs")
        self.scan_btn.setFixedSize(110, 32)
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self.execute_search)
        top_layout.addWidget(self.scan_btn)

        self.container.addLayout(top_layout)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["File Path", "Line", "TODO Text"])
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.cellDoubleClicked.connect(self.goto_definition)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setFixedHeight(28)

        self.container.addWidget(self.table)

    def retheme(self, t) -> None:
        self._theme = t
        bg = t.color("widget.background", "#252526")
        text = t.color("widget.text", "#CCCCCC")
        border = t.color("widget.border", "#3C3C3C")
        input_bg = t.color("input.background", "#3C3C3C")
        input_text = t.color("input.text", "#D4D4D4")
        input_placeholder = t.color("input.placeholder", "#858585")
        btn_text = t.color("button.text", "#FFFFFF")
        btn_hover = t.color("button.hover", "#333333")
        accent = t.color("widget.accent", "#007ACC")
        table_bg = t.color("treeview.background", "#252526")
        table_text = t.color("treeview.text", "#CCCCCC")
        table_highlight = t.color("treeview.highlight", "#2D476D")
        table_hover = t.color("treeview.hover", "#2D2D2D")
        header_bg = t.color("treeview.header_bg", "#2D2D2D")
        header_text = t.color("treeview.header_text", "#CCCCCC")
        scroll_fg = t.color("scrollbar.fg", "#424242")
        scroll_hover = t.color("scrollbar.hover", "#555555")

        self.setStyleSheet(f"""
            background-color: {bg};
            color: {text};
        """)

        self.path_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
            }}
            QLineEdit::placeholder {{
                color: {input_placeholder};
                font-style: italic;
            }}
        """)

        self.scan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
            QPushButton:pressed {{
                background-color: {accent};
            }}
        """)

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {table_bg};
                color: {table_text};
                border: 1px solid {border};
                border-radius: 4px;
                gridline-color: transparent;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {table_highlight};
                color: white;
            }}
            QTableWidget::item:hover {{
                background-color: {table_hover};
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {header_text};
                border: none;
                border-bottom: 1px solid {border};
                padding: 4px 8px;
                font-weight: bold;
                font-size: 11px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_fg};
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scroll_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
                border: none;
            }}
        """)

    _TODO_RE = re.compile(r'\btodo\b', re.IGNORECASE)
    _COMMENT_RE = re.compile(r'(?:#|//|--|<!--|%|;|/\*)')
    _TRIPLE_DOUBLE_RE = re.compile(r'"""')
    _TRIPLE_SINGLE_RE = re.compile(r"'''")

    _SKIP_DIRS = frozenset({
        "venv", ".venv", "env", ".env", "virtualenv",
        "__pycache__", ".git", ".svn", ".hg",
        "node_modules", "bower_components",
        ".idea", ".vscode", ".tox", ".mypy_cache",
        ".pytest_cache", ".ruff_cache", "dist", "build",
        ".egg-info", " eggs", ".eggs",
    })

    def execute_search(self):
        root_dir = os.path.normpath(self.path_input.text().strip())
        base_dir = os.path.normpath(self._base_dir)

        if not os.path.isdir(root_dir):
            self.path_input.setStyleSheet(
                "border: 1px solid #E81123;"
            )
            return

        if os.path.commonpath([base_dir, root_dir]) != base_dir:
            self.path_input.setStyleSheet(
                "border: 1px solid #E81123;"
            )
            return

        self.table.setRowCount(0)
        results = self._search_for_todos(root_dir)
        self.table.setRowCount(len(results))

        for row_idx, (file_path, line_num, text) in enumerate(results):
            self.table.setItem(row_idx, 0, QTableWidgetItem(file_path))
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
                            found_todos.append(
                                (file_path, line_num, stripped)
                            )

                        if dq_count % 2 == 1:
                            in_triple_double = not in_triple_double
                        if sq_count % 2 == 1:
                            in_triple_single = not in_triple_single

                except (IOError, OSError, UnicodeDecodeError):
                    pass
        return found_todos

    def goto_definition(self, row: int, column: int) -> None:
        file_path = self.table.item(row, 0).text()
        line_num = int(self.table.item(row, 1).text())
        main_window = self.window()
        if hasattr(main_window, "tab_editors"):
            main_window.tab_editors.open_file_at_line(file_path, line_num - 1)
