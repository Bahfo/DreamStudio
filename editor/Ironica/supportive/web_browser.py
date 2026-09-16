"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Embedded browser widget for rendering HTML file previews inside
DreamStudio tabs via Qt WebEngine.
"""

from editor import *
from editor.utils.resource_path import resource_path
from PyQt6.QtWebEngineWidgets import QWebEngineView

_BTN_STYLE = (
    "QPushButton { background: rgba(128,128,128,40); "
    "border: none; border-radius: 4px; }"
    "QPushButton:hover { background: rgba(128,128,128,90); }"
)


class WebViewer(QWidget):
    """Embedded browser widget that displays an HTML file preview.

    Wraps ``QWebEngineView`` and adds navigation controls
    (back, forward, refresh) in the top-right corner.
    """

    def __init__(self, file: str, parent=None):
        super().__init__(parent)

        self.file = file

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 4, 6, 0)
        top_bar.addStretch(1)

        self._back_btn = QPushButton()
        self._back_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        )
        self._back_btn.setIconSize(QSize(16, 16))
        self._back_btn.setFixedSize(24, 24)
        self._back_btn.setToolTip("Back")
        self._back_btn.setStyleSheet(_BTN_STYLE)
        self._back_btn.setEnabled(False)
        self._back_btn.clicked.connect(self._on_back)
        top_bar.addWidget(self._back_btn)

        self._forward_btn = QPushButton()
        self._forward_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward)
        )
        self._forward_btn.setIconSize(QSize(16, 16))
        self._forward_btn.setFixedSize(24, 24)
        self._forward_btn.setToolTip("Forward")
        self._forward_btn.setStyleSheet(_BTN_STYLE)
        self._forward_btn.setEnabled(False)
        self._forward_btn.clicked.connect(self._on_forward)
        top_bar.addWidget(self._forward_btn)

        self._refresh_btn = QPushButton()
        self._refresh_btn.setIcon(QIcon(resource_path("assets/menus/browser.png")))
        self._refresh_btn.setIconSize(QSize(16, 16))
        self._refresh_btn.setFixedSize(24, 24)
        self._refresh_btn.setToolTip("Refresh Preview")
        self._refresh_btn.setStyleSheet(_BTN_STYLE)
        self._refresh_btn.clicked.connect(self._on_refresh)
        top_bar.addWidget(self._refresh_btn)

        root.addLayout(top_bar)

        # Fix: Attach parent immediately to prevent phantom window flashing
        self.browser = QWebEngineView(self)
        root.addWidget(self.browser)

        # Fix: Update navigation buttons when history changes
        self.browser.loadFinished.connect(self._update_nav_buttons)
        self.browser.urlChanged.connect(self._update_nav_buttons)

        self.load_file_in_preview(self.file)

    def _update_nav_buttons(self) -> None:
        """Enable or disable navigation buttons based on browser history."""
        self._back_btn.setEnabled(self.browser.history().canGoBack())
        self._forward_btn.setEnabled(self.browser.history().canGoForward())

    def _on_back(self) -> None:
        """Navigate to the previous page in history."""
        self.browser.back()

    def _on_forward(self) -> None:
        """Navigate to the next page in history."""
        self.browser.forward()

    def _on_refresh(self) -> None:
        """Reload the currently displayed page."""
        self.browser.reload()

    def load_file_in_preview(self, file_path: str) -> None:
        """Load *file_path* (local or remote) into the browser widget."""
        path = os.path.abspath(file_path)
        if os.path.exists(path):
            self.browser.setUrl(QUrl.fromLocalFile(path))
        else:
            self.browser.setUrl(QUrl(file_path))

    def load_html_code(
        self, html_content: str, base_url: str = "http://localhost/"
    ) -> None:
        """Render a raw HTML string inside the browser widget."""
        self.browser.setHtml(html_content, QUrl(base_url))
