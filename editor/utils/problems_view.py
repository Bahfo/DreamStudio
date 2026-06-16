from typing import Optional, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPushButton
)


class _FocusClearTable(QTableWidget):
    def focusOutEvent(self, event):
        self.clearSelection()
        super().focusOutEvent(event)


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
        self._selection_bg = "rgba(128, 128, 128, 0.25)"
        self._grid_border = "#444444"

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
            QTableWidget::item {{
                border-right: 1px solid {self._grid_border};
                padding: 2px 6px;
            }}
            QTableWidget::item:selected {{
                background-color: {self._selection_bg};
                color: {self._fg};
            }}
            QTableWidget::item:hover {{
                background-color: {self._selection_bg};
            }}
            QHeaderView::section {{
                background-color: {self._header_bg};
                color: {self._header_fg};
                padding: 6px;
                border: none;
                border-right: 1px solid {self._grid_border};
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton {{
                background: transparent;
                border: 1px solid {self._header_bg};
                color: {self._header_fg};
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {self._header_bg};
            }}
        """)

    def _build_ui(self) -> None:
        self._apply_stylesheet()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.problems_table = self._create_table(
            ["Severity", "Description", "Line", "Col", "Go To"]
        )
        self.problems_table.setColumnWidth(2, 50)
        self.problems_table.setColumnWidth(3, 50)
        self.problems_table.setColumnWidth(4, 50)
        self.problems_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )

        self.functions_table = self._create_table(
            ["Name", "Parameters", "Returns", "Complexity", "Line", "Col"]
        )
        self.functions_table.setColumnWidth(3, 65)
        self.functions_table.setColumnWidth(4, 50)
        self.functions_table.setColumnWidth(5, 50)
        self.functions_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )

        self.classes_table = self._create_table(
            ["Name", "Methods", "Init Params", "Inherits", "Line", "Col"]
        )
        self.classes_table.setColumnWidth(1, 65)
        self.classes_table.setColumnWidth(4, 50)
        self.classes_table.setColumnWidth(5, 50)
        self.classes_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )

        self.tabs.addTab(self.problems_table, "⚠️ Problems")
        self.tabs.addTab(self.functions_table, "ƒ Functions")
        self.tabs.addTab(self.classes_table, "⛃ Classes")

        self.problems_table.cellDoubleClicked.connect(
            lambda r, c: self.goto_definition("problem", r)
        )
        self.functions_table.cellDoubleClicked.connect(
            lambda r, c: self.goto_definition("function", r)
        )
        self.classes_table.cellDoubleClicked.connect(
            lambda r, c: self.goto_definition("class", r)
        )

    def _create_table(self, headers: list) -> _FocusClearTable:
        table = _FocusClearTable()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        return table

    def set_results(self, results: dict) -> None:
        self._populate_problems(results)
        self._populate_functions(results)
        self._populate_classes(results)

    def _populate_problems(self, results: dict) -> None:
        self.problems_table.setRowCount(0)
        row = 0

        for warn in results.get("security_warnings", []):
            self.problems_table.insertRow(row)
            sev_item = QTableWidgetItem("Error")
            sev_item.setForeground(Qt.GlobalColor.red)
            self.problems_table.setItem(row, 0, sev_item)
            self.problems_table.setItem(row, 1, QTableWidgetItem(warn["message"]))
            self.problems_table.setItem(row, 2, QTableWidgetItem(str(warn.get("line", ""))))
            self.problems_table.setItem(row, 3, QTableWidgetItem(str(warn.get("col", ""))))
            self._add_goto_button(row)
            row += 1

        for doc in results.get("missing_docstrings", []):
            self.problems_table.insertRow(row)
            sev_item = QTableWidgetItem("Warning")
            sev_item.setForeground(Qt.GlobalColor.yellow)
            self.problems_table.setItem(row, 0, sev_item)
            self.problems_table.setItem(
                row, 1, QTableWidgetItem(f"Missing documentation for: {doc['name']}")
            )
            self.problems_table.setItem(row, 2, QTableWidgetItem(str(doc.get("line", ""))))
            self.problems_table.setItem(row, 3, QTableWidgetItem(str(doc.get("col", ""))))
            self._add_goto_button(row)
            row += 1

        for be in results.get("bare_except_warnings", []):
            self.problems_table.insertRow(row)
            sev_item = QTableWidgetItem("Warning")
            sev_item.setForeground(Qt.GlobalColor.yellow)
            self.problems_table.setItem(row, 0, sev_item)
            self.problems_table.setItem(
                row, 1, QTableWidgetItem("Bare except statement.")
            )
            self.problems_table.setItem(row, 2, QTableWidgetItem(str(be.get("line", ""))))
            self.problems_table.setItem(row, 3, QTableWidgetItem(str(be.get("col", ""))))
            self._add_goto_button(row)
            row += 1

        self.tabs.setTabText(
            0, f"⚠️ Problems ({self.problems_table.rowCount()})"
        )

    def _add_goto_button(self, row: int) -> None:
        btn = QPushButton("↗")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda checked, r=row: self.goto_definition("problem", r))
        self.problems_table.setCellWidget(row, 4, btn)

    def _populate_functions(self, results: dict) -> None:
        table = self.functions_table
        table.setRowCount(0)
        for i, func in enumerate(results.get("functions", [])):
            table.insertRow(i)
            table.setItem(i, 0, QTableWidgetItem(func.get("name", "")))
            table.setItem(i, 1, QTableWidgetItem(", ".join(func.get("params", []))))
            table.setItem(i, 2, QTableWidgetItem(func.get("returns", "")))
            table.setItem(i, 3, QTableWidgetItem(str(func.get("complexity", ""))))
            table.setItem(i, 4, QTableWidgetItem(str(func.get("line", ""))))
            table.setItem(i, 5, QTableWidgetItem(str(func.get("col", ""))))

        self.tabs.setTabText(
            1, f"ƒ Functions ({table.rowCount()})"
        )

    def _populate_classes(self, results: dict) -> None:
        table = self.classes_table
        table.setRowCount(0)
        for i, cls in enumerate(results.get("classes", [])):
            table.insertRow(i)
            table.setItem(i, 0, QTableWidgetItem(cls.get("name", "")))
            table.setItem(i, 1, QTableWidgetItem(str(cls.get("num_methods", 0))))
            table.setItem(i, 2, QTableWidgetItem(", ".join(cls.get("init_params", []))))
            bases = cls.get("base_classes", [])
            table.setItem(i, 3, QTableWidgetItem(", ".join(bases) if bases else "None"))
            table.setItem(i, 4, QTableWidgetItem(str(cls.get("line", ""))))
            table.setItem(i, 5, QTableWidgetItem(str(cls.get("col", ""))))

        self.tabs.setTabText(
            2, f"⛃ Classes ({table.rowCount()})"
        )

    def retheme(self, t) -> None:
        bg = t.color("terminal.background", self._bg)
        fg = t.color("terminal.text", self._fg)
        border = t.color("widget.border", self._border)

        is_dark_light = t.name in ("dark", "light")
        if is_dark_light:
            self._header_bg = "#0062BF"
            self._header_fg = "#FFFFFF"
            self._selection_bg = "rgba(128, 128, 128, 0.20)"
        else:
            self._header_bg = t.color("treeview.header_bg", "#0062BF")
            self._header_fg = t.color("treeview.header_text", self._fg)
            self._selection_bg = t.color(
                "treeview.selection_bg", "rgba(128, 128, 128, 0.25)"
            )

        self._grid_border = border
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

    def goto_definition(self, table_source: str, row: int) -> None:
        editor = self._get_active_editor()
        if not editor:
            return

        if table_source == "function":
            item = self.functions_table.item(row, 4)
        elif table_source == "class":
            item = self.classes_table.item(row, 4)
        else:
            item = self.problems_table.item(row, 2)

        if item and item.text():
            line = int(item.text()) - 1
            editor.setCursorPosition(line, 0)
            editor.ensureLineVisible(line)
