"""
UI Views for the Python IDE Features.
Written strictly using PySide6. Fully decoupled from Jedi logic.
"""

from typing import List, Optional
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QLabel,
    QWidget,
    QDialog,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QTreeWidget,
    QListWidgetItem,
    QTreeWidgetItem,
)
from .domain_models import ReferenceLocation, ComplexityReport


class ReferenceViewerWidget(QWidget):
    """
    Custom widget displaying a tree-view of project symbol occurrences.
    Emits navigate_requested whenever a user double-clicks an element.
    """

    # Signal arguments: (file_path, line_number, column_number)
    navigate_requested = pyqtSignal(str, int, int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("Symbol References:")
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Location / Content", "Position"])
        self.tree.setColumnWidth(0, 450)

        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)

        layout.addWidget(self.label)
        layout.addWidget(self.tree)

    def populate_references(self, references: List[ReferenceLocation]) -> None:
        """Loads reference locations into a structured multi-file view tree."""
        self.tree.clear()

        # Group references by file path
        grouped: dict[str, List[ReferenceLocation]] = {}
        for ref in references:
            path = ref.file_path or "Unknown Buffer"
            grouped.setdefault(path, []).append(ref)

        for file_path, locs in grouped.items():
            file_node = QTreeWidgetItem(self.tree)
            file_node.setText(0, file_path)
            file_node.setExpanded(True)

            for ref in locs:
                ref_node = QTreeWidgetItem(file_node)
                ref_node.setText(0, f"Line {ref.line}: {ref.context_line}")
                ref_node.setText(1, f"Col {ref.column}")

                # Store coordinates inside the node metadata to retrieve during double clicks
                ref_node.setData(
                    0, Qt.ItemDataRole.UserRole, (file_path, ref.line, ref.column)
                )

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        coords = item.data(0, Qt.ItemDataRole.UserRole)
        if coords:
            file_path, line, col = coords
            self.navigate_requested.emit(file_path, line, col)


class RefactorDialog(QDialog):
    """
    Prompt interface to accept rename inputs and preview file adjustments.
    """

    def __init__(self, current_name: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.current_name = current_name
        self.confirmed_new_name: Optional[str] = None
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("Rename Symbol")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        self.info_label = QLabel(
            f"Rename all references to variable: <b>{self.current_name}</b>"
        )
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter new identifier...")
        self.input_field.setText(self.current_name)

        buttons_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_ok = QPushButton("Rename")
        self.btn_ok.setDefault(True)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._on_accept_clicked)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_ok)

        layout.addWidget(self.info_label)
        layout.addWidget(self.input_field)
        layout.addLayout(buttons_layout)

    def _on_accept_clicked(self) -> None:
        new_text = self.input_field.text().strip()
        if new_text and new_text != self.current_name:
            self.confirmed_new_name = new_text
            self.accept()
        else:
            self.reject()


class ComplexityDashboard(QWidget):
    """
    Displays code density analysis, class/function metrics, and alerts
    the developer about deeply nested or complex routines.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Overview Stats Header
        self.summary_label = QLabel("<h3>Complexity Analysis</h3>No reports loaded.")
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)

        # Details List View
        self.issues_list = QListWidget()

        layout.addWidget(self.summary_label)
        layout.addWidget(QLabel("<b>Function Breakdown:</b>"))
        layout.addWidget(self.issues_list)

    def render_report(self, report: ComplexityReport) -> None:
        """Updates UI components to match metrics captured in the report."""
        self.issues_list.clear()

        summary = f"""
        <h3>Complexity Overview</h3>
        <table cellspacing="10" style="font-size: 13px;">
          <tr><td><b>Lines of Code:</b></td><td>{report.total_loc}</td></tr>
          <tr><td><b>Classes:</b></td><td>{report.class_count}</td></tr>
          <tr><td><b>Functions:</b></td><td>{report.function_count}</td></tr>
          <tr><td><b>Peak Complexity:</b></td><td><span style="color: {'#FF6B6B' if report.max_cyclomatic_complexity > 10 else '#4EC9B0'}; font-weight: bold;">{report.max_cyclomatic_complexity}</span></td></tr>
        </table>
        """
        self.summary_label.setText(summary)

        # Populate individual functions
        for f in report.functions:
            # Classify function complexity standards (standard metrics state CC > 10 is risky)
            color_prefix = (
                "🟢"
                if f.cyclomatic_complexity <= 4
                else ("🟡" if f.cyclomatic_complexity <= 10 else "🔴")
            )

            item_text = (
                f"{color_prefix} {f.name}() [Line {f.line}] -> "
                f"Complexity: {f.cyclomatic_complexity} | Nesting: {f.nesting_depth}"
            )

            item = QListWidgetItem(item_text, self.issues_list)
            if f.cyclomatic_complexity > 10:
                item.setToolTip(
                    "Refactoring is highly recommended for this function to decrease branch paths."
                )
