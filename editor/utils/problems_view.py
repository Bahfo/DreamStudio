from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView
)

class ComplexityWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._bg = "#1E1E1E"
        self._border = "#333333"
        self._fg = "#CCCCCC"
        self._header_bg = "#252526"
        self._warn_color = "#CCA700"
        self._err_color = "#F44747"
        self._info_color = "#3794FF"

        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"""
            QWidget {{ background-color: {self._bg}; color: {self._fg}; }}
            QTabWidget::pane {{ border: 1px solid {self._border}; top: -1px; }}
            QTabBar::tab {{ background: {self._header_bg}; 
                border: 1px solid {self._border}; padding: 6px 12px; }}
            QTabBar::tab:selected {{ background: {self._bg};
                border-bottom-color: {self._bg}; font-weight: bold; }}
            QTableWidget {{ border: none; gridline-color: {self._border}; 
                font-family: 'Consolas', 'Courier New', monospace; }}
            QHeaderView::section {{ background-color: {self._header_bg}; 
                color: {self._fg}; padding: 4px; border: 1px solid {self._border}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Build Tables
        self.problems_table = self._create_table(["Severity", "Description"])
        self.functions_table = self._create_table(["Function Name", "Type"])
        self.classes_table = self._create_table(["Class Name"])

        # Add tabs
        self.tabs.addTab(self.problems_table, "⚠️ Problems")
        self.tabs.addTab(self.functions_table, "ƒ Functions")
        self.tabs.addTab(self.classes_table, "⛃ Classes")

        # Connect double-click signals to our routing method
        self.problems_table.cellDoubleClicked.connect(lambda r, c: self.goto_definition("problem", r, c))
        self.functions_table.cellDoubleClicked.connect(lambda r, c: self.goto_definition("function", r, c))
        self.classes_table.cellDoubleClicked.connect(lambda r, c: self.goto_definition("class", r, c))

    def _create_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        return table

    def set_results(self, results: dict):
        self._populate_problems(results)
        self._populate_list(self.functions_table, results.get("functions", []), "Function")
        self._populate_list(self.classes_table, results.get("classes", []))

    def _populate_problems(self, results):
        self.problems_table.setRowCount(0)
        row = 0
        
        for warn in results.get("security_warnings", []):
            self.problems_table.insertRow(row)
            sev_item = QTableWidgetItem("Error")
            sev_item.setForeground(Qt.GlobalColor.red)
            desc_item = QTableWidgetItem(warn)
            self.problems_table.setItem(row, 0, sev_item)
            self.problems_table.setItem(row, 1, desc_item)
            row += 1

        for doc in results.get("missing_docstrings", []):
            self.problems_table.insertRow(row)
            sev_item = QTableWidgetItem("Warning")
            sev_item.setForeground(Qt.GlobalColor.yellow)
            desc_item = QTableWidgetItem(f"Missing documentation for: {doc}")
            self.problems_table.setItem(row, 0, sev_item)
            self.problems_table.setItem(row, 1, desc_item)
            row += 1
            
        be = results.get("bare_except_warnings", 0)
        if be > 0:
            self.problems_table.insertRow(row)
            sev_item = QTableWidgetItem("Warning")
            sev_item.setForeground(Qt.GlobalColor.yellow)
            desc_item = QTableWidgetItem(f"Found {be} bare except statement(s).")
            self.problems_table.setItem(row, 0, sev_item)
            self.problems_table.setItem(row, 1, desc_item)

        self.tabs.setTabText(0, f"⚠️ Problems ({self.problems_table.rowCount()})")

    def _populate_list(self, table, items, item_type=None):
        table.setRowCount(0)
        for i, item_name in enumerate(items):
            table.insertRow(i)
            table.setItem(i, 0, QTableWidgetItem(item_name))
            if item_type:
                table.setItem(i, 1, QTableWidgetItem(item_type))

    def goto_definition(self, table_source: str, row: int, col: int):
        """
        GOTO METHOD PLACEHOLDER:
        This is triggered when a user double-clicks any cell in the tables.
        You will implement the editor navigation logic here.
        """
        if table_source == "problem":
            item = self.problems_table.item(row, 1).text()
            print(f"Navigate to Problem: {item}")
        elif table_source == "function":
            func_name = self.functions_table.item(row, 0).text()
            print(f"Navigate to Function: {func_name}")
        elif table_source == "class":
            class_name = self.classes_table.item(row, 0).text()
            print(f"Navigate to Class: {class_name}")