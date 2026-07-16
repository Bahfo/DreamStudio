"""
RecoveryWindow: displays unrecoverable startup failures.

Shows human-readable diagnostics and recovery actions.
Never instantiates the entire IDE.
"""

import logging
import traceback

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QApplication,
)

logger = logging.getLogger(__name__)


class RecoveryWindow(QMainWindow):
    """Minimal window shown when startup fails critically."""

    def __init__(
        self,
        title: str = "DreamStudio - Startup Error",
        message: str = "An unrecoverable error occurred during startup.",
        details: str = "",
        recovery_actions: list[tuple[str, callable]] | None = None,
    ) -> None:
        super().__init__()
        self._recovery_actions = recovery_actions or []
        self._message = message
        self._details = details
        self.setWindowTitle(title)
        self.setMinimumSize(600, 420)
        self.setWindowFlags(Qt.WindowType.Window)
        self._build_ui()
        logger.warning("RecoveryWindow created: %s", message)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        self.setStyleSheet("background-color: #1a1a2e; color: #e0e0e0;")

        title_label = QLabel("Startup Error")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #e94560;")
        layout.addWidget(title_label)

        msg_label = QLabel(self._message)
        msg_label.setFont(QFont("Segoe UI", 11))
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #cccccc;")
        layout.addWidget(msg_label)

        if self._details:
            details_edit = QTextEdit()
            details_edit.setReadOnly(True)
            details_edit.setFont(QFont("Consolas", 9))
            details_edit.setStyleSheet(
                "background-color: #0f0f23; color: #aaaaaa; border: 1px solid #333333; padding: 8px;"
            )
            details_edit.setText(self._details)
            details_edit.setMaximumHeight(180)
            layout.addWidget(details_edit)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        retry_btn = QPushButton("Retry Startup")
        retry_btn.setStyleSheet(
            "QPushButton { background-color: #0f3460; color: white; padding: 10px 24px; "
            "border: none; border-radius: 4px; font-size: 12px; }"
            "QPushButton:hover { background-color: #1a5276; }"
        )
        retry_btn.clicked.connect(self._on_retry)
        btn_layout.addWidget(retry_btn)

        quit_btn = QPushButton("Quit")
        quit_btn.setStyleSheet(
            "QPushButton { background-color: #333333; color: #cccccc; padding: 10px 24px; "
            "border: none; border-radius: 4px; font-size: 12px; }"
            "QPushButton:hover { background-color: #555555; }"
        )
        quit_btn.clicked.connect(self._on_quit)
        btn_layout.addWidget(quit_btn)

        layout.addLayout(btn_layout)

    def _on_retry(self) -> None:
        for label, action in self._recovery_actions:
            if label == "retry":
                try:
                    action()
                except Exception:
                    logger.error("Recovery retry failed:\n%s", traceback.format_exc())
                return
        logger.warning("No retry action registered")
        self._on_quit()

    def _on_quit(self) -> None:
        app = QApplication.instance()
        if app:
            app.quit()
