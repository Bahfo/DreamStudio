from typing import Optional, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)


class ComplexityWidget(QWidget):
    def __init__(self, main_window: Optional[Any] = None):
        super().__init__()
        self._main_window = main_window
        self._bg = "#1E1E1E"
        self._border = "#333333"
        self._fg = "#CCCCCC"
        self._header_bg = "#0062BF"
        self._header_fg = "#FFFFFF"
        self._warn_color = "#CCA700"
        self._err_color = "#F44747"
        self._info_color = "#3794FF"

        self._build_ui()

    def _apply_stylesheet(self) -> None:
        tab_bg = "#252526"
        tab_inactive_fg = "#9B9B9B"
        self.setStyleSheet(f"""
            QWidget {{ background-color: {self._bg}; color: {self._fg}; }}
            QTabWidget::pane {{ border: 1px solid {self._border}; top: -1px; }}
            QTabBar::tab {{ background: {tab_bg};
                color: {tab_inactive_fg};
                border: 1px solid {self._border}; padding: 6px 12px; }}
            QTabBar::tab:selected {{ background: {self._bg};
                color: {self._fg};
                border-bottom-color: {self._bg}; font-weight: bold; }}
            QTableWidget {{ border: none; gridline-color: {self._border};
                font-family: 'Inter', 'Segoe UI', sans-serif; }}
            QTableWidget::item:selected {{
                background-color: rgba(255, 255, 255, 0.10);
                color: {self._fg};
            }}
            QTableWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.05);
            }}
            QHeaderView::section {{
                background-color: {self._header_bg};
                color: {self._header_fg};
                padding: 6px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }}
        """)

    def _build_ui(self) -> None:
        self._apply_stylesheet()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.problems_table = self._create_table(["Severity", "Description"])
        self.functions_table = self._create_table(["Function Name", "Type"])
        self.classes_table = self._create_table(["Class Name"])

        self.tabs.addTab(self.problems_table, "⚠️ Problems")
        self.tabs.addTab(self.functions_table, "ƒ Functions")
        self.tabs.addTab(self.classes_table, "⛃ Classes")

        self.problems_table.cellDoubleClicked.connect(
            lambda r, c: self.goto_definition("problem", r, c)
        )
        self.functions_table.cellDoubleClicked.connect(
            lambda r, c: self.goto_definition("function", r, c)
        )
        self.classes_table.cellDoubleClicked.connect(
            lambda r, c: self.goto_definition("class", r, c)
        )

    def _create_table(self, headers: list) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        return table

    def set_results(self, results: dict) -> None:
        self._populate_problems(results)
        self._populate_list(
            self.functions_table, results.get("functions", []), "Function"
        )
        self._populate_list(
            self.classes_table, results.get("classes", [])
        )

    def _populate_problems(self, results: dict) -> None:
        self.problems_table.setRowCount(0)
        row = 0

        for warn in results.get("security_warnings", []):
            self.problems_table.insertRow(row)
            sev_item = QTableWidgetItem("Error")
            sev_item.setForeground(Qt.GlobalColor.red)
            self.problems_table.setItem(row, 0, sev_item)
            self.problems_table.setItem(row, 1, QTableWidgetItem(warn))
            row += 1

        for doc in results.get("missing_docstrings", []):
            self.problems_table.insertRow(row)
            sev_item = QTableWidgetItem("Warning")
            sev_item.setForeground(Qt.GlobalColor.yellow)
            self.problems_table.setItem(row, 0, sev_item)
            self.problems_table.setItem(
                row, 1, QTableWidgetItem(f"Missing documentation for: {doc}")
            )
            row += 1

        be = results.get("bare_except_warnings", 0)
        if be > 0:
            self.problems_table.insertRow(row)
            sev_item = QTableWidgetItem("Warning")
            sev_item.setForeground(Qt.GlobalColor.yellow)
            desc_item = QTableWidgetItem(
                f"Found {be} bare except statement(s)."
            )
            self.problems_table.setItem(row, 0, sev_item)
            self.problems_table.setItem(row, 1, desc_item)

        self.tabs.setTabText(
            0, f"⚠️ Problems ({self.problems_table.rowCount()})"
        )

    def _populate_list(
        self, table: QTableWidget, items: list, item_type: Optional[str] = None
    ) -> None:
        table.setRowCount(0)
        for i, item_name in enumerate(items):
            table.insertRow(i)
            table.setItem(i, 0, QTableWidgetItem(item_name))
            if item_type:
                table.setItem(i, 1, QTableWidgetItem(item_type))

    def retheme(self, t) -> None:
        bg = t.color("terminal.background", self._bg)
        fg = t.color("terminal.text", self._fg)
        border = t.color("widget.border", self._border)

        is_dark_light = t.name in ("dark", "light")
        if is_dark_light:
            self._header_bg = "#0062BF"
            self._header_fg = "#FFFFFF"
        else:
            self._header_bg = t.color("treeview.header_bg", "#0062BF")
            self._header_fg = t.color("treeview.header_text", self._fg)

        self._bg = bg
        self._fg = fg
        self._border = border
        self._apply_stylesheet()

    def _get_active_editor(self) -> Optional[Any]:
        if not self._main_window:
            return None
        tab_editors = getattr(self._main_window, "tab_editors", None)
        if not tab_editors:
            return None
        editor = tab_editors.currentWidget()
        if editor and hasattr(editor, "setCursorPosition"):
            return editor
        return None

    def _navigate_to_symbol(self, editor: Any, keyword: str, name: str) -> None:
        text = editor.text()
        lines = text.split("\n")
        pattern = f"{keyword} {name}"
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(pattern) and (
                len(stripped) == len(pattern)
                or not stripped[len(pattern)].isalnum()
            ):
                editor.setCursorPosition(i, 0)
                editor.ensureLineVisible(i)
                return

    def goto_definition(self, table_source: str, row: int, col: int) -> None:
        editor = self._get_active_editor()
        if not editor:
            return

        if table_source == "function":
            name = self.functions_table.item(row, 0).text()
            self._navigate_to_symbol(editor, "def", name)
        elif table_source == "class":
            name = self.classes_table.item(row, 0).text()
            self._navigate_to_symbol(editor, "class", name)
        elif table_source == "problem":
            desc = self.problems_table.item(row, 1).text()
            editor.setCursorPosition(0, 0)
            editor.ensureLineVisible(0)
