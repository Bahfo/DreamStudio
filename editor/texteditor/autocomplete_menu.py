"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved

IntelliSense autocomplete infrastructure for DreamStudio.

This module provides:

- ``CompletionItem`` — data class for a single completion entry.
- ``CompletionModel`` — ``QAbstractListModel`` driving the popup list.
- ``CompletionDelegate`` — custom painter for icons, highlights, and kind labels.
- ``DocumentationFlyout`` — side-panel showing documentation for the selected item.
- ``IntelliSenseMenu`` — the frameless popup widget.
- ``EditorAutocompleteExtension`` — ``QObject`` event filter that owns the
  lifecycle of the popup and manages debounced triggering.

**Lifecycle ownership:**

``EditorAutocompleteExtension`` is created by ``CodeEditor.__init__`` and
installs itself as an event filter.  When the editor is destroyed the
extension's ``cleanup()`` method must be called to disconnect signals,
stop timers, and schedule the popup for deletion.  ``DreamTabbedEditor``
calls ``cleanup()`` in ``close_editor()`` before deleting the editor widget.
"""

import os
import re
import logging

from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QFrame,
    QApplication,
    QGraphicsDropShadowEffect,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QScrollArea,
    QSizePolicy,
    QWidgetAction,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPoint,
    QSize,
    QRect,
    pyqtSignal,
    QObject,
    QEvent,
    QAbstractListModel,
    QModelIndex,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPixmap,
    QPalette,
)
logger = logging.getLogger(__name__)

_ASSETS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "editor")
)

ICON_PATHS = {
    "keyword": os.path.join(_ASSETS_DIR, "keyword.png"),
    "function": os.path.join(_ASSETS_DIR, "function.png"),
    "method": os.path.join(_ASSETS_DIR, "function.png"),
    "class": os.path.join(_ASSETS_DIR, "class.png"),
    "variable": os.path.join(_ASSETS_DIR, "variable.png"),
    "constant": os.path.join(_ASSETS_DIR, "variable.png"),
    "module": os.path.join(_ASSETS_DIR, "module.png"),
    "parameter": os.path.join(_ASSETS_DIR, "parameter.png"),
    "property": os.path.join(_ASSETS_DIR, "property.png"),
    "snippet": os.path.join(_ASSETS_DIR, "text.png"),
    "text": os.path.join(_ASSETS_DIR, "text.png"),
    "value": os.path.join(_ASSETS_DIR, "variable.png"),
    "enum": os.path.join(_ASSETS_DIR, "enum.png"),
    "path": os.path.join(_ASSETS_DIR, "path.png"),
}

ICON_CACHE: dict = {}


def _theme_colors(widget=None) -> dict:
    """Read colours from a widget's palette (reflects the current
    stylesheet) or fall back to the application palette."""
    if widget is not None:
        pal = widget.palette()
    else:
        pal = QApplication.palette()
    bg = pal.color(QPalette.ColorRole.Window)
    text = pal.color(QPalette.ColorRole.WindowText)
    base = pal.color(QPalette.ColorRole.Base)
    highlight = pal.color(QPalette.ColorRole.Highlight)
    mid = pal.color(QPalette.ColorRole.Mid)
    placeholder = pal.color(QPalette.ColorRole.PlaceholderText)
    return {
        "bg": bg.name(),
        "bg_hover": mid.name(),
        "bg_selected": highlight.name(),
        "border": mid.name(),
        "text": text.name(),
        "text_dim": placeholder.name() if placeholder.isValid() else mid.name(),
        "text_match": highlight.name(),
        "flyout_bg": bg.name(),
        "flyout_border": mid.name(),
        "scrollbar_bg": base.name(),
        "scrollbar_handle": mid.name(),
        "scrollbar_handle_hover": pal.color(QPalette.ColorRole.Dark).name(),
        "separator": mid.name(),
        "icon_bg": mid.name(),
        "arrow_normal": placeholder.name() if placeholder.isValid() else mid.name(),
        "arrow_hover": highlight.name(),
    }

ITEM_HEIGHT = 24
MAX_VISIBLE_ITEMS = 10
FLYOUT_MIN_WIDTH = 280
FLYOUT_MAX_WIDTH = 420
DEBOUNCE_MS = 150
BUFFER_LINE_WINDOW = 100
MIN_MENU_WIDTH = 360
MAX_MENU_WIDTH = 600
WORD_REGEX = re.compile(r"\b[a-zA-Z_]\w*\b")


def load_icon(kind: str) -> Optional[QPixmap]:
    """Load and cache an icon pixmap for *kind*."""
    path = ICON_PATHS.get(kind)
    if not path:
        path = ICON_PATHS.get("text")
    if path in ICON_CACHE:
        return ICON_CACHE[path]
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None
    scaled = pixmap.scaled(
        16,
        16,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    ICON_CACHE[path] = scaled
    return scaled


@dataclass
class CompletionItem:
    """A single completion entry."""

    name: str
    kind: str
    documentation: str = ""
    score: int = 0


class CompletionModel(QAbstractListModel):
    """Model backing the completion popup's ``QListView``."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[CompletionItem] = []
        self._filter_text = ""

    def set_items(self, items: List[CompletionItem], filter_text: str = ""):
        self.beginResetModel()
        self._items = items
        self._filter_text = filter_text
        self.endResetModel()

    def item_at_row(self, row: int) -> Optional[CompletionItem]:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def all_items(self) -> List[CompletionItem]:
        return self._items

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._items):
            return None
        item = self._items[row]
        if role == Qt.ItemDataRole.DisplayRole:
            return item.name
        if role == Qt.ItemDataRole.UserRole:
            return item
        return None


def _highlight_html(name: str, query: str, widget=None) -> str:
    """Build an HTML snippet with the matching portion highlighted."""
    if not query:
        return name
    lower_name = name.lower()
    lower_query = query.lower()
    idx = lower_name.find(lower_query)
    if idx == -1:
        return name
    before = name[:idx]
    match_text = name[idx : idx + len(query)]
    after = name[idx + len(query) :]
    t = _theme_colors(widget)
    return (
        f"{before}"
        f"<span style='color:{t['text_match']};"
        f"font-weight:bold;'>{match_text}</span>"
        f"{after}"
    )


class CompletionDelegate(QStyledItemDelegate):
    """Custom painter for completion list items."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_text = ""
        self._selected_row = 0

    def _editor_font(self, size: int = 11) -> QFont:
        """Return the editor's actual resolved font at *size* points.

        Reads the QFont from the editor widget through the parent chain
        so that the autocomplete popup matches the editor exactly --
        no hardcoded font family names that may resolve differently.
        """
        try:
            menu = self.parent()
            editor = getattr(menu, "_editor_ref", None)
            if editor is not None:
                base = editor.font()
                f = QFont(base)
                f.setPointSize(size)
                return f
        except Exception:
            pass
        return QFont("monospace", size)

    def set_filter_text(self, text: str):
        self._filter_text = text

    def set_selected_row(self, row: int):
        self._selected_row = row

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = _theme_colors(self.parent())
        is_selected = index.row() == self._selected_row
        bg = t["bg_selected"] if is_selected else t["bg"]
        painter.fillRect(option.rect, QColor(bg))

        item = index.data(Qt.ItemDataRole.UserRole)
        if item is None:
            painter.restore()
            return

        rect = option.rect
        x = rect.left() + 6
        center_y = rect.top() + rect.height() // 2

        pixmap = load_icon(item.kind)
        if pixmap:
            painter.drawPixmap(x, center_y - 8, pixmap)
        else:
            painter.setBrush(QColor(t["icon_bg"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRect(x, center_y - 8, 16, 16), 2, 2)

        x += 24

        font = self._editor_font(11)
        painter.setFont(font)
        painter.setPen(QColor(t["text"]))

        html = _highlight_html(item.name, self._filter_text, self.parent())
        text_width = rect.width() - x - 60
        text_rect = QRect(x, rect.top(), max(text_width, 40), rect.height())
        self._draw_html(painter, text_rect, html)

        kind_font = self._editor_font(10)
        painter.setFont(kind_font)
        painter.setPen(QColor(t["text_dim"]))
        kind_text = item.kind.lower()
        kind_width = QFontMetrics(kind_font).horizontalAdvance(kind_text)
        kind_x = rect.right() - kind_width - 28
        painter.drawText(
            QRect(kind_x, rect.top(), kind_width, rect.height()),
            Qt.AlignmentFlag.AlignVCenter,
            kind_text,
        )

        arrow_font = self._editor_font(13)
        arrow_font.setBold(True)
        painter.setFont(arrow_font)
        arrow_color = t["arrow_hover"] if is_selected else t["arrow_normal"]
        painter.setPen(QColor(arrow_color))
        painter.drawText(
            QRect(rect.right() - 22, rect.top(), 20, rect.height()),
            Qt.AlignmentFlag.AlignCenter,
            "\u203a",
        )

        painter.restore()

    def _draw_html(self, painter: QPainter, rect: QRect, html: str):
        parts = []
        tag_re = re.compile(r"<span style='([^']*)'>([^<]*)</span>|([^<]+)")
        for m in tag_re.finditer(html):
            if m.group(2):
                parts.append((m.group(1), m.group(2)))
            elif m.group(3):
                parts.append((None, m.group(3)))

        fm = QFontMetrics(painter.font())
        x = rect.left()
        y = rect.top()

        for style_str, text in parts:
            if style_str:
                color_match = re.search(r"color:\s*([^;]+)", style_str)
                if color_match:
                    painter.setPen(QColor(color_match.group(1).strip()))
                if "font-weight" in style_str and "bold" in style_str:
                    f = painter.font()
                    f.setBold(True)
                    painter.setFont(f)
            else:
                painter.setPen(QColor(_theme_colors(self.parent())["text"]))
                f = painter.font()
                f.setBold(False)
                painter.setFont(f)

            for ch in text:
                cw = fm.horizontalAdvance(ch)
                if x + cw > rect.right():
                    break
                painter.drawText(
                    QRect(x, y, cw, rect.height()), Qt.AlignmentFlag.AlignVCenter, ch
                )
                x += cw

    def sizeHint(self, option, index):
        return QSize(0, ITEM_HEIGHT)


class DocumentationFlyout(QFrame):
    """Side panel showing documentation for the selected completion item."""

    def __init__(self, item: CompletionItem, parent=None, editor=None):
        super().__init__(parent)
        self.item = item
        self._editor = editor
        self.setMinimumWidth(FLYOUT_MIN_WIDTH)
        self.setMaximumWidth(FLYOUT_MAX_WIDTH)
        self.setObjectName("DocumentationFlyout")
        self._apply_theme(editor)

    def _apply_theme(self, widget=None):
        t = _theme_colors(widget)
        self.setStyleSheet(
            f"QFrame#DocumentationFlyout {{"
            f"background: {t['flyout_bg']};"
            f"border-left: 1px solid {t['flyout_border']};"
            f"border-top: none; border-bottom: none; border-right: none;"
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        header = QLabel(self.item.name)
        family = "monospace"
        if widget is not None:
            family = widget.font().family()
        header.setStyleSheet(
            f"color: {t['text']}; font-family: '{family}';"
            f" font-size: 13px; font-weight: bold; background: transparent;"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        if self.item.kind:
            kind_label = QLabel(f"({self.item.kind.lower()})")
            kind_label.setStyleSheet(
                f"color: {t['text_match']};"
                f" font-size: 11px; background: transparent;"
            )
            layout.addWidget(kind_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"background: {t['border']};" f" max-height: 1px; margin: 4px 0;"
        )
        layout.addWidget(sep)

        doc = self.item.documentation or "<i>No documentation available.</i>"
        doc_label = QLabel(doc)
        doc_label.setTextFormat(Qt.TextFormat.RichText)
        doc_label.setWordWrap(True)
        doc_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        doc_label.setStyleSheet(
            f"color: {t['text_dim']}; font-size: 12px;"
            f" background: transparent;"
        )
        layout.addWidget(doc_label)
        layout.addStretch()


class HoverDocumentationPopup(QWidget):
    """Custom scrollable hover popup for documentation display.

    Behaves like a QMenu: auto-dismisses on key press or focus loss,
    stays visible when the mouse hovers over it, supports scrolling
    for large content, and allows text selection/copy inside.
    """

    MAX_WIDTH = 420
    MAX_HEIGHT_RATIO = 0.6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedWidth(self.MAX_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self._content_label = QLabel()
        self._content_label.setTextFormat(Qt.TextFormat.RichText)
        self._content_label.setWordWrap(True)
        self._content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self._content_label.setOpenExternalLinks(True)
        self._content_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._content_label.setContentsMargins(10, 8, 10, 8)

        self._scroll_area.setWidget(self._content_label)
        layout.addWidget(self._scroll_area)

        # Dismiss timer — delayed hide lets the mouse transition from
        # the editor into the popup without flashing.
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.setInterval(350)
        self._dismiss_timer.timeout.connect(self.hide)

        self._apply_theme()

    def _apply_theme(self):
        t = _theme_colors()
        self.setStyleSheet(
            f"HoverDocumentationPopup {{"
            f"background: {t['bg']};"
            f"border: 1px solid {t['border']};"
            f"}}"
            f"QScrollArea {{"
            f"background: {t['bg']};"
            f"border: none;"
            f"}}"
            f"QScrollBar:vertical {{"
            f"background: {t['scrollbar_bg']};"
            f"width: 8px; border: none; margin: 0px;"
            f"}}"
            f"QScrollBar::handle:vertical {{"
            f"background: {t['scrollbar_handle']};"
            f"min-height: 16px; border-radius: 4px;"
            f"}}"
            f"QScrollBar::handle:vertical:hover {{"
            f"background: {t['scrollbar_handle_hover']};"
            f"}}"
            f"QScrollBar::add-line:vertical,"
            f"QScrollBar::sub-line:vertical {{"
            f"height: 0; background: none; border: none;"
            f"}}"
            f"QScrollBar::add-page:vertical,"
            f"QScrollBar::sub-page:vertical {{"
            f"background: none;"
            f"}}"
        )

    def show_html(self, html: str, pos: QPoint):
        """Show the popup with *html* content at *pos* (global coordinates)."""
        if not html:
            self.hide()
            return

        self._content_label.setText(html)

        # Constrain height to screen size.
        screen = QApplication.screenAt(pos)
        max_h = 500
        if screen:
            geo = screen.availableGeometry()
            max_h = int(geo.height() * self.MAX_HEIGHT_RATIO)

        self._scroll_area.setMinimumHeight(80)
        self._scroll_area.setMaximumHeight(max_h)
        self._content_label.setMinimumWidth(self.MAX_WIDTH - 24)

        # Let the label compute its natural height, then clamp.
        self._content_label.adjustSize()
        label_h = self._content_label.sizeHint().height()
        popup_h = min(max_h, label_h + 16)

        self.setFixedSize(self.MAX_WIDTH, popup_h)

        # Position — avoid going off-screen.
        px, py = pos.x(), pos.y()
        if screen:
            geo = screen.availableGeometry()
            if px + self.MAX_WIDTH > geo.right():
                px = geo.right() - self.MAX_WIDTH - 8
            if py + popup_h > geo.bottom():
                py = pos.y() - popup_h - 20
            px = max(geo.left() + 8, px)
            py = max(geo.top() + 8, py)

        self.move(px, py)
        self._dismiss_timer.stop()
        self.show()
        self.raise_()

    def enterEvent(self, event):
        """Mouse entered the popup — cancel pending dismissal."""
        self._dismiss_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse left the popup — start dismissal timer."""
        self._dismiss_timer.start()
        super().leaveEvent(event)

    def wheelEvent(self, event):
        """Allow scrolling inside the popup."""
        self._scroll_area.wheelEvent(event)


class IntelliSenseMenu(QWidget):
    """Frameless, always-on-top completion popup.

    The popup displays a filtered, ranked list of ``CompletionItem``
    objects and optionally a documentation flyout panel.
    """

    item_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._model = CompletionModel(self)
        self._delegate = CompletionDelegate(self)
        self._filtered: List[CompletionItem] = []
        self._filter_text = ""
        self._selected_index = 0
        self._flyout_visible = False
        self._flyout: Optional[DocumentationFlyout] = None
        self._editor_ref = None
        self._init_line = -1

        self._setup_ui()
        self._apply_shadow()

    def _setup_ui(self):
        t = _theme_colors(self._editor_ref)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(0)

        self._container = QFrame()
        self._container.setObjectName("IntelliSenseContainer")
        self._container.setStyleSheet(
            f"QFrame#IntelliSenseContainer {{"
            f"background: {t['bg']};"
            f"border: 1px solid {t['border']};"
            f"border-radius: 0px;"
            f"}}"
        )

        self._main_layout = QHBoxLayout(self._container)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._list_view = QListView()
        self._list_view.setModel(self._model)
        self._list_view.setItemDelegate(self._delegate)
        self._list_view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._list_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list_view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self._list_view.setMouseTracking(True)
        self._list_view.setUniformItemSizes(True)
        self._list_view.setStyleSheet(
            f"QListView {{"
            f"background: {t['bg']};"
            f"border: none; outline: none; padding: 0px;"
            f"}}"
            f"QListView::item {{"
            f"padding: 0; margin: 0; height: {ITEM_HEIGHT}px;"
            f"}}"
            f"QListView::item:selected {{"
            f"background: {t['bg_selected']};"
            f"}}"
            f"QScrollBar:vertical {{"
            f"background: {t['scrollbar_bg']};"
            f"width: 10px; border: none; margin: 0px;"
            f"}}"
            f"QScrollBar::handle:vertical {{"
            f"background: {t['scrollbar_handle']};"
            f"min-height: 16px; border-radius: 0px;"
            f"}}"
            f"QScrollBar::handle:vertical:hover {{"
            f"background: {t['scrollbar_handle_hover']};"
            f"}}"
            f"QScrollBar::add-line:vertical,"
            f" QScrollBar::sub-line:vertical {{"
            f"height: 0; background: none; border: none;"
            f"}}"
            f"QScrollBar::add-page:vertical,"
            f" QScrollBar::sub-page:vertical {{"
            f"background: none;"
            f"}}"
        )
        self._list_view.clicked.connect(self._on_item_clicked)
        self._main_layout.addWidget(self._list_view, 1)

        root.addWidget(self._container)

    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow)

    def set_editor(self, editor):
        self._editor_ref = editor

    def set_init_line(self, line: int):
        self._init_line = line

    def update_filter(self, text: str):
        self._filter_text = text
        self._apply_filter()

    def _apply_filter(self):
        self._filtered = []
        lower_filter = self._filter_text.lower()

        for item in self._model.all_items():
            if not lower_filter:
                score = 0
            else:
                lower_name = item.name.lower()
                if lower_name.startswith(lower_filter):
                    score = 3
                elif lower_filter in lower_name:
                    score = 2
                else:
                    parts = lower_name.split("_")
                    if any(lower_filter in p for p in parts):
                        score = 1
                    else:
                        continue
            item.score = score
            self._filtered.append(item)

        self._filtered.sort(key=lambda i: (-i.score, i.name))

        self._delegate.set_filter_text(self._filter_text)
        self._delegate.set_selected_row(0)
        self._model.set_items(self._filtered, self._filter_text)

        self._selected_index = 0
        if self._filtered:
            idx = self._model.index(0)
            self._list_view.setCurrentIndex(idx)
        else:
            self._hide_flyout()

        self._resize_to_content()
        self._position_near_editor()

    def _resize_to_content(self):
        count = min(len(self._filtered), MAX_VISIBLE_ITEMS)
        if count == 0:
            count = 1

        list_h = count * ITEM_HEIGHT
        container_h = list_h + 2
        self._list_view.setFixedHeight(list_h)
        self._container.setFixedHeight(container_h)

        fm = QFontMetrics(self._delegate._editor_font(11))
        max_w = 0
        for item in self._filtered:
            text_w = fm.horizontalAdvance(item.name)
            kind_w = fm.horizontalAdvance(item.kind.lower())
            row_w = 6 + 16 + 8 + text_w + 12 + kind_w + 28 + 24
            max_w = max(max_w, row_w)

        width = max(MIN_MENU_WIDTH, min(MAX_MENU_WIDTH, max_w + 20))
        if self._flyout_visible and self._flyout:
            flyout_w = max(FLYOUT_MIN_WIDTH, min(FLYOUT_MAX_WIDTH, 320))
            width += flyout_w
            self._flyout.setFixedHeight(container_h)

        total_width = width + 16
        total_height = container_h + 16
        self.setFixedSize(total_width, total_height)

    def _position_near_editor(self):
        if not self._editor_ref:
            self.move(100, 100)
            return

        editor = self._editor_ref
        try:
            from PyQt6.Qsci import QsciScintilla

            pos = int(editor.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS))
            x = int(editor.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, pos))
            y = int(editor.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, pos))

            line, _col = editor.getCursorPosition()
            text_height = int(editor.SendScintilla(QsciScintilla.SCI_TEXTHEIGHT, int(line)))

            display_widget = (
                editor.viewport()
                if hasattr(editor, "viewport") and editor.viewport()
                else editor
            )
            global_pt = display_widget.mapToGlobal(QPoint(x, y + text_height))
        except Exception as e:
            logger.debug("Scintilla positioning failed: %s", e)
            global_pt = editor.mapToGlobal(QPoint(0, editor.fontMetrics().height() * 3))

        screen = QApplication.screenAt(global_pt)
        if screen:
            geo = screen.availableGeometry()
            px = global_pt.x()
            py = global_pt.y()
            mw = self.width()
            mh = self.height()

            if px + mw > geo.right():
                px = geo.right() - mw - 8
            if py + mh > geo.bottom():
                line_h = text_height if "text_height" in dir() else 20
                py = global_pt.y() - mh - line_h - 8
            px = max(geo.left() + 8, px)
            py = max(geo.top() + 8, py)

            self.move(px, py)
        else:
            self.move(global_pt)

    def _on_row_changed(self, row: int):
        if row < 0 or row >= len(self._filtered):
            return
        self._selected_index = row
        self._delegate.set_selected_row(row)
        self._list_view.viewport().update()
        if self._flyout_visible:
            item = self._filtered[row]
            if item.documentation:
                self._show_flyout(item)
            else:
                self._hide_flyout()

    def _on_item_clicked(self, index: QModelIndex):
        row = index.row()
        if 0 <= row < len(self._filtered):
            self._selected_index = row
            self._delegate.set_selected_row(row)
            self._list_view.viewport().update()
            self._accept_selection()

    def _show_flyout(self, item: CompletionItem):
        if self._flyout and self._flyout.item == item:
            return
        if self._flyout:
            self._main_layout.removeWidget(self._flyout)
            self._flyout.deleteLater()
        self._flyout = DocumentationFlyout(item, self, editor=self._editor_ref)
        self._flyout.setFixedHeight(self._list_view.height() + 2)
        self._flyout.setFixedWidth(min(FLYOUT_MAX_WIDTH, 320))
        self._flyout_visible = True
        self._main_layout.addWidget(self._flyout)
        self._resize_to_content()

    def _hide_flyout(self):
        if self._flyout:
            self._flyout_visible = False
            self._main_layout.removeWidget(self._flyout)
            self._flyout.deleteLater()
            self._flyout = None
            self._resize_to_content()

    def toggle_flyout(self):
        if self._filtered and self._selected_index < len(self._filtered):
            item = self._filtered[self._selected_index]
            if self._flyout_visible:
                self._hide_flyout()
            else:
                self._show_flyout(item)

    def navigate_up(self):
        if self._selected_index > 0:
            self._selected_index -= 1
            idx = self._model.index(self._selected_index)
            self._list_view.setCurrentIndex(idx)
            self._delegate.set_selected_row(self._selected_index)
            self._list_view.viewport().update()
            if self._flyout_visible:
                item = self._filtered[self._selected_index]
                if item.documentation:
                    self._show_flyout(item)

    def navigate_down(self):
        if self._selected_index < len(self._filtered) - 1:
            self._selected_index += 1
            idx = self._model.index(self._selected_index)
            self._list_view.setCurrentIndex(idx)
            self._delegate.set_selected_row(self._selected_index)
            self._list_view.viewport().update()
            if self._flyout_visible:
                item = self._filtered[self._selected_index]
                if item.documentation:
                    self._show_flyout(item)

    def _accept_selection(self):
        if self._filtered and self._selected_index < len(self._filtered):
            name = self._filtered[self._selected_index].name
            self.item_selected.emit(name)
            self.hide()

    def show_items(
        self, items: List[CompletionItem], filter_text: str = "", init_line: int = -1
    ):
        if not items:
            self.hide()
            return
        self._init_line = init_line
        self._refresh_theme()
        self._model.set_items(items)
        self._filter_text = filter_text
        self._apply_filter()
        self.show()
        self.raise_()

    def _refresh_theme(self):
        """Re-read colours from the editor's palette and restyle."""
        t = _theme_colors(self._editor_ref)
        self._container.setStyleSheet(
            f"QFrame#IntelliSenseContainer {{"
            f"background: {t['bg']};"
            f"border: 1px solid {t['border']};"
            f"border-radius: 0px;"
            f"}}"
        )
        self._list_view.setStyleSheet(
            f"QListView {{"
            f"background: {t['bg']};"
            f"border: none; outline: none; padding: 0px;"
            f"}}"
            f"QListView::item {{"
            f"padding: 0; margin: 0; height: {ITEM_HEIGHT}px;"
            f"}}"
            f"QListView::item:selected {{"
            f"background: {t['bg_selected']};"
            f"}}"
            f"QScrollBar:vertical {{"
            f"background: {t['scrollbar_bg']};"
            f"width: 10px; border: none; margin: 0px;"
            f"}}"
            f"QScrollBar::handle:vertical {{"
            f"background: {t['scrollbar_handle']};"
            f"min-height: 16px; border-radius: 0px;"
            f"}}"
            f"QScrollBar::handle:vertical:hover {{"
            f"background: {t['scrollbar_handle_hover']};"
            f"}}"
            f"QScrollBar::add-line:vertical,"
            f" QScrollBar::sub-line:vertical {{"
            f"height: 0; background: none; border: none;"
            f"}}"
            f"QScrollBar::add-page:vertical,"
            f" QScrollBar::sub-page:vertical {{"
            f"background: none;"
            f"}}"
        )

    def hideEvent(self, event):
        self._hide_flyout()
        super().hideEvent(event)


class EditorAutocompleteExtension(QObject):
    """Event filter that manages autocomplete lifecycle for a ``CodeEditor``.

    Owns:

    - The ``IntelliSenseMenu`` popup (created lazily).
    - A debounce ``QTimer`` that coalesces rapid keystrokes.
    - Signal connections to ``cursorPositionChanged``.

    **Cleanup:** Call ``cleanup()`` before the editor widget is destroyed
    to disconnect all signals and stop timers.  Failing to do so may
    cause ``RuntimeError`` exceptions from deleted Qt objects.
    """

    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor
        self._menu: Optional[IntelliSenseMenu] = None
        self._debounce_timer = QTimer(editor)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._do_autocomplete)
        self._min_chars = 2
        self._init_line = -1
        self._cleaned_up = False
        self._position_signal_connected = False

    @property
    def menu(self) -> IntelliSenseMenu:
        if self._menu is None:
            self._menu = IntelliSenseMenu(self._editor)
            self._menu.item_selected.connect(self._insert_completion)
        return self._menu

    def install(self):
        """Install the event filter and connect editor signals."""
        self._editor.installEventFilter(self)
        if hasattr(self._editor, "cursorPositionChanged"):
            self._editor.cursorPositionChanged.connect(self._on_position_changed)
            self._position_signal_connected = True
        elif hasattr(self._editor, "position_changed"):
            self._editor.position_changed.connect(self._on_position_changed)
            self._position_signal_connected = True
        logger.debug("Autocomplete extension installed on editor")

    def cleanup(self):
        """Disconnect all signals and stop timers.

        Must be called before the editor widget is deleted.
        """
        if self._cleaned_up:
            return
        self._cleaned_up = True

        self._debounce_timer.stop()
        self._debounce_timer.timeout.disconnect()

        if self._position_signal_connected:
            try:
                if hasattr(self._editor, "cursorPositionChanged"):
                    self._editor.cursorPositionChanged.disconnect(
                        self._on_position_changed
                    )
                elif hasattr(self._editor, "position_changed"):
                    self._editor.position_changed.disconnect(
                        self._on_position_changed
                    )
            except (TypeError, RuntimeError):
                pass

        try:
            self._editor.removeEventFilter(self)
        except (TypeError, RuntimeError):
            pass

        if self._menu is not None:
            self._menu.hide()
            self._menu.deleteLater()
            self._menu = None

        logger.debug("Autocomplete extension cleaned up")

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            return self._handle_key_press(event)
        if event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.Hide,
            QEvent.Type.WindowStateChange,
            QEvent.Type.FocusOut,
        ):
            if self._menu and self._menu.isVisible():
                self._menu.hide()
            if hasattr(self._editor, "_dismiss_all_popups"):
                self._editor._dismiss_all_popups()
            return False
        return False

    def _handle_key_press(self, event) -> bool:
        if not self._menu or not self._menu.isVisible():
            return False

        key = event.key()
        text = event.text()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._menu._accept_selection()
            return True

        if key == Qt.Key.Key_Space or text.isspace():
            self.cancel_autocomplete()
            return False

        if key == Qt.Key.Key_Escape:
            self.cancel_autocomplete()
            return True

        if key == Qt.Key.Key_Up:
            self._menu.navigate_up()
            return True

        if key == Qt.Key.Key_Down:
            self._menu.navigate_down()
            return True

        if key == Qt.Key.Key_Tab:
            self._menu._accept_selection()
            return True

        if key == Qt.Key.Key_Right:
            if not self._menu._flyout_visible:
                self._menu.toggle_flyout()
                return True
            return False

        if key == Qt.Key.Key_Left:
            if self._menu._flyout_visible:
                self._menu.toggle_flyout()
                return True
            return False

        return False

    def _on_position_changed(self, line: int, col: int):
        if not self._menu or not self._menu.isVisible():
            return
        if self._menu._init_line >= 0 and line != self._menu._init_line:
            self.cancel_autocomplete()
        else:
            self._menu._position_near_editor()

    def schedule_autocomplete(self):
        """Start (or restart) the debounce timer."""
        if self._cleaned_up:
            return
        self._debounce_timer.start()

    def trigger_autocomplete(self):
        """Immediately trigger an autocomplete cycle."""
        if self._cleaned_up:
            return
        self.menu.show()
        self._do_autocomplete()

    def cancel_autocomplete(self):
        """Dismiss the popup and stop the debounce timer."""
        if self._cleaned_up:
            return
        self._debounce_timer.stop()
        if self._menu and self._menu.isVisible():
            self._menu.hide()
        self._init_line = -1

    def _do_autocomplete(self):
        if self._cleaned_up:
            return

        line, col = self._editor.getCursorPosition()
        full_text = self._editor.text()
        word_prefix = self._get_word_prefix(full_text, line, col)

        if len(word_prefix) < self._min_chars:
            self.cancel_autocomplete()
            return

        provider_items = []
        if getattr(self._editor, "current_provider", None):
            provider_items = self._query_provider(full_text, line, col, word_prefix)
        buffer_items = self._scan_buffer(full_text, line, word_prefix)

        seen = set()
        merged: List[CompletionItem] = []
        for item in provider_items:
            if item.name not in seen:
                seen.add(item.name)
                merged.append(item)
        for item in buffer_items:
            if item.name not in seen:
                seen.add(item.name)
                merged.append(item)

        if not merged:
            self.cancel_autocomplete()
            return

        self._init_line = line
        self.menu.set_editor(self._editor)
        self.menu.show_items(merged, word_prefix, init_line=line)

    def _get_word_prefix(self, text: str, line: int, col: int) -> str:
        lines = text.split("\n")
        if line >= len(lines):
            return ""
        before_cursor = lines[line][:col]
        match = re.search(r"(\w+)$", before_cursor)
        return match.group(1) if match else ""

    def _query_provider(
        self, text: str, line: int, col: int, prefix: str
    ) -> List[CompletionItem]:
        try:
            raw = self._editor.current_provider.get_auto_completions(text, line, col)
            items = []
            lower_prefix = prefix.lower()

            hover_html = None
            provider = self._editor.current_provider
            try:
                if hasattr(provider, "get_hover_html"):
                    hover_html = provider.get_hover_html(text, line, col)
                elif hasattr(provider, "get_hover_hint"):
                    hover_html = provider.get_hover_hint(text, line, col)
            except Exception:
                pass

            for name in raw:
                if not isinstance(name, str):
                    continue
                if lower_prefix and lower_prefix not in name.lower():
                    continue
                kind = self._infer_kind(name)
                doc = hover_html if hover_html else ""
                items.append(CompletionItem(name=name, kind=kind, documentation=doc))
            return items
        except Exception as e:
            logger.debug("Provider query failed: %s", e)
            return []

    @staticmethod
    def _normalize_doc_for_wrap(text: str) -> str:
        """Insert natural spaces around punctuation so word-wrap works.

        Qt's ``setWordWrap(True)`` needs whitespace break-points to
        function.  Long signature strings without spaces (e.g.
        ``func(a,b,c)``) cause the label to overflow.
        """
        text = text.replace(",", ", ")
        text = text.replace("(", "( ")
        text = text.replace(")", " )")
        text = text.replace("->", " -> ")
        return text

    def _infer_kind(self, name: str) -> str:
        if name[0:1].isupper() and not name.isupper():
            return "class"
        if "(" in name or name.endswith("()"):
            return "function"
        if name.isupper():
            return "constant"
        return "variable"

    def _scan_buffer(self, text: str, line: int, prefix: str) -> List[CompletionItem]:
        lines = text.split("\n")
        start = max(0, line - BUFFER_LINE_WINDOW)
        end = min(len(lines), line + BUFFER_LINE_WINDOW)
        window = "\n".join(lines[start:end])

        matches = WORD_REGEX.findall(window)
        lower_prefix = prefix.lower()
        seen = set()
        items = []
        for word in matches:
            if word in seen:
                continue
            if len(word) < 2:
                continue
            if not word.lower().startswith(lower_prefix):
                continue
            seen.add(word)
            items.append(CompletionItem(name=word, kind="text"))
        return items

    def _insert_completion(self, name: str):
        editor = self._editor
        line, index = editor.getCursorPosition()
        current_line_text = editor.text(line)[:index]

        match = re.search(r"(\w+)$", current_line_text)
        word_len = len(match.group(1)) if match else 0

        editor.beginUndoAction()
        if word_len > 0:
            editor.setSelection(line, index - word_len, line, index)
            editor.removeSelectedText()
        editor.insert(name)
        editor.endUndoAction()
        editor.setCursorPosition(line, index - word_len + len(name))
