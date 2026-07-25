"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

HoverController: Non-blocking manager for the Documentation Flyout.
"""

from PyQt6.QtCore import QObject, QTimer, QPoint, Qt, QEvent
from PyQt6.QtWidgets import QWidget

from editor.Ironica.plugins.python.hover_presenter import HoverPresenter


class HoverController(QObject):
    """
    Controller that coordinates mouse hover events, provider resolution,
    and the DocumentationFlyout lifecycle without blocking the main UI.
    """

    def __init__(self, editor: QWidget, flyout: QWidget, provider=None) -> None:
        super().__init__(editor)
        self.editor = editor
        self.flyout = flyout
        self.provider = provider

        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(1000)
        self._hover_timer.timeout.connect(self._on_hover_timeout)

        self._last_mouse_pos = QPoint()
        self._target_line: int = -1
        self._target_col: int = -1

        self.editor.installEventFilter(self)
        if hasattr(self.editor, "viewport") and self.editor.viewport():
            self.editor.viewport().installEventFilter(self)

        if hasattr(self.editor, "verticalScrollBar"):
            self.editor.verticalScrollBar().valueChanged.connect(
                self._on_editor_activity
            )
        if hasattr(self.editor, "horizontalScrollBar"):
            self.editor.horizontalScrollBar().valueChanged.connect(
                self._on_editor_activity
            )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        etype = event.type()

        if etype == QEvent.Type.MouseMove:
            pos = event.pos()

            if (pos - self._last_mouse_pos).manhattanLength() > 3:
                self._last_mouse_pos = pos
                self._on_mouse_moved()

        elif etype in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.Wheel,
            QEvent.Type.KeyPress,
            QEvent.Type.FocusOut,
        ):
            self._on_editor_activity()

        return super().eventFilter(watched, event)

    def _on_mouse_moved(self) -> None:
        """Triggered whenever mouse moves in the editor."""
        self._hover_timer.stop()

        line, col = self._get_line_col_at_pos(self._last_mouse_pos)
        if line >= 0 and col >= 0:
            self._target_line = line
            self._target_col = col
            # Restart 1-second timer
            self._hover_timer.start()
        else:
            self._dismiss_flyout_if_needed()

    def _on_editor_activity(self) -> None:
        """Triggered on scroll, keypress, or click."""
        self._hover_timer.stop()
        self._dismiss_flyout_if_needed()

    def _dismiss_flyout_if_needed(self) -> None:
        """Dismisses flyout unless mouse is inside or window is pinned."""
        if self.flyout and self.flyout.isVisible():
            self.flyout.dismiss(force=False)

    def _get_line_col_at_pos(self, pos: QPoint):
        """Extract line and column from QScintilla mouse point."""
        position = self.editor.SendScintilla(
            self.editor.SCI_POSITIONFROMPOINT, pos.x(), pos.y()
        )
        if position < 0:
            return -1, -1
        line = self.editor.SendScintilla(self.editor.SCI_LINEFROMPOSITION, position)
        col = self.editor.SendScintilla(self.editor.SCI_GETCOLUMN, position)
        return line, col

    def _on_hover_timeout(self) -> None:
        """Fires exactly 1 second after mouse comes to rest on code."""
        if self._target_line < 0 or self._target_col < 0:
            return

        text = self.editor.text()
        if not text:
            return

        title_html, body_html = self._resolve_hover_content(
            text, self._target_line, self._target_col
        )

        if not title_html or not body_html:
            return

        self.flyout.set_documentation(title_html, body_html)

        line_pos = self.editor.SendScintilla(
            self.editor.SCI_POSITIONFROMLINE, self._target_line
        )
        x = self.editor.SendScintilla(
            self.editor.SCI_POINTXFROMPOSITION, 0, line_pos + self._target_col
        )
        y = self.editor.SendScintilla(
            self.editor.SCI_POINTYFROMPOSITION, 0, line_pos + self._target_col
        )
        line_height = self.editor.SendScintilla(
            self.editor.SCI_TEXTHEIGHT, self._target_line
        )

        global_pt = self.editor.mapToGlobal(QPoint(x, y + line_height + 2))

        self.flyout.move(global_pt)
        self.flyout.show()

    def _resolve_hover_content(self, text: str, line: int, col: int):
        """Build IntelliJ-styled title and body strings."""
        details = None
        if self.provider and hasattr(self.provider, "get_hover_details"):
            try:
                details = self.provider.get_hover_details(text, line, col)
            except Exception:
                details = None

        if not details:
            return None, None

        kind_str = f"<i>({details.kind})</i>" if details.kind else ""
        title_html = (
            f'<span style="font-weight:bold; font-size:13px;">{details.name}</span> '
            f'<span style="color:#888888; font-style:italic;">{kind_str}</span>'
        )

        body_html = HoverPresenter.to_html(details)
        return title_html, body_html
