"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Blocking modal progress dialog shown over the IDE while a new solution is
being scaffolded in the background thread. The dialog reflects step/progress
signals from the ProjectBootstrapWorker and supports a safe user cancel that
stops work at the current point without rolling back partial structure.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from editor.utils.solution.theme import center_on_screen_show, inherit_theme


class QScaffoldProgressDialog(QDialog):
    """Modal dialog mirroring a running scaffolding operation.

    Attributes:
        success (bool): True only when the worker finished successfully.
        cancelled (bool): True when the user requested a safe cancel.
        failed (bool): True when the worker reported an error.
    """

    def __init__(self, parent=None, title="Creating Project", description="") -> None:
        """Build the progress dialog.

        Args:
            parent: Parent widget (the revealed DreamStudio main window).
            title: Dialog window title.
            description: Human-readable operation description (project type).
        """
        super().__init__(parent)
        self.success = False
        self.cancelled = False
        self.failed = False

        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        heading = QLabel(description)
        heading.setObjectName("ScaffoldHeading")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        self._step_label = QLabel("Initializing...")
        self._step_label.setObjectName("ScaffoldStep")
        self._step_label.setWordWrap(True)
        layout.addWidget(self._step_label)

        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress.setFixedHeight(8)
        layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("ScaffoldProgress")
        self._progress_label.setWordWrap(True)
        layout.addWidget(self._progress_label)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._request_cancel)
        layout.addWidget(self._cancel_btn, 0, Qt.AlignmentFlag.AlignRight)

        styled = inherit_theme(self)
        if not styled:
            self._apply_style()

    def showEvent(self, event) -> None:
        """Center the dialog on the screen each time it is shown."""
        center_on_screen_show(self, event)

    # ------------------------------------------------------------------
    # Binding
    # ------------------------------------------------------------------

    def bind(self, bootstrap) -> None:
        """Connect a ProjectBootstrap instance's signals to the dialog.

        Args:
            bootstrap: The scaffold-running ProjectBootstrap instance.
        """
        bootstrap.step_changed.connect(self._on_step_changed)
        bootstrap.step_progress.connect(self._on_step_progress)
        bootstrap.step_failed.connect(self._on_step_failed)
        bootstrap.cancelled.connect(self._on_cancelled)
        bootstrap.finished.connect(self._on_finished)
        self._cancel_btn.clicked.connect(bootstrap.request_cancel)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_step_changed(self, _name: str, description: str) -> None:
        self._step_label.setText(description)

    def _on_step_progress(self, text: str) -> None:
        self._progress_label.setText(text)
        self._progress.setValue((self._progress.value() + 1) % 1000)

    def _on_step_failed(self, _step: str, _error: str) -> None:
        self.failed = True
        self._step_label.setText("Scaffolding failed — rolling back changes...")

    def _on_cancelled(self) -> None:
        self.cancelled = True
        self._step_label.setText("Cancelled — keeping the created structure as-is.")
        self._cancel_btn.setEnabled(False)

    def _on_finished(self, success: bool) -> None:
        self.success = success
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        if not self.cancelled:
            self._cancel_btn.setEnabled(False)
        self.accept()

    def _request_cancel(self) -> None:
        """Allow the cancel button to trigger the worker's safe stop."""
        self.cancel_clicked = True
        self._cancel_btn.setEnabled(False)
        self._step_label.setText("Stopping after the current step...")

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1e1e2e;
            }
            QLabel {
                color: #cdd6f4;
            }
            QLabel#ScaffoldHeading {
                color: #89b4fa;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel#ScaffoldStep {
                color: #cdd6f4;
                font-size: 13px;
            }
            QLabel#ScaffoldProgress {
                color: #a6adc8;
                font-size: 12px;
            }
            QProgressBar {
                background-color: #313244;
                border: none;
                border-radius: 4px;
                color: #cdd6f4;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                color: #cdd6f4;
                padding: 7px 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
            """
        )
