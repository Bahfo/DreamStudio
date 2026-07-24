"""
RecoveryWindow: displays unrecoverable startup failures.

Uses assets/error_crash.svg as a full-window background with overlaid
widgets for the error details textbox and action buttons.
"""

import logging
import os
import traceback

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QMainWindow,
    QPushButton,
    QTextEdit,
    QApplication,
)

logger = logging.getLogger(__name__)

_ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
)
_SVG_PATH = os.path.join(_ASSETS_DIR, "error_crash.svg")


class RecoveryWindow(QMainWindow):
    """Window shown when startup fails critically.

    Renders error_crash.svg as the full background and overlays a
    scrollable textbox for the error details plus Retry/Quit buttons.
    """

    _W, _H = 800, 533

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
        self._renderer = QSvgRenderer(_SVG_PATH)
        self.setWindowTitle(title)
        self.setFixedSize(self._W, self._H)
        self.setWindowFlags(Qt.WindowType.Window)
        self._build_ui()
        logger.warning("RecoveryWindow created: %s", message)

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        if self._renderer.isValid():
            self._renderer.render(painter)
        else:
            painter.fillRect(0, 0, self._W, self._H, Qt.GlobalColor.darkBlue)
        painter.end()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        text_content = self._message
        if self._details:
            if text_content:
                text_content += "\n\n"
            text_content += self._details

        # -- Error details textbox (between the two SVG label lines) --
        self._text_edit = QTextEdit(self)
        self._text_edit.setReadOnly(True)
        self._text_edit.setPlainText(text_content)
        self._text_edit.setGeometry(48, 232, 704, 180)
        self._text_edit.setStyleSheet(
            "QTextEdit {"
            "  background: transparent;"
            "  color: #c8c8c8;"
            "  border: none;"
            "  font-family: Consolas, monospace;"
            "  font-size: 10pt;"
            "  selection-background-color: #1a5276;"
            "}"
            "QScrollBar:vertical {"
            "  background: transparent;"
            "  width: 3px;"
            "  margin: 0;"
            "}"
            "QScrollBar::handle:vertical {"
            "  background: rgba(255,255,255,0.15);"
            "  border-radius: 1px;"
            "  min-height: 20px;"
            "}"
            "QScrollBar::add-line:vertical,"
            "QScrollBar::sub-line:vertical {"
            "  height: 0;"
            "  border: none;"
            "}"
            "QScrollBar::add-page:vertical,"
            "QScrollBar::sub-page:vertical {"
            "  background: none;"
            "}"
        )

        # -- Retry button (right side, above the causality-fix text) --
        retry_btn = QPushButton("Retry", self)
        retry_btn.setGeometry(560, 430, 100, 32)
        retry_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: rgba(255,255,255,0.18);"
            "  color: white;"
            "  border: 1px solid rgba(255,255,255,0.3);"
            "  border-radius: 4px;"
            "  font-size: 11px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover {"
            "  background-color: rgba(255,255,255,0.28);"
            "}"
            "QPushButton:pressed {"
            "  background-color: rgba(255,255,255,0.10);"
            "}"
        )
        retry_btn.clicked.connect(self._on_retry)

        # -- Quit button (right side, next to Retry) --
        quit_btn = QPushButton("Quit", self)
        quit_btn.setGeometry(672, 430, 80, 32)
        quit_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: rgba(255,255,255,0.08);"
            "  color: #cccccc;"
            "  border: 1px solid rgba(255,255,255,0.2);"
            "  border-radius: 4px;"
            "  font-size: 11px;"
            "}"
            "QPushButton:hover {"
            "  background-color: rgba(255,255,255,0.16);"
            "  color: white;"
            "}"
            "QPushButton:pressed {"
            "  background-color: rgba(255,255,255,0.06);"
            "}"
        )
        quit_btn.clicked.connect(self._on_quit)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

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
