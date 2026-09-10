"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

DocumentationFlyout: interactive, VS Code-like symbol documentation card.

This widget intentionally does not decide when an unpinned flyout should
close. HoverController owns that state transition.  The flyout only provides
presentation, scrolling, pinning and positioning.
"""

from __future__ import annotations

import re
from typing import Optional

from PyQt6.QtCore import QPoint, QTimer, Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QStyle,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)



def _plain_title_from_markdown(value: str) -> str:
    """Extract a compact plain-text title from Markdown heading/text."""
    if not value:
        return ""

    text = value.strip()
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, count=1)
    text = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(`{1,3})(.*?)\1", r"\2", text, flags=re.DOTALL)
    # Strip Markdown emphasis without destroying snake_case identifiers.
    # ``**bold**`` and ``*italic*`` use asterisks, ``~~strike~~`` uses tildes.
    # Underscore emphasis (``_italic_``, ``__bold__``) is intentionally not
    # stripped globally because it would corrupt names like ``my_func``.
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"~~(.*?)~~", r"\1", text)
    text = re.sub(r"[*~]", "", text)
    return " ".join(text.split())


class DocumentationFlyout(QFrame):
    """Scrollable documentation card with optional pinned mode."""

    navigate_back_requested = pyqtSignal()
    navigate_forward_requested = pyqtSignal()
    jump_to_source_requested = pyqtSignal()
    pin_toggled = pyqtSignal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        # Tool gives the card its own window surface so it can sit over the
        # editor, but it remains associated with the CodeEditor parent.
        super().__init__(
            parent,
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint,
        )

        self.setObjectName("documentationFlyout")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._width = 520
        self._min_height = 110
        self._max_height = 460
        self._is_pinned = False

        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.timeout.connect(self._update_size)

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = QFrame(self)
        self._header.setObjectName("documentationFlyoutHeader")
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(13, 10, 9, 9)
        header_layout.setSpacing(8)

        self._title_label = QLabel(self._header)
        self._title_label.setObjectName("documentationFlyoutTitle")
        self._title_label.setWordWrap(True)
        self._title_label.setTextFormat(Qt.TextFormat.RichText)
        self._title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        header_layout.addWidget(self._title_label, 1)

        self.btn_pin = QToolButton(self._header)
        self.btn_pin.setObjectName("documentationFlyoutPin")
        self.btn_pin.setCheckable(True)
        self.btn_pin.setAutoRaise(True)
        self.btn_pin.setFixedSize(24, 24)
        self.btn_pin.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton)
        )
        self.btn_pin.setIconSize(QSize(13, 13))
        self.btn_pin.setToolTip("Pin documentation")
        self.btn_pin.toggled.connect(self._on_pin_toggled)
        header_layout.addWidget(self.btn_pin, 0, Qt.AlignmentFlag.AlignTop)

        root.addWidget(self._header)

        self._separator = QFrame(self)
        self._separator.setObjectName("documentationFlyoutSeparator")
        self._separator.setFrameShape(QFrame.Shape.HLine)
        self._separator.setFixedHeight(1)
        root.addWidget(self._separator)

        self.browser = QTextBrowser(self)
        self.browser.setObjectName("documentationFlyoutBrowser")
        self.browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.browser.setReadOnly(True)
        self.browser.setOpenLinks(True)
        self.browser.setOpenExternalLinks(True)
        self.browser.setMouseTracking(True)
        self.browser.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        self.browser.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.browser.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.browser.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.browser.document().setDocumentMargin(14)
        root.addWidget(self.browser, 1)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setObjectName("documentationFlyoutShadow")
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 3)
        shadow.setColor(self.palette().color(QPalette.ColorRole.Shadow))
        self.setGraphicsEffect(shadow)

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------

    def set_documentation(self, title_markdown: str, body_markdown: str) -> None:
        """Render documentation as Markdown using Qt's native Markdown engine.

        The hover provider should return Markdown rather than pre-rendered HTML.
        QTextDocument performs the Markdown -> rich-text conversion, while the
        default stylesheet below controls the restrained IDE documentation style.
        """
        title = _plain_title_from_markdown(title_markdown)
        body = body_markdown or ""

        self._title_label.setText(title or "Documentation")

        document = self.browser.document()
        document.clear()
        document.setDefaultStyleSheet(self._markdown_stylesheet())
        document.setMarkdown(body)
        document.setDocumentMargin(14)

        self._schedule_update_size()

    @staticmethod
    def _markdown_stylesheet() -> str:
        """QTextDocument stylesheet – airy, small-font, human-readable.

        Tuned for 11 px body text with generous line-height and paragraph
        gaps so dense signatures / docstrings do not feel cramped.  The
        palette (foreground/background) is inherited from the widget palette
        so dark and light themes both remain legible.
        """
        return """
            body {
                font-size: 11px;
                line-height: 1.58;
            }
            p {
                margin-top: 0px;
                margin-bottom: 11px;
                line-height: 1.62;
            }
            h1 {
                font-size: 15px;
                font-weight: 600;
                margin-top: 4px;
                margin-bottom: 10px;
                line-height: 1.35;
            }
            h2 {
                font-size: 13px;
                font-weight: 600;
                margin-top: 14px;
                margin-bottom: 7px;
                line-height: 1.4;
            }
            h3 {
                font-size: 11.5px;
                font-weight: 600;
                margin-top: 13px;
                margin-bottom: 6px;
                line-height: 1.45;
            }
            h4, h5, h6 {
                font-size: 11px;
                font-weight: 600;
                margin-top: 10px;
                margin-bottom: 5px;
                line-height: 1.45;
            }
            ul, ol {
                margin-top: 6px;
                margin-bottom: 12px;
                padding-left: 22px;
                line-height: 1.6;
            }
            li {
                margin-bottom: 5px;
                line-height: 1.58;
            }
            blockquote {
                margin-left: 8px;
                margin-top: 8px;
                margin-bottom: 10px;
                padding-left: 12px;
                line-height: 1.6;
            }
            pre {
                margin-top: 9px;
                margin-bottom: 12px;
                padding: 10px 12px;
                line-height: 1.5;
                font-size: 10.5px;
            }
            code {
                font-family: monospace;
                font-size: 10.5px;
                line-height: 1.5;
            }
            table {
                margin-top: 9px;
                margin-bottom: 12px;
                line-height: 1.55;
            }
            th, td {
                padding: 5px 10px 5px 0;
            }
            hr {
                margin-top: 12px;
                margin-bottom: 12px;
            }
            a {
                text-decoration: none;
            }
        """

    def clear_documentation(self) -> None:
        self._title_label.clear()
        self.browser.clear()
        self._schedule_update_size()

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    def _schedule_update_size(self) -> None:
        if not self._layout_timer.isActive():
            self._layout_timer.start(0)

    def _update_size(self) -> None:
        width = max(360, int(self._width))
        self.setFixedWidth(width)

        try:
            margin = int(self.browser.document().documentMargin())
            self.browser.document().setTextWidth(
                max(100, width - (2 * margin))
            )
            doc_height = self.browser.document().documentLayout().documentSize().height()
            doc_height = int(doc_height)
        except Exception:
            doc_height = 180

        header_height = self._header.sizeHint().height()
        target = header_height + 1 + doc_height
        height = max(self._min_height, min(self._max_height, target))
        self.setFixedHeight(height)

    def show_at(self, global_pos: QPoint) -> None:
        self._update_size()

        screen = QApplication.screenAt(global_pos) or QApplication.primaryScreen()
        if screen is None:
            self.move(global_pos)
            self.show()
            self.raise_()
            return

        area = screen.availableGeometry()
        margin = 8
        width = self.width()
        height = self.height()

        max_x = area.right() - width - margin + 1
        x = max(area.left() + margin, min(global_pos.x(), max_x))

        if global_pos.y() + height <= area.bottom() - margin + 1:
            y = global_pos.y()
        else:
            above = global_pos.y() - height - margin
            if above >= area.top() + margin:
                y = above
            else:
                y = max(area.top() + margin, area.bottom() - height - margin + 1)

        self.move(x, y)
        self.show()
        self.raise_()

    def contains_global_pos(self, global_pos: QPoint) -> bool:
        if not self.isVisible():
            return False
        try:
            return bool(self.frameGeometry().contains(global_pos))
        except Exception:
            return bool(self.rect().contains(self.mapFromGlobal(global_pos)))

    # ------------------------------------------------------------------
    # Pinning / dismissal
    # ------------------------------------------------------------------

    @property
    def is_pinned(self) -> bool:
        return self._is_pinned

    def set_pinned(self, pinned: bool) -> None:
        pinned = bool(pinned)
        if self.btn_pin.isChecked() != pinned:
            self.btn_pin.setChecked(pinned)
        else:
            self._set_pinned_state(pinned)

    def _on_pin_toggled(self, checked: bool) -> None:
        self._set_pinned_state(bool(checked))

    def _set_pinned_state(self, checked: bool) -> None:
        self._is_pinned = bool(checked)
        self.btn_pin.setToolTip(
            "Unpin documentation" if self._is_pinned else "Pin documentation"
        )
        self.pin_toggled.emit(self._is_pinned)

    def dismiss(self, force: bool = False) -> None:
        # The controller requests force=True for its ordinary lifetime action.
        # This method intentionally contains no mouse-position logic.
        if self._is_pinned and not force:
            return
        self.hide()

    # ------------------------------------------------------------------
    # Qt events
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and not self._is_pinned:
            self.dismiss(force=True)
            event.accept()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Interaction – clicks inside the flyout must never destroy it.
    # This allows embedding richer widgets (buttons, tabs, etc.) later.
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        # Accept so the event does not propagate to the editor's
        # focus-out / click-to-dismiss logic.  HoverController's filter
        # also stops the close timer, but accepting here guarantees the
        # click is treated as handled inside the card.
        event.accept()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        event.accept()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        event.accept()
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event) -> None:
        # Let the internal QTextBrowser scroll, but never let the wheel
        # dismiss the card.
        event.accept()
        super().wheelEvent(event)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
