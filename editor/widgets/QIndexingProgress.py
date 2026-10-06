"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Indexing progress indicator for DreamStudio.

A small label-plus-bar widget that shows determinate background-job
progress (``done`` of ``total`` items) and hides itself when the job
finishes. The widget owns the percentage math — callers only report raw
counts, never percentages.
"""

from editor import *


class IndexingProgress(QWidget):
    """Determinate progress indicator for background indexing jobs.

    Attributes:
        label: Text shown beside the bar (e.g. the waiting message).
        bar: The underlying ``QProgressBar`` (0-100, determinate).
    """

    def __init__(self, parent=None) -> None:
        """Build a hidden label-plus-bar row.

        Args:
            parent: Optional parent widget.
        """
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
        """Show the indicator for a job covering *total* items.

        Args:
            total: Number of items to process. Values below 1 are treated
                as 1 so division stays defined.
            message: Text shown beside the bar. Defaults to the standard
                repository-indexing message.
        """
        self._total = max(1, int(total))
        self.label.setText(
            message or "Please wait while DreamStudio indexes the repository"
        )
        self.bar.setValue(0)
        self.show()

    def advance_indexing(self, done: int) -> None:
        """Move the bar to reflect *done* processed items.

        Args:
            done: Number of items processed so far. Clamped to the range
                ``[0, total]`` given to :meth:`start_indexing`.
        """
        done = max(0, min(int(done), self._total))
        self.bar.setValue(round(done / self._total * 100))

    def finish_indexing(self) -> None:
        """Fill the bar and hide the indicator."""
        self.bar.setValue(100)
        self.hide()
        self._total = 0
