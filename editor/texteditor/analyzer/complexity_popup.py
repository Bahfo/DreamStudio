from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel


class ComplexityPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self._bg = "#252526"
        self._border = "#3C3C3C"
        self._fg = "#D4D4D4"
        self._accent = "#569CD6"
        self._err_color = "#F44747"
        self._ok_color = "#89D185"

        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self._bg};
                border: 1px solid {self._border};
                border-radius: 4px;
            }}
            QLabel {{ border: none; font-family: 'Segoe UI', sans-serif; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        self.file_label = QLabel("File")
        self.file_label.setStyleSheet(
            f"color: {self._accent}; font-size: 12px; font-weight: bold;"
        )

        self.status_label = QLabel("✓ Clean")
        self.status_label.setStyleSheet(f"color: {self._ok_color}; font-size: 11px;")

        header_layout.addWidget(self.file_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        layout.addLayout(header_layout)

        self.metrics_label = QLabel("CC: - | Depth: -")
        self.metrics_label.setStyleSheet(f"color: {self._fg}; font-size: 11px;")
        layout.addWidget(self.metrics_label)

    def set_results(self, results: dict):
        self.file_label.setText(results.get("file", "<input>"))

        cc = results.get("cyclomatic_complexity", 1)
        nd = results.get("max_nesting_depth", 0)
        self.metrics_label.setText(f"Complexity: {cc}  |  Nesting Depth: {nd}")

        issues = (
            len(results.get("security_warnings", []))
            + len(results.get("missing_docstrings", []))
            + results.get("bare_except_warnings", 0)
        )

        if issues > 0:
            self.status_label.setText(f"⚠️ {issues} Issues")
            self.status_label.setStyleSheet(
                f"color: {self._err_color}; font-size: 11px; font-weight: bold;"
            )
        else:
            self.status_label.setText("✓ Clean")
            self.status_label.setStyleSheet(
                f"color: {self._ok_color}; font-size: 11px; font-weight: bold;"
            )

        self.adjustSize()

    def retheme(self, t) -> None:
        self._bg = t.color("tooltip.background", self._bg)
        self._border = t.color("widget.border", self._border)
        self._fg = t.color("tooltip.text", self._fg)
        self._accent = t.color("widget.accent", self._accent)
        self._err_color = t.color("terminal.error", self._err_color)
        self._ok_color = t.color("terminal.success", self._ok_color)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self._bg};
                border: 1px solid {self._border};
                border-radius: 4px;
            }}
            QLabel {{ border: none; font-family: 'Segoe UI', sans-serif; }}
        """)
        self.file_label.setStyleSheet(
            f"color: {self._accent}; font-size: 12px; font-weight: bold;"
        )
        self.metrics_label.setStyleSheet(f"color: {self._fg}; font-size: 11px;")

    def show_at(self, point: QPoint):
        self.adjustSize()
        self.move(point)
        self.show()
        self.raise_()