"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Stateful and non-blocking documentation flayout widget.
"""

from editor import *

# Kind → badge colour mapping (shared with CompletionDelegate fallback).
_KIND_COLORS: dict = {
    "function": "#C586C0",
    "method": "#C586C0",
    "class": "#4EC9B0",
    "module": "#DCDCAA",
    "keyword": "#569CD6",
    "builtin": "#569CD6",
    "variable": "#9CDCFE",
    "instance": "#9CDCFE",
    "property": "#4FC1FF",
    "param": "#9CDCFE",
    "parameter": "#9CDCFE",
    "statement": "#858585",
    "import": "#DCDCAA",
}


def _kind_color(kind: str) -> str:
    """Return hex colour for *kind*."""
    if not kind:
        return "#858585"
    return _KIND_COLORS.get(kind.lower(), "#858585")


def _kind_label(kind: str) -> str:
    """Return human-readable uppercase label for *kind*."""
    if not kind:
        return "SYMBOL"
    return kind.upper()


class DocumentationFlyout(QFrame):
    """
    Floating, stateful documentation flyout modeled after IntelliJ IDEA.

    Features:
    - Matches the editor background colour via QPalette.
    - Rounded border with subtle contrast and drop shadow.
    - Kind-coloured badge that instantly tells the user what is hovered.
    - Compact header with title, kind label and action buttons.
    - Built-in scrollbar via QTextBrowser.
    - Tracks mouse hover internally to prevent auto-dismissal when scrolling/reading.
    - Responds to 'Esc' key to close cleanly.
    - Auto-hides on window deactivate / hide / tab change.
    """

    # Toolbar button interactions signals
    navigate_back_requested = pyqtSignal()
    navigate_forward_requested = pyqtSignal()
    jump_to_source_requested = pyqtSignal()
    pin_toggled = pyqtSignal(bool)

    _BTN_SIZE = QSize(24, 24)
    _ICON_SIZE = QSize(16, 16)
    _BORDER_RADIUS = 8

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(
            parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )

        self._is_mouse_inside: bool = False
        self._is_pinned: bool = False

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.resize(520, 280)
        self.setMinimumSize(360, 180)
        self.setMaximumSize(640, 480)

        self._init_ui()
        self._apply_theme()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _resolve_palette(self) -> QPalette:
        """Return the palette from the editor parent, or the app palette."""
        if self.parent() and hasattr(self.parent(), "palette"):
            try:
                return self.parent().palette()
            except Exception:
                pass
        return QApplication.palette()

    def _apply_theme(self) -> None:
        """Apply background, border, and scrollbar colours from the palette."""
        pal = self._resolve_palette()
        bg = pal.color(QPalette.ColorRole.Window)
        border = pal.color(QPalette.ColorRole.Mid)
        base = pal.color(QPalette.ColorRole.Base)
        mid = pal.color(QPalette.ColorRole.Mid)
        dark = pal.color(QPalette.ColorRole.Dark)
        text = pal.color(QPalette.ColorRole.WindowText)
        is_dark = bg.lightness() < 128

        r = self._BORDER_RADIUS
        # Card background slightly elevated from window.
        if is_dark:
            card_bg = bg.lighter(108)
            header_bg = bg.lighter(112)
            sep_color = mid.lighter(115).name()
        else:
            card_bg = bg.lighter(103) if bg.lightness() < 220 else QColor("#FFFFFF")
            header_bg = bg.darker(103).name() if isinstance(bg, QColor) else bg.name()
            # For light theme header_bg should be a colour string.
            header_bg = QColor(header_bg) if isinstance(header_bg, str) else header_bg
            sep_color = mid.name()

        # Convert header_bg to name if QColor
        if isinstance(header_bg, QColor):
            header_bg_name = header_bg.name()
        else:
            header_bg_name = str(header_bg)

        # QTextBrowser background should contrast slightly from card.
        browser_bg = base.name() if is_dark else "#FFFFFF"
        if not is_dark and base.lightness() > 200:
            browser_bg = "#FAFAFA"

        self._card_bg = card_bg if isinstance(card_bg, QColor) else QColor(card_bg)
        self._header_bg_name = header_bg_name
        self._browser_bg_name = browser_bg
        self._text_color = text

        self._container.setStyleSheet(
            f"QFrame#flyoutContainer {{"
            f"  background-color: {self._card_bg.name()};"
            f"  border: 1px solid {border.name()};"
            f"  border-radius: {r}px;"
            f"}}"
        )
        self._header_frame.setStyleSheet(
            f"QFrame#flyoutHeader {{"
            f"  background-color: {header_bg_name};"
            f"  border: none;"
            f"  border-top-left-radius: {r}px;"
            f"  border-top-right-radius: {r}px;"
            f"}}"
        )
        # Scrollbars styled to match theme.
        self.setStyleSheet(
            f"DocumentationFlyout {{"
            f"  background: transparent;"
            f"  border: none;"
            f"}}"
            f" QToolButton {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  padding: 2px;"
            f"  border-radius: 4px;"
            f"}}"
            f"QToolButton:hover {{"
            f"  background-color: {mid.name()};"
            f"}}"
            f"QToolButton:checked {{"
            f"  background-color: {dark.name()};"
            f"}}"
            f"QTextBrowser {{"
            f"  background-color: {browser_bg};"
            f"  border: none;"
            f"  padding: 2px;"
            f"}}"
            f"QScrollBar:vertical {{"
            f"  background: transparent;"
            f"  width: 7px; border: none; margin: 2px 1px;"
            f"}}"
            f"QScrollBar::handle:vertical {{"
            f"  background: {mid.name()};"
            f"  min-height: 18px; border-radius: 3px;"
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
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(0)

        self._container = QFrame(self)
        self._container.setObjectName("flyoutContainer")
        outer.addWidget(self._container)

        main_layout = QVBoxLayout(self._container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header row
        self._header_frame = QFrame(self._container)
        self._header_frame.setObjectName("flyoutHeader")
        header_layout = QHBoxLayout(self._header_frame)
        header_layout.setContentsMargins(10, 8, 6, 8)
        header_layout.setSpacing(8)

        # Kind badge: coloured dot + label
        self._badge_dot = QLabel(self._header_frame)
        self._badge_dot.setFixedSize(10, 10)
        self._badge_dot.setStyleSheet("background-color: #858585; border-radius: 5px;")
        header_layout.addWidget(self._badge_dot)

        self._kind_label = QLabel(self._header_frame)
        self._kind_label.setTextFormat(Qt.TextFormat.PlainText)
        self._kind_label.setStyleSheet("color: #888888; font-size: 11px; font-weight: 600;")
        header_layout.addWidget(self._kind_label)

        self.title_label = QLabel(self._header_frame)
        self.title_label.setTextFormat(Qt.TextFormat.RichText)
        self.title_label.setWordWrap(False)
        self.title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
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

        main_layout.addWidget(self._header_frame)

        # Separator
        self._separator = QFrame(self._container)
        self._separator.setFrameShape(QFrame.Shape.HLine)
        self._separator.setFrameShadow(QFrame.Shadow.Sunken)
        self._separator.setFixedHeight(1)
        self._separator.setStyleSheet("background-color: #3A3A3A; border: none;")
        main_layout.addWidget(self._separator)

        self.content_browser = QTextBrowser(self._container)
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.setFrameShape(QFrame.Shape.NoFrame)
        self.content_browser.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.content_browser.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.content_browser.setContentsMargins(4, 0, 4, 4)

        main_layout.addWidget(self.content_browser, stretch=1)

        # Hint footer (subtle)
        self._hint_label = QLabel("Press Esc to close • Click pin to keep open", self._container)
        self._hint_label.setStyleSheet("color: #888888; font-size: 10px; padding: 4px 8px;")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self._hint_label)

    def _make_button(self, pixmap: QStyle.StandardPixmap, tooltip: str) -> QToolButton:
        """Create a compact, icon-only QToolButton."""
        btn = QToolButton(self)
        btn.setIcon(self.style().standardIcon(pixmap))
        btn.setToolTip(tooltip)
        btn.setIconSize(self._ICON_SIZE)
        btn.setFixedSize(self._BTN_SIZE)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        btn.setAutoRaise(True)
        return btn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_documentation(self, title_html: str, body_html: str) -> None:
        """Update header and body content safely."""
        # Extract kind/name from title_html for badge if possible.
        kind_guess = ""
        try:
            # title_html looks like '<span ...>name</span> <span ...><i>(kind)</i></span>'
            # Extract inside parentheses.
            import re as _re
            m = _re.search(r"\(([^)]+)\)", title_html)
            if m:
                kind_guess = m.group(1).strip().strip("<>i/ ").lower()
        except Exception:
            pass

        badge_color = _kind_color(kind_guess)
        self._badge_dot.setStyleSheet(
            f"background-color: {badge_color}; border-radius: 5px; border: 1px solid rgba(255,255,255,30);"
        )
        self._kind_label.setText(_kind_label(kind_guess))
        self._kind_label.setStyleSheet(
            f"color: {badge_color}; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;"
        )

        self.title_label.setText(title_html)
        # Wrap body_html with container style for consistent fonts.
        # Ensure signature blocks use theme-aware background.
        wrapped = self._wrap_body_html(body_html)
        self.content_browser.setHtml(wrapped)
        # Scroll to top when new docs arrive.
        try:
            vbar = self.content_browser.verticalScrollBar()
            if vbar is not None:
                vbar.setValue(0)
        except Exception:
            pass

    def _wrap_body_html(self, body_html: str) -> str:
        """Wrap provider HTML with theme-aware container styling."""
        # Use browser background for signature block override if provider used
        # hard-coded #1E1E1E. Replace it with theme colour for consistency.
        themed = body_html
        try:
            themed = themed.replace("#1E1E1E", self._browser_bg_name)
            themed = themed.replace("#1e1e1e", self._browser_bg_name)
            # Ensure code blocks are readable in light theme.
            if hasattr(self, "_text_color") and self._text_color.lightness() >= 128:
                themed = themed.replace("color:#D4D4D4", "color:#1A1A1A")
                themed = themed.replace("color:#A9A9A9", "color:#555555")
        except Exception:
            pass
        return themed

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
        # If not pinned, schedule a short hide so moving back in quickly
        # does not flicker; otherwise keep visible for reading.
        if not self._is_pinned:
            QTimer.singleShot(120, lambda: self.dismiss(force=False))
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

    def hideEvent(self, event) -> None:
        self._is_mouse_inside = False
        super().hideEvent(event)

    def changeEvent(self, event) -> None:
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if getattr(self, "_in_change_event", False):
                super().changeEvent(event)
                return
            self._in_change_event = True
            try:
                self._apply_theme()
            finally:
                self._in_change_event = False
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Pin
    # ------------------------------------------------------------------

    def _on_pin_toggled(self, checked: bool) -> None:
        self._is_pinned = checked
        self._btn_pin.setToolTip("Unpin Window" if checked else "Pin Window")
        self.pin_toggled.emit(checked)
