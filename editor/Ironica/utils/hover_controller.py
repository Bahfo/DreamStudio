"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

HoverController: Non-blocking manager for the Documentation Flyout.
"""

from editor import *

# IDE-standard hover delay.  500 ms matches IntelliJ IDEA / VS Code
# defaults: fast enough to feel responsive, slow enough to avoid
# accidental popups while moving the caret.
_HOVER_DELAY_MS = 500
# Movement threshold to avoid jitter re-triggering the timer.
_HOVER_MOVE_THRESHOLD = 3


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
        self._hover_timer.setInterval(_HOVER_DELAY_MS)
        self._hover_timer.timeout.connect(self._on_hover_timeout)

        self._last_mouse_pos = QPoint()
        self._target_line: int = -1
        self._target_col: int = -1
        self._last_viewport_pos = QPoint()

        self.editor.installEventFilter(self)
        if hasattr(self.editor, "viewport") and self.editor.viewport():
            self.editor.viewport().installEventFilter(self)

        # Application-level events (window deactivate, etc.) are
        # installed separately so the flyout hides even when the
        # editor itself does not receive the event.
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self._orig_window = None
        if hasattr(self.editor, "window") and self.editor.window():
            try:
                win = self.editor.window()
                self._orig_window = win
                win.installEventFilter(self)
            except Exception:
                pass

        # Auto-cleanup when the editor is destroyed (tab closed).
        try:
            self.editor.destroyed.connect(self.shutdown)
        except Exception:
            pass

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
            viewport_pos = self._to_viewport_pos(watched, pos)
            if (viewport_pos - self._last_viewport_pos).manhattanLength() > _HOVER_MOVE_THRESHOLD:
                self._last_viewport_pos = viewport_pos
                self._last_mouse_pos = viewport_pos
                self._on_mouse_moved()

        elif etype in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.Wheel,
            QEvent.Type.KeyPress,
            QEvent.Type.KeyRelease,
            QEvent.Type.FocusOut,
        ):
            self._on_editor_activity()

        elif etype in (
            QEvent.Type.Leave,
            QEvent.Type.Hide,
            QEvent.Type.Close,
            QEvent.Type.WindowDeactivate,
            QEvent.Type.ApplicationDeactivate,
            QEvent.Type.WindowStateChange,
        ):
            self._on_hard_activity()

        return super().eventFilter(watched, event)

    def _to_viewport_pos(self, watched: QObject, pos: QPoint) -> QPoint:
        """Convert *pos* (in *watched* coords) to viewport coords."""
        try:
            viewport = self.editor.viewport() if hasattr(self.editor, "viewport") else None
            if viewport is not None and watched is not viewport:
                global_pt = watched.mapToGlobal(pos) if hasattr(watched, "mapToGlobal") else pos
                return viewport.mapFromGlobal(global_pt)
        except Exception:
            pass
        return pos

    def _on_mouse_moved(self) -> None:
        """Triggered whenever mouse moves in the editor."""
        self._hover_timer.stop()

        line, col = self._get_line_col_at_pos(self._last_mouse_pos)
        if line >= 0 and col >= 0:
            self._target_line = line
            self._target_col = col
            self._hover_timer.start()
        else:
            self._dismiss_flyout_if_needed()

    def _on_editor_activity(self) -> None:
        """Triggered on scroll, keypress, or click (soft dismiss)."""
        self._hover_timer.stop()
        self._dismiss_flyout_if_needed()

    def _on_hard_activity(self) -> None:
        """Triggered on hide/tab-change/minimize (hard dismiss, ignores pin)."""
        self._hover_timer.stop()
        if self.flyout and self.flyout.isVisible():
            self.flyout.dismiss(force=True)

    def _dismiss_flyout_if_needed(self) -> None:
        """Dismiss flyout unless mouse is inside or window is pinned."""
        if self.flyout and self.flyout.isVisible():
            self.flyout.dismiss(force=False)

    def _get_line_col_at_pos(self, pos: QPoint):
        """Extract line and column from QScintilla mouse point."""
        try:
            # Use CLOSE variant when available to avoid snapping to
            # distant text; fall back to POSITIONFROMPOINT.
            sci_close = getattr(self.editor, "SCI_POSITIONFROMPOINTCLOSE", None)
            if sci_close is not None:
                position = self.editor.SendScintilla(sci_close, pos.x(), pos.y())
            else:
                position = self.editor.SendScintilla(
                    self.editor.SCI_POSITIONFROMPOINT, pos.x(), pos.y()
                )
        except Exception:
            return -1, -1
        if position < 0:
            return -1, -1
        try:
            line, col = self.editor.lineIndexFromPosition(position)
            return line, col
        except Exception:
            # Fallback to raw Scintilla queries.
            try:
                line = self.editor.SendScintilla(self.editor.SCI_LINEFROMPOSITION, position)
                col = self.editor.SendScintilla(self.editor.SCI_GETCOLUMN, position)
                return line, col
            except Exception:
                return -1, -1

    def _on_hover_timeout(self) -> None:
        """Fires after the hover delay when mouse comes to rest on code."""
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

        try:
            pos = self.editor.positionFromLineIndex(self._target_line, self._target_col)
        except Exception:
            # Fallback: compute from line start + column offset.
            line_pos = self.editor.SendScintilla(
                self.editor.SCI_POSITIONFROMLINE, self._target_line
            )
            pos = line_pos + max(0, self._target_col)

        x = self.editor.SendScintilla(
            self.editor.SCI_POINTXFROMPOSITION, 0, pos
        )
        y = self.editor.SendScintilla(
            self.editor.SCI_POINTYFROMPOSITION, 0, pos
        )
        line_height = self.editor.SendScintilla(
            self.editor.SCI_TEXTHEIGHT, self._target_line
        )

        # Position just below the token's line.
        global_pt = self.editor.viewport().mapToGlobal(QPoint(x, y + line_height + 4))
        # Also try mapping via editor for margin correctness.
        if global_pt.isNull() or x < 0:
            global_pt = self.editor.mapToGlobal(QPoint(x, y + line_height + 4))

        # Clamp to screen geometry so the flyout never overflows.
        try:
            screen = QApplication.screenAt(global_pt)
            if screen is None:
                screen = QApplication.primaryScreen()
            if screen is not None:
                avail = screen.availableGeometry()
                fw = self.flyout.width() if hasattr(self.flyout, "width") else 480
                fh = self.flyout.height() if hasattr(self.flyout, "height") else 260
                # Keep inside horizontal bounds.
                if global_pt.x() + fw > avail.right() - 8:
                    global_pt.setX(max(avail.left() + 8, avail.right() - fw - 8))
                # Flip above if not enough space below.
                if global_pt.y() + fh > avail.bottom() - 8:
                    above_y = self.editor.viewport().mapToGlobal(QPoint(x, y - fh - 4)).y()
                    if above_y >= avail.top() + 8:
                        global_pt.setY(above_y)
                    else:
                        global_pt.setY(max(avail.top() + 8, avail.bottom() - fh - 8))
        except Exception:
            pass

        self.flyout.move(global_pt)
        self.flyout.show()
        try:
            self.flyout.raise_()
        except Exception:
            pass

    def _resolve_hover_content(self, text: str, line: int, col: int):
        """Delegate formatting entirely to the language provider."""
        if not self.provider or not hasattr(self.provider, "get_hover_display"):
            return None, None

        try:
            result = self.provider.get_hover_display(text, line, col)
        except Exception:
            return None, None

        if not result:
            return None, None

        return result

    def shutdown(self) -> None:
        """Stop timers and remove event filters."""
        try:
            self._hover_timer.stop()
        except Exception:
            pass
        try:
            self.editor.removeEventFilter(self)
        except Exception:
            pass
        try:
            vp = self.editor.viewport() if hasattr(self.editor, "viewport") else None
            if vp is not None:
                vp.removeEventFilter(self)
        except Exception:
            pass
        try:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
        except Exception:
            pass
        try:
            win = getattr(self, "_orig_window", None) or self.editor.window()
            if win is not None:
                win.removeEventFilter(self)
            # Also try current window if different
            cur_win = self.editor.window()
            if cur_win is not None and cur_win is not win:
                cur_win.removeEventFilter(self)
        except Exception:
            pass
