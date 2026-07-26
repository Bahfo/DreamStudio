"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Stateful and non-blocking documentation flayout widget.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QSize
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import (
    QTextBrowser,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QStyle,
    QLabel,
    QFrame,
    QToolButton,
    QApplication,
)


class DocumentationFlyout(QFrame):
    """
    Floating, stateful documentation flyout modeled after IntelliJ IDEA.

    Features:
    - Matches the editor background colour via QPalette.
    - Rounded border with subtle contrast.
    - Compact right-aligned action buttons.
    - Built-in scrollbar via QTextBrowser.
    - Tracks mouse hover internally to prevent auto-dismissal when scrolling/reading.
    - Responds to 'Esc' key to close cleanly.
    """

    # Toolbar button interactions signals
    navigate_back_requested = pyqtSignal()
    navigate_forward_requested = pyqtSignal()
    jump_to_source_requested = pyqtSignal()
    pin_toggled = pyqtSignal(bool)

    _BTN_SIZE = QSize(24, 24)
    _ICON_SIZE = QSize(16, 16)
    _BORDER_RADIUS = 10

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(
            parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )

        self._is_mouse_inside: bool = False
        self._is_pinned: bool = False

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.resize(480, 260)
        self.setMinimumSize(320, 160)

        self._init_ui()
        self._apply_theme()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _resolve_palette(self) -> QPalette:
        """Return the palette from the editor parent, or the app palette."""
        if self.parent() and hasattr(self.parent(), "palette"):
            return self.parent().palette()
        return QApplication.palette()

    def _apply_theme(self) -> None:
        """Apply background, border, and scrollbar colours from the palette."""
        pal = self._resolve_palette()
        bg = pal.color(QPalette.ColorRole.Window)
        border = pal.color(QPalette.ColorRole.Mid)
        base = pal.color(QPalette.ColorRole.Base)
        mid = pal.color(QPalette.ColorRole.Mid)
        dark = pal.color(QPalette.ColorRole.Dark)

        r = self._BORDER_RADIUS
        self.setStyleSheet(
            f"DocumentationFlyout {{"
            f"  background-color: {bg.name()};"
            f"  border: 1px solid {border.name()};"
            f"  border-radius: {r}px;"
            f"}}"
            f"QToolButton {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  padding: 2px;"
            f"}}"
            f"QToolButton:hover {{"
            f"  background-color: {mid.name()};"
            f"  border-radius: 3px;"
            f"}}"
            f"QTextBrowser {{"
            f"  background-color: {bg.name()};"
            f"  border: none;"
            f"}}"
            f"QScrollBar:vertical {{"
            f"  background: {base.name()};"
            f"  width: 6px; border: none; margin: 0px;"
            f"}}"
            f"QScrollBar::handle:vertical {{"
            f"  background: {mid.name()};"
            f"  min-height: 12px; border-radius: 3px;"
            f"}}"
            f"QScrollBar::handle:vertical:hover {{"
            f"  background: {dark.name()};"
            f"}}"
            f"QScrollBar::add-line:vertical,"
            f"QScrollBar::sub-line:vertical {{"
            f"  height: 0; background: none; border: none;"
            f"}}"
            f"QScrollBar::add-page:vertical,"
            f"QScrollBar::sub-page:vertical {{"
            f"  background: none;"
            f"}}"
        )

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(4)

        # Header row: title on the left, compact buttons on the right.
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        self.title_label = QLabel(self)
        self.title_label.setTextFormat(Qt.TextFormat.RichText)
        self.title_label.setWordWrap(False)
        header_layout.addWidget(self.title_label, stretch=1)

        self._btn_back = self._make_button(
            QStyle.StandardPixmap.SP_ArrowBack,
            "Back",
        )
        self._btn_back.clicked.connect(self.navigate_back_requested.emit)
        self._btn_back.setEnabled(False)
        header_layout.addWidget(self._btn_back)

        self._btn_forward = self._make_button(
            QStyle.StandardPixmap.SP_ArrowForward,
            "Forward",
        )
        self._btn_forward.clicked.connect(self.navigate_forward_requested.emit)
        self._btn_forward.setEnabled(False)
        header_layout.addWidget(self._btn_forward)

        self._btn_jump = self._make_button(
            QStyle.StandardPixmap.SP_FileDialogContentsView,
            "Go to Declaration",
        )
        self._btn_jump.clicked.connect(self.jump_to_source_requested.emit)
        header_layout.addWidget(self._btn_jump)

        self._btn_pin = self._make_button(
            QStyle.StandardPixmap.SP_TitleBarNormalButton,
            "Pin Window",
        )
        self._btn_pin.setCheckable(True)
        self._btn_pin.toggled.connect(self._on_pin_toggled)
        header_layout.addWidget(self._btn_pin)

        main_layout.addLayout(header_layout)

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

    def _make_button(self, pixmap: QStyle.StandardPixmap, tooltip: str) -> QToolButton:
        """Create a compact, icon-only QToolButton."""
        btn = QToolButton(self)
        btn.setIcon(self.style().standardIcon(pixmap))
        btn.setToolTip(tooltip)
        btn.setIconSize(self._ICON_SIZE)
        btn.setFixedSize(self._BTN_SIZE)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        return btn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_documentation(self, title_html: str, body_html: str) -> None:
        """Update header and body content safely."""
        self.title_label.setText(title_html)
        self.content_browser.setHtml(body_html)

    def is_mouse_inside(self) -> bool:
        return self._is_mouse_inside

    def is_pinned(self) -> bool:
        return self._is_pinned

    def dismiss(self, force: bool = False) -> None:
        """Dismiss flyout unless pinned or mouse is inside it."""
        if force or (not self._is_pinned and not self._is_mouse_inside):
            self.hide()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

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

    def showEvent(self, event) -> None:
        """Re-apply theme on every show so palette changes are picked up."""
        self._apply_theme()
        super().showEvent(event)

    # ------------------------------------------------------------------
    # Pin
    # ------------------------------------------------------------------

    def _on_pin_toggled(self, checked: bool) -> None:
        self._is_pinned = checked
        self.pin_toggled.emit(checked)
