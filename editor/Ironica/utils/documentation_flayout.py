"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.
DocumentationFlyout:
"""

from __future__ import annotations

import html
import re
from typing import Optional

from PyQt6.QtCore import QEvent, QPoint, QTimer, Qt, QSize, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QPalette,
    QTextCursor,
    QTextDocument,
    QTextCharFormat,
)
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QStyle,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QToolButton,
    QApplication,
    QTextBrowser,
    QGraphicsDropShadowEffect,
)

from editor.Ironica.retheme import DEFAULT_DOC_PALETTE, doc_palette


def _plain_title_from_markdown(value: str) -> str:
    """Extract a compact plain-text title from Markdown heading/text."""
    if not value:
        return ""

    text = value.strip()
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, count=1)
    text = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(`{1,3})(.*?)\1", r"\2", text, flags=re.DOTALL)

    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"~~(.*?)~~", r"\1", text)
    text = re.sub(r"[*~]", "", text)
    return " ".join(text.split())


_MONOSPACE_FAMILIES = frozenset(
    {
        "monospace",
        "courier",
        "courier new",
        "consolas",
        "menlo",
        "dejavu sans mono",
        "liberation mono",
        "source code pro",
        "jetbrains mono",
        "fira code",
        "cascadia code",
        "cascadia mono",
    }
)


def _split_name_kind(title: str) -> tuple:
    """Split a ``Name (Kind)`` header into its parts for badge rendering."""
    text = (title or "").strip()
    match = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", text)
    if match:
        name, kind = match.group(1).strip(), match.group(2).strip()
        if name and kind and len(kind) <= 24:
            return name, kind
    return text, ""


class DocumentationFlyout(QFrame):
    """Scrollable documentation card with optional pinned mode."""

    navigate_back_requested = pyqtSignal()
    navigate_forward_requested = pyqtSignal()
    jump_to_source_requested = pyqtSignal()
    pin_toggled = pyqtSignal(bool)
    dismissed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
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
        self._min_height = 40
        self._max_height = 460
        self._document_margin = 8
        self._is_pinned = False
        self._in_change_event = False
        self._last_body = ""

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
        header_layout.setContentsMargins(10, 8, 6, 6)
        header_layout.setSpacing(6)

        self._kind_icon = QLabel(self._header)
        self._kind_icon.setObjectName("documentationFlyoutKindIcon")
        self._kind_icon.setFixedSize(9, 9)
        header_layout.addWidget(self._kind_icon, 0, Qt.AlignmentFlag.AlignVCenter)

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
        self.btn_pin.setFixedSize(22, 22)
        self.btn_pin.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton)
        )
        self.btn_pin.setIconSize(QSize(12, 12))
        self.btn_pin.setToolTip("Pin documentation")
        self.btn_pin.toggled.connect(self._on_pin_toggled)
        header_layout.addWidget(self.btn_pin, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_dismiss = QToolButton(self._header)
        self.btn_dismiss.setObjectName("documentationFlyoutDismiss")
        self.btn_dismiss.setAutoRaise(True)
        self.btn_dismiss.setFixedSize(22, 22)
        self.btn_dismiss.setText("✕")
        self.btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dismiss.setToolTip("Close documentation (Esc)")
        self.btn_dismiss.clicked.connect(self._on_dismiss_clicked)
        header_layout.addWidget(self.btn_dismiss, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addWidget(self._header)

        self._divider = QFrame(self)
        self._divider.setObjectName("documentationFlyoutDivider")
        self._divider.setFixedHeight(1)
        root.addWidget(self._divider)

        self._separator = None

        self.browser = QTextBrowser(self)
        self.browser.setObjectName("documentationFlyoutBrowser")
        self.browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.browser.setReadOnly(True)
        self.browser.setOpenLinks(True)
        self.browser.setOpenExternalLinks(True)
        self.browser.setMouseTracking(True)
        self.browser.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        self.browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.browser.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.browser.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Ignored,
        )
        self.browser.setMinimumHeight(0)
        self.browser.document().setDocumentMargin(self._document_margin)
        root.addWidget(self.browser, 1)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setObjectName("documentationFlyoutShadow")
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 3)
        shadow.setColor(self.palette().color(QPalette.ColorRole.Shadow))
        self.setGraphicsEffect(shadow)
        self._apply_card_style()

    def _apply_card_style(self) -> None:
        """Give the card themed surfaces instead of Qt's stock light palette."""
        colors = self._doc_colors()
        surface = colors["surface"]
        surface_alt = colors.get("surface_alt", surface)
        border = colors["border"]
        text = colors["text"]
        outline = self._distinct_outline(surface, border)

        palette = QPalette(self.palette())
        palette.setColor(QPalette.ColorRole.Window, QColor(surface))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(text))
        palette.setColor(QPalette.ColorRole.Base, QColor(surface_alt))
        palette.setColor(QPalette.ColorRole.Text, QColor(text))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(text))
        palette.setColor(QPalette.ColorRole.Mid, QColor(outline))
        self.setPalette(palette)

        self._title_label.setStyleSheet(f"color: {text};")
        self.browser.setPalette(palette)
        self.browser.setStyleSheet(
            "QTextBrowser {"
            f" background-color: {surface_alt};"
            f" color: {text};"
            " border: none;"
            "}"
        )
        viewport = self.browser.viewport()
        viewport.setAutoFillBackground(True)
        viewport.setStyleSheet(f"background-color: {surface_alt};")
        self._divider.setStyleSheet(f"background-color: {outline}; border: none;")
        self.setStyleSheet(
            "QFrame#documentationFlyout {"
            f" background-color: {surface};"
            f" border: 1px solid {outline};"
            " border-radius: 0px;"
            "}"
            f"QToolButton {{ border: none; background: transparent; }}"
            f"QToolButton:hover {{ background: {colors['rule']}; border-radius: 3px; }}"
            f"QToolButton:checked {{ background: {colors['rule']}; border-radius: 3px; }}"
        )

    @staticmethod
    def _colour_distance(first: QColor, second: QColor) -> float:
        """Return the Euclidean RGB distance between two colours."""
        return (
            (first.red() - second.red()) ** 2
            + (first.green() - second.green()) ** 2
            + (first.blue() - second.blue()) ** 2
        ) ** 0.5

    def _distinct_outline(self, surface: str, border: str) -> str:
        """Return a theme-aware edge that visibly separates the card.

        Some themes define ``edge`` almost identical to the editor background,
        which makes a 1px border invisible. Nudge the theme edge away from the
        surface until it reaches a distinguishable contrast while keeping the
        theme's hue.
        """
        surface_color = QColor(surface)
        edge = QColor(border)
        if not surface_color.isValid():
            return border
        if not edge.isValid():
            edge = QColor(surface_color)

        dark_surface = surface_color.lightness() < 128
        candidate = edge
        for factor in (100, 130, 160, 190, 220):
            candidate = edge.lighter(factor) if dark_surface else edge.darker(factor)
            if self._colour_distance(candidate, surface_color) >= 90:
                break
        return candidate.name()

    def changeEvent(self, event) -> None:
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange):
            if not getattr(self, "_in_change_event", False):
                self._in_change_event = True
                try:
                    self._apply_card_style()
                except Exception:
                    pass
                finally:
                    self._in_change_event = False
        super().changeEvent(event)

    def _doc_colors(self) -> dict[str, str]:
        """Return the active theme's documentation accents.

        Falls back to the built-in dark accents so a theme missing the keys
        still renders a legible flyout rather than unset colours.
        """
        try:
            return doc_palette()
        except Exception:
            return dict(DEFAULT_DOC_PALETTE)

    def set_documentation(self, title_markdown: str, body_markdown: str) -> None:
        """Render documentation as Markdown using Qt's native Markdown engine."""
        title = _plain_title_from_markdown(title_markdown)
        body = body_markdown or ""

        name, kind = _split_name_kind(title or "Documentation")
        colors = self._doc_colors()
        self._kind_icon.setStyleSheet(
            f"background: {colors['kind']}; border-radius: 4px;"
        )
        parts = [
            f'<span style="color:{colors["name"]}; font-size:12.5px;'
            f' font-weight:600;">{html.escape(name)}</span>'
        ]
        if kind:
            parts.append(
                f'<span style="color:{colors["kind"]}; font-size:11.5px;">'
                f"&#183; {html.escape(kind)}</span>"
            )
        header = " ".join(parts)
        self._title_label.setText(header)
        self._last_body = body

        document = self.browser.document()
        document.clear()
        document.setDefaultStyleSheet(self._markdown_stylesheet())
        document.setMarkdown(body)
        document.setDocumentMargin(self._document_margin)
        self._style_code(document)

        self._schedule_update_size()

    def _style_code(self, document: QTextDocument) -> None:
        """Colour code blocks and inline code on the rendered document."""
        colors = self._doc_colors()
        limit = max(document.characterCount() - 1, 0)

        edits = []
        block = document.begin()
        while block.isValid():
            existing = self._char_format_at(document, block.position())
            if self._is_code_format(existing):
                edits.append(("block", block.position(), block.length(), existing))
            else:
                it = block.begin()
                while not it.atEnd():
                    fragment = it.fragment()
                    if not fragment.isValid():
                        it += 1
                        continue
                    fragment_format = fragment.charFormat()
                    if self._is_code_format(fragment_format):
                        edits.append(
                            (
                                "fragment",
                                fragment.position(),
                                fragment.length(),
                                fragment_format,
                            )
                        )
                    it += 1
            block = block.next()

        for _kind, position, length, existing in edits:
            end = min(position + max(length, 1), limit)
            if end <= position:
                continue
            cursor = QTextCursor(document)
            cursor.setPosition(position)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            char_format = QTextCharFormat(existing)
            char_format.setForeground(QColor(colors["code"]))
            cursor.setCharFormat(char_format)

    @staticmethod
    def _char_format_at(document: QTextDocument, position: int) -> QTextCharFormat:
        """Return the character format in effect at *position*."""
        cursor = QTextCursor(document)
        cursor.setPosition(min(max(position, 0), max(document.characterCount() - 1, 0)))
        return cursor.charFormat()

    @staticmethod
    def _doc_colors_for() -> dict:
        """Return the active theme's documentation palette.

        Returns:
            Mapping of surface and accent keys to hex colours.
        """
        try:
            return doc_palette()
        except Exception:
            return dict(DEFAULT_DOC_PALETTE)

    @staticmethod
    def _is_code_format(fmt: QTextCharFormat) -> bool:
        """Return whether *fmt* renders text as code."""
        if fmt.fontFixedPitch():
            return True
        return fmt.font().family().strip().lower() in _MONOSPACE_FAMILIES

    def _on_dismiss_clicked(self) -> None:
        """Close from the in-card dismiss button, even while pinned."""
        self.set_pinned(False)
        self.dismiss(force=True)
        self.dismissed.emit()

    def _markdown_stylesheet(self) -> str:
        c = self._doc_colors()
        surface_alt = c.get("surface_alt", c["surface"])
        return f"""
            body {{
                font-size: 12px;
                line-height: 1.45;
                color: {c["text"]};
                background: {surface_alt};
            }}
            p {{
                margin-top: 0px;
                margin-bottom: 8px;
                line-height: 1.45;
                color: {c["text"]};
            }}
            h1 {{
                font-size: 13px;
                font-weight: 600;
                color: {c["name"]};
                margin-top: 0px;
                margin-bottom: 6px;
                line-height: 1.3;
            }}
            h2 {{
                font-size: 12.5px;
                font-weight: 600;
                color: {c["name"]};
                margin-top: 10px;
                margin-bottom: 5px;
                line-height: 1.3;
            }}
            h3 {{
                font-size: 12px;
                font-weight: 600;
                color: {c["muted"]};
                margin-top: 9px;
                margin-bottom: 4px;
                line-height: 1.35;
            }}
            h4, h5, h6 {{
                font-size: 12px;
                font-weight: 600;
                color: {c["muted"]};
                margin-top: 8px;
                margin-bottom: 4px;
                line-height: 1.35;
            }}
            ul, ol {{
                margin-top: 4px;
                margin-bottom: 8px;
                padding-left: 20px;
                line-height: 1.45;
            }}
            li {{
                margin-bottom: 3px;
                line-height: 1.45;
            }}
            blockquote {{
                margin-left: 6px;
                margin-top: 6px;
                margin-bottom: 8px;
                padding-left: 10px;
                border-left: 2px solid {c["quote"]};
                color: {c["muted"]};
                line-height: 1.45;
            }}
            pre {{
                margin-top: 2px;
                margin-bottom: 8px;
                padding: 6px 8px;
                line-height: 1.4;
                font-size: 11.5px;
                color: {c["code"]};
                background-color: {c["surface_alt"]};
                border: 1px solid {c["rule"]};
                border-radius: 4px;
            }}
            code {{
                font-family: monospace;
                font-size: 11.5px;
                line-height: 1.4;
                color: {c["code"]};
            }}
            table {{
                margin-top: 6px;
                margin-bottom: 8px;
                line-height: 1.45;
            }}
            th, td {{
                padding: 3px 8px 3px 0;
            }}
            hr {{
                margin-top: 9px;
                margin-bottom: 9px;
                color: {c["rule"]};
            }}
            a {{
                color: {c["link"]};
                text-decoration: none;
            }}
        """

    def clear_documentation(self) -> None:
        self._title_label.clear()
        self.browser.clear()
        self._schedule_update_size()

    def _schedule_update_size(self) -> None:
        if not self._layout_timer.isActive():
            self._layout_timer.start(0)

    def _update_size(self) -> None:
        width = max(360, int(self._width))
        self.setFixedWidth(width)

        # The card stylesheet draws a 1px border on each side; the browser
        # fills the remaining contents area.
        border_extent = 2
        content_width = max(100, width - border_extent)

        try:
            measure = QTextDocument()
            measure.setDefaultStyleSheet(self._markdown_stylesheet())
            measure.setMarkdown(self._last_body or "")
            measure.setDocumentMargin(self._document_margin)
            # Match the browser's real viewport width so short text is not
            # measured against a narrower, artificially taller column.
            measure.setTextWidth(content_width)
            doc_height = int(measure.documentLayout().documentSize().height())
        except Exception:
            doc_height = 80

        header_height = self._header.sizeHint().height()
        divider_height = self._divider.height() or 1
        # 2px covers the outer border and guards against sub-pixel rounding.
        target = border_extent + header_height + divider_height + max(0, doc_height) + 2
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
        if self._is_pinned and not force:
            return
        self.hide()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and not self._is_pinned:
            self.dismiss(force=True)
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        event.accept()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        event.accept()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        event.accept()
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event) -> None:
        event.accept()
        super().wheelEvent(event)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
