"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Stateful and non-blocking documentation flayout widget.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtWidgets import (
    QTextBrowser,
    QVBoxLayout,
    QHBoxLayout,
    QToolBar,
    QWidget,
    QStyle,
    QLabel,
    QFrame,
)


class DocumentationFlyout(QFrame):
    """
    Floating, stateful documentation flyout modeled after IntelliJ IDEA.

    Features:
    - Pure native QPalette styling (no setStyleSheet overhead or paint crashes).
    - Built-in scrollbar via QTextBrowser.
    - Tracks mouse hover internally to prevent auto-dismissal when scrolling/reading.
    - Responds to 'Esc' key to close cleanly.
    """

    # Toolbar button interactions signals
    navigate_back_requested = pyqtSignal()
    navigate_forward_requested = pyqtSignal()
    jump_to_source_requested = pyqtSignal()
    pin_toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(
            parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )

        self._is_mouse_inside: bool = False
        self._is_pinned: bool = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.resize(480, 260)
        self.setMinimumSize(320, 160)

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 2, 2, 2)

        self.title_label = QLabel(self)
        self.title_label.setTextFormat(Qt.TextFormat.RichText)
        self.title_label.setWordWrap(False)
        header_layout.addWidget(self.title_label, stretch=1)

        main_layout.addLayout(header_layout)

        self.toolbar = QToolBar(self)
        self.toolbar.setIconSize(self.toolbar.iconSize())

        self.action_back = self.toolbar.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack), "Back"
        )
        self.action_back.triggered.connect(self.navigate_back_requested.emit)
        self.action_back.setEnabled(False)

        self.action_forward = self.toolbar.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward), "Forward"
        )
        self.action_forward.triggered.connect(self.navigate_forward_requested.emit)
        self.action_forward.setEnabled(False)

        self.action_jump = self.toolbar.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            "Go to Declaration",
        )
        self.action_jump.triggered.connect(self.jump_to_source_requested.emit)

        self.action_pin = self.toolbar.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton),
            "Pin Window",
        )
        self.action_pin.setCheckable(True)
        self.action_pin.toggled.connect(self._on_pin_toggled)

        main_layout.addWidget(self.toolbar)

        self.content_browser = QTextBrowser(self)
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.setFrameShape(QFrame.Shape.NoFrame)
        self.content_browser.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.content_browser.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        main_layout.addWidget(self.content_browser, stretch=1)

    def set_documentation(self, title_html: str, body_html: str) -> None:
        """Update header and body content safely."""
        self.title_label.setText(title_html)
        self.content_browser.setHtml(body_html)

    def enterEvent(self, event: QEvent) -> None:
        self._is_mouse_inside = True
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._is_mouse_inside = False
        super().leaveEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss(force=True)
            return
        super().keyPressEvent(event)

    def is_mouse_inside(self) -> bool:
        return self._is_mouse_inside

    def is_pinned(self) -> bool:
        return self._is_pinned

    def _on_pin_toggled(self, checked: bool) -> None:
        self._is_pinned = checked
        self.pin_toggled.emit(checked)

    def dismiss(self, force: bool = False) -> None:
        """Dismiss flyout unless pinned or mouse is inside it."""
        if force or (not self._is_pinned and not self._is_mouse_inside):
            self.hide()
