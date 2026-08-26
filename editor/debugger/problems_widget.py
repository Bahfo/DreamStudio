from editor import *
from editor.analysis.walker import ProblemsAnalyzer


class ProblemsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["File", "Line", "Message"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setObjectName("problemsTable")
        layout.addWidget(self._table)

    def run_workspace_analysis(self, workspace_root: str) -> None:
        analyzer = ProblemsAnalyzer(workspace_root)
        result = analyzer.return_errors()
        self._populate_table(result)

    def _populate_table(self, result: dict) -> None:
        errors = result.get("errors", [])
        self._table.setRowCount(len(errors))
        for row, err in enumerate(errors):
            file_item = QTableWidgetItem(err.get("file_path", ""))
            line_item = QTableWidgetItem(str(err.get("error_line", "")))
            msg_item = QTableWidgetItem(err.get("error_msg", ""))
            self._table.setItem(row, 0, file_item)
            self._table.setItem(row, 1, line_item)
            self._table.setItem(row, 2, msg_item)

    def clear(self) -> None:
        self._table.setRowCount(0)
