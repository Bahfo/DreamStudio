"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Indexing progress indicator for DreamStudio.
"""

from editor import *


class IndexingProgress(QWidget):
    """Determinate progress indicator for background indexing jobs."""

    def __init__(self, parent=None) -> None:
        """Build a hidden label-plus-bar row."""
        super().__init__(parent)
        self.setObjectName("IndexingProgress")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.label = QLabel(self)
        self.label.setObjectName("IndexingProgressLabel")
        layout.addWidget(self.label)

        self.bar = QProgressBar(self)
        self.bar.setObjectName("IndexingProgressBar")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(True)
        self.bar.setFixedWidth(140)
        self.bar.setFixedHeight(6)
        layout.addWidget(self.bar)

        self._total = 0
        self.hide()

    def start_indexing(self, total: int, message: str = "") -> None:
        """Show the indicator for a job covering *total* items."""
        self._total = max(1, int(total))
        self.label.setText(
            message or "Please wait while DreamStudio indexes the repository"
        )
        self.bar.setValue(0)
        self.show()

    def advance_indexing(self, done: int) -> None:
        """Move the bar to reflect *done* processed items."""
        done = max(0, min(int(done), self._total))
        self.bar.setValue(round(done / self._total * 100))

    def finish_indexing(self) -> None:
        """Fill the bar and hide the indicator."""
        self.bar.setValue(100)
        self.hide()
        self._total = 0
