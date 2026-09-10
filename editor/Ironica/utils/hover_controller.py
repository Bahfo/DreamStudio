"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

HoverController: deterministic documentation-hover manager for DreamStudio.

The controller owns the lifetime of DocumentationFlyout.  The important rule
is that a visible flyout is kept alive only while the cursor is over either:

    1. the symbol that produced the documentation, or
    2. the flyout itself.

When the cursor leaves both regions a short grace timer is started.  This
allows the user to move from the editor into the flyout without losing it.

The editor's Leave event is intercepted here because the parent CodeEditor
must not run an independent 50 ms dismissal timer.  Having two independent
lifetime controllers was the source of the editor -> flyout race.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt6.QtCore import QEvent, QObject, QPoint, QRect, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QWidget


_HOVER_DELAY_MS = 500
_HOVER_MOVE_THRESHOLD = 3

# Time allowed to cross the gap from the symbol/editor to the flyout.
_FLYOUT_BRIDGE_MS = 350

# Time allowed after the cursor leaves the active symbol before the card closes.
_FLYOUT_CLOSE_MS = 180

# The cursor is sampled while the documentation is visible.  This deliberately
# uses the desktop/global cursor position rather than Qt child enter/leave state.
_CURSOR_TRACK_MS = 16


class HoverController(QObject):
    """Control symbol hover resolution and DocumentationFlyout lifetime."""

    def __init__(self, editor: QWidget, flyout: QWidget, provider=None) -> None:
        super().__init__(editor)

        self.editor = editor
        self.flyout = flyout
        self.provider = provider
        self._viewport = self._get_viewport()
        self._app = QApplication.instance()
        self._shutdown = False
        self._mouse_down = False

        self._target_line = -1
        self._target_col = -1
        self._target_position = -1
        self._token_rect_global = QRect()
        self._last_editor_pos = QPoint(-10_000, -10_000)

        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(_HOVER_DELAY_MS)
        self._hover_timer.timeout.connect(self._on_hover_timeout)

        self._flyout_close_timer = QTimer(self)
        self._flyout_close_timer.setSingleShot(True)
        self._flyout_close_timer.timeout.connect(self._on_close_timeout)

        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(_CURSOR_TRACK_MS)
        self._cursor_timer.timeout.connect(self._track_cursor)

        self._editor_watchers = {self.editor}
        if self._viewport is not None:
            self._editor_watchers.add(self._viewport)

        # Watch the flyout itself so clicks / hover inside the docs card
        # never destroy it.  This is the hook that lets users embed
        # interactive widgets (buttons, links, custom controls) inside the
        # flyout without losing it on interaction.
        try:
            self.flyout.installEventFilter(self)
        except Exception:
            pass
        # The browser and header are children of the flyout – clicks there
        # would otherwise bypass the flyout filter because the watched
        # object is the child widget itself.
        for _child_name in ("browser", "_header"):
            try:
                child = getattr(self.flyout, _child_name, None)
                if child is not None:
                    child.installEventFilter(self)
                    # QTextBrowser viewport is the actual hit-test widget
                    vp = getattr(child, "viewport", None)
                    if callable(vp):
                        vp().installEventFilter(self)  # type: ignore[operator]
            except Exception:
                pass

        # The controller deliberately watches both the editor and the whole
        # application.  The application filter is only used for cursor state;
        # it never tries to resolve symbols from widgets outside the editor.
        for watched in self._editor_watchers:
            watched.installEventFilter(self)
        if self._app is not None:
            self._app.installEventFilter(self)

        try:
            self.editor.destroyed.connect(self.shutdown)
        except Exception:
            pass
        try:
            self.flyout.destroyed.connect(self.shutdown)
        except Exception:
            pass

        for method_name in ("verticalScrollBar", "horizontalScrollBar"):
            try:
                bar = getattr(self.editor, method_name)()
                if bar is not None:
                    bar.valueChanged.connect(self._on_editor_scroll)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Event filtering
    # ------------------------------------------------------------------

    def _event_global_pos(self, event: QEvent) -> Optional[QPoint]:
        """Best-effort extraction of a global cursor position from *event*."""
        try:
            # QMouseEvent / QWheelEvent
            gp = getattr(event, "globalPosition", None)
            if callable(gp):
                return gp().toPoint()
            gp2 = getattr(event, "globalPos", None)
            if callable(gp2):
                return gp2()
            pos = getattr(event, "pos", None)
            if callable(pos):
                # Fallback: map local pos via watched widget if possible
                return None
        except Exception:
            pass
        return None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self._shutdown:
            return False

        event_type = event.type()

        # ------------------------------------------------------------------
        # Flyout interaction – clicks / hover inside the docs card must never
        # destroy it.  This keeps the card alive for complex embedded widgets.
        # Any mouse interaction whose global position is inside the flyout
        # (even if the watched object is a deep child not directly filtered,
        # e.g. QToolButton, QScrollBar) must reset the close timer and never
        # hide the card.
        # ------------------------------------------------------------------
        if self.flyout.isVisible() and event_type in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.Wheel,
        ):
            gpos = self._event_global_pos(event)
            if gpos is None:
                try:
                    gpos = QCursor.pos()
                except Exception:
                    gpos = None
            if gpos is not None and self._is_point_in_flyout(gpos):
                self._flyout_close_timer.stop()
                self._cursor_timer.start()
                return False
            # Also cover hover without event pos (e.g. child not filtered)
            try:
                if self._is_cursor_over_flyout():
                    self._flyout_close_timer.stop()
                    return False
            except Exception:
                pass

        # Safe ancestor check – only QWidgets have isAncestorOf
        is_flyout_related = False
        try:
            if watched is self.flyout:
                is_flyout_related = True
            elif isinstance(watched, QWidget) and self.flyout.isAncestorOf(watched):  # type: ignore[arg-type]
                is_flyout_related = True
        except Exception:
            is_flyout_related = False

        if is_flyout_related:
            if event_type in (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.MouseButtonDblClick,
                QEvent.Type.Enter,
                QEvent.Type.HoverEnter,
            ):
                # Any interaction inside the flyout resets the close countdown.
                self._flyout_close_timer.stop()
                if self.flyout.isVisible():
                    self._cursor_timer.start()
                return False
            if event_type == QEvent.Type.Leave:
                # Let the global cursor tracker decide; do not hide immediately.
                self._track_cursor()
                return False
            if event_type == QEvent.Type.Wheel:
                # Scrolling inside the docs should not dismiss it.
                self._flyout_close_timer.stop()
                return False
            if event_type == QEvent.Type.FocusIn:
                self._flyout_close_timer.stop()
                return False
            return False

        if event_type == QEvent.Type.MouseMove:
            self._track_cursor()

            if watched in self._editor_watchers:
                # Once the flyout exists, a mouse move in the editor is no
                # longer a reason to blindly keep it open.  The current symbol
                # rectangle decides whether it remains open.
                if not self._mouse_down:
                    self._handle_editor_mouse_move(watched, event)
            return False

        if watched in self._editor_watchers:
            if event_type in (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonDblClick,
            ):
                self._mouse_down = True
                self._hide_unpinned()
                return False

            if event_type == QEvent.Type.MouseButtonRelease:
                self._mouse_down = False
                return False

            if event_type in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
                self._hover_timer.stop()
                self._hide_unpinned()
                return False

            if event_type == QEvent.Type.Leave:
                self._on_editor_leave(watched)
                # Crucial: stop CodeEditor's independent leaveEvent dismissal.
                # The parent currently has a QTimer.singleShot(50, ...); that
                # race can hide the flyout while the pointer is entering it.
                if watched is self.editor:
                    return True
                return False

            if event_type == QEvent.Type.FocusOut:
                self._hover_timer.stop()
                return False

            if event_type == QEvent.Type.Wheel:
                self._on_editor_scroll()
                return False

            if event_type in (QEvent.Type.Hide, QEvent.Type.Close):
                self._hide_unpinned(force=True)
                self._cursor_timer.stop()
                return False

        # Do not use WindowDeactivate/ApplicationDeactivate at all.  The flyout
        # is a separate Tool window and activating it is a valid interaction.
        return False

    # ------------------------------------------------------------------
    # Editor hover handling
    # ------------------------------------------------------------------

    def _handle_editor_mouse_move(self, watched: QObject, event: QEvent) -> None:
        try:
            local_pos = event.position().toPoint()
        except AttributeError:
            local_pos = event.pos()

        viewport_pos = self._to_viewport_pos(watched, local_pos)
        if (viewport_pos - self._last_editor_pos).manhattanLength() <= _HOVER_MOVE_THRESHOLD:
            return

        self._last_editor_pos = viewport_pos

        line, col = self._get_line_col_at_pos(viewport_pos)
        if line < 0 or col < 0:
            self._target_line = -1
            self._target_col = -1
            self._target_position = -1
            self._token_rect_global = QRect()
            self._hover_timer.stop()
            return

        # If a flyout is already visible, moving away from its symbol starts
        # the short close countdown.  A new symbol can still start the normal
        # 500 ms hover resolution timer.
        if self.flyout.isVisible() and not self._flyout_is_pinned():
            if self._is_cursor_over_flyout() or self._is_cursor_over_target_token():
                self._flyout_close_timer.stop()
            else:
                self._flyout_close_timer.start(_FLYOUT_CLOSE_MS)

        # Resolve the currently hovered symbol normally.
        self._target_line = line
        self._target_col = col
        self._update_target_position(viewport_pos)

        self._hover_timer.stop()
        self._hover_timer.start(_HOVER_DELAY_MS)

    def _on_editor_leave(self, watched: QObject) -> None:
        self._hover_timer.stop()

        if not self.flyout.isVisible() or self._flyout_is_pinned():
            return

        # Do not call hide() here.  The next global cursor sample determines
        # whether the pointer reached the flyout during this bridge window.
        self._flyout_close_timer.start(_FLYOUT_BRIDGE_MS)
        self._cursor_timer.start()
        self._track_cursor()

    def _on_editor_scroll(self, *_args) -> None:
        self._hover_timer.stop()
        self._target_position = -1
        self._token_rect_global = QRect()
        self._hide_unpinned()

    # ------------------------------------------------------------------
    # Cursor state machine
    # ------------------------------------------------------------------

    def _track_cursor(self) -> None:
        if self._shutdown:
            self._cursor_timer.stop()
            return

        if not self.flyout.isVisible():
            self._cursor_timer.stop()
            self._flyout_close_timer.stop()
            return

        if self._flyout_is_pinned():
            self._flyout_close_timer.stop()
            return

        cursor = QCursor.pos()

        # Highest priority: being over the documentation itself always keeps
        # it alive, including every child of the QTextBrowser.
        if self._is_point_in_flyout(cursor):
            self._flyout_close_timer.stop()
            return

        # Being over the symbol that produced the card also keeps it alive.
        # This is what allows small cursor movements on a token.
        if self._is_point_in_target_token(cursor):
            self._flyout_close_timer.stop()
            return

        # Anywhere else is a departure.  The short close period is the bridge
        # window when crossing toward the flyout and the normal close grace when
        # the pointer has simply moved elsewhere in the editor/application.
        if not self._flyout_close_timer.isActive():
            self._flyout_close_timer.start(_FLYOUT_CLOSE_MS)

    def _on_close_timeout(self) -> None:
        if self._shutdown or not self.flyout.isVisible():
            self._cursor_timer.stop()
            return
        if self._flyout_is_pinned():
            return

        cursor = QCursor.pos()
        if self._is_point_in_flyout(cursor):
            return
        if self._is_point_in_target_token(cursor):
            return

        self._hide_unpinned()
        self._cursor_timer.stop()

    # ------------------------------------------------------------------
    # Documentation resolution / display
    # ------------------------------------------------------------------

    def _on_hover_timeout(self) -> None:
        if self._shutdown:
            return

        if self._target_line < 0 or self._target_col < 0:
            return

        # A delayed hover result is valid only while the pointer is still in
        # the editor.  This prevents a stale result from appearing after the
        # user has already moved into the flyout or elsewhere.
        if not self._point_inside_editor(QCursor.pos()):
            return

        try:
            text = self.editor.text()
        except Exception:
            return
        if not text:
            return

        result = self._resolve_hover_content(
            text,
            self._target_line,
            self._target_col,
        )
        if not result:
            return

        try:
            title_markdown, body_markdown = result
        except (TypeError, ValueError):
            return

        if not title_markdown and not body_markdown:
            return

        # Replace content before positioning so width/height are final before
        # hit-testing begins.
        try:
            self.flyout.set_documentation(
                title_markdown or "Documentation",
                body_markdown or "",
            )
        except Exception:
            return

        anchor = self._position_flyout_anchor(
            self._target_line,
            self._target_col,
        )
        if anchor is None:
            return

        self._update_target_token_rect()

        try:
            self.flyout.show_at(anchor)
        except Exception:
            return

        self._cursor_timer.start()
        self._track_cursor()

    def _resolve_hover_content(self, text: str, line: int, col: int):
        resolver = getattr(self.provider, "get_hover_display", None)
        if resolver is None:
            return None
        try:
            return resolver(text, line, col)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # QScintilla coordinates
    # ------------------------------------------------------------------

    def _to_viewport_pos(self, watched: QObject, pos: QPoint) -> QPoint:
        if self._viewport is None or watched is self._viewport:
            return pos
        try:
            return self._viewport.mapFromGlobal(watched.mapToGlobal(pos))
        except Exception:
            return pos

    def _get_line_col_at_pos(self, pos: QPoint) -> Tuple[int, int]:
        try:
            sci_close = getattr(self.editor, "SCI_POSITIONFROMPOINTCLOSE", None)
            if sci_close is not None:
                position = self.editor.SendScintilla(
                    sci_close,
                    pos.x(),
                    pos.y(),
                )
            else:
                position = self.editor.SendScintilla(
                    self.editor.SCI_POSITIONFROMPOINT,
                    pos.x(),
                    pos.y(),
                )
        except Exception:
            return -1, -1

        if position is None or int(position) < 0:
            return -1, -1

        self._target_position = int(position)

        try:
            line, col = self.editor.lineIndexFromPosition(position)
            return int(line), int(col)
        except Exception:
            pass

        try:
            line = self.editor.SendScintilla(
                self.editor.SCI_LINEFROMPOSITION,
                position,
            )
            col = self.editor.SendScintilla(
                self.editor.SCI_GETCOLUMN,
                position,
            )
            return int(line), int(col)
        except Exception:
            return -1, -1

    def _position_from_line_col(self, line: int, col: int) -> Optional[int]:
        try:
            return int(self.editor.positionFromLineIndex(line, col))
        except Exception:
            try:
                base = self.editor.SendScintilla(
                    self.editor.SCI_POSITIONFROMLINE,
                    line,
                )
                return int(base) + max(0, int(col))
            except Exception:
                return None

    def _position_flyout_anchor(self, line: int, col: int) -> Optional[QPoint]:
        position = self._position_from_line_col(line, col)
        if position is None:
            return None

        self._target_position = position
        try:
            x = int(self.editor.SendScintilla(
                self.editor.SCI_POINTXFROMPOSITION,
                0,
                position,
            ))
            y = int(self.editor.SendScintilla(
                self.editor.SCI_POINTYFROMPOSITION,
                0,
                position,
            ))
            line_height = max(1, int(self.editor.SendScintilla(
                self.editor.SCI_TEXTHEIGHT,
                line,
            )))
        except Exception:
            return None

        if x < 0 or y < 0 or self._viewport is None:
            return None

        try:
            return self._viewport.mapToGlobal(
                QPoint(x, y + line_height + 6)
            )
        except Exception:
            return None

    def _update_target_position(self, viewport_pos: QPoint) -> None:
        position = self.editor_position_at(viewport_pos)
        if position is not None:
            self._target_position = position
            self._update_target_token_rect()

    def editor_position_at(self, pos: QPoint) -> Optional[int]:
        try:
            sci_close = getattr(self.editor, "SCI_POSITIONFROMPOINTCLOSE", None)
            command = sci_close if sci_close is not None else self.editor.SCI_POSITIONFROMPOINT
            value = self.editor.SendScintilla(command, pos.x(), pos.y())
            value = int(value)
            return value if value >= 0 else None
        except Exception:
            return None

    def _update_target_token_rect(self) -> None:
        self._token_rect_global = QRect()
        if self._viewport is None or self._target_position < 0:
            return

        try:
            start = int(self.editor.SendScintilla(
                self.editor.SCI_WORDSTARTPOSITION,
                self._target_position,
                1,
            ))
            end = int(self.editor.SendScintilla(
                self.editor.SCI_WORDENDPOSITION,
                self._target_position,
                1,
            ))
            if end <= start:
                end = start + 1

            x1 = int(self.editor.SendScintilla(
                self.editor.SCI_POINTXFROMPOSITION,
                0,
                start,
            ))
            x2 = int(self.editor.SendScintilla(
                self.editor.SCI_POINTXFROMPOSITION,
                0,
                end,
            ))
            line = int(self.editor.SendScintilla(
                self.editor.SCI_LINEFROMPOSITION,
                self._target_position,
            ))
            y = int(self.editor.SendScintilla(
                self.editor.SCI_POINTYFROMPOSITION,
                0,
                start,
            ))
            line_height = max(1, int(self.editor.SendScintilla(
                self.editor.SCI_TEXTHEIGHT,
                line,
            )))

            left = min(x1, x2) - 2
            right = max(x1, x2) + 2
            rect = QRect(
                left,
                max(0, y - 1),
                max(3, right - left),
                line_height + 2,
            )
            top_left = self._viewport.mapToGlobal(rect.topLeft())
            bottom_right = self._viewport.mapToGlobal(rect.bottomRight())
            self._token_rect_global = QRect(top_left, bottom_right).normalized()
        except Exception:
            self._token_rect_global = QRect()

    # ------------------------------------------------------------------
    # Hit testing
    # ------------------------------------------------------------------

    def _is_point_in_flyout(self, global_pos: QPoint) -> bool:
        try:
            return bool(self.flyout.isVisible() and self.flyout.frameGeometry().contains(global_pos))
        except Exception:
            try:
                return bool(self.flyout.rect().contains(self.flyout.mapFromGlobal(global_pos)))
            except Exception:
                return False

    def _is_cursor_over_flyout(self) -> bool:
        return self._is_point_in_flyout(QCursor.pos())

    def _is_point_in_target_token(self, global_pos: QPoint) -> bool:
        return bool(not self._token_rect_global.isNull() and self._token_rect_global.contains(global_pos))

    def _is_cursor_over_target_token(self) -> bool:
        return self._is_point_in_target_token(QCursor.pos())

    def _point_inside_editor(self, global_pos: QPoint) -> bool:
        if self._viewport is not None:
            try:
                if self._viewport.isVisible() and self._viewport.rect().contains(
                    self._viewport.mapFromGlobal(global_pos)
                ):
                    return True
            except Exception:
                pass

        try:
            return bool(self.editor.isVisible() and self.editor.rect().contains(
                self.editor.mapFromGlobal(global_pos)
            ))
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Flyout lifetime
    # ------------------------------------------------------------------

    def _hide_unpinned(self, force: bool = False) -> None:
        self._flyout_close_timer.stop()
        self._hover_timer.stop()
        self._target_line = -1
        self._target_col = -1
        self._target_position = -1
        self._token_rect_global = QRect()

        if not self.flyout.isVisible():
            return
        if force or not self._flyout_is_pinned():
            try:
                self.flyout.dismiss(force=True)
            except Exception:
                try:
                    self.flyout.hide()
                except Exception:
                    pass

    def _flyout_is_pinned(self) -> bool:
        try:
            return bool(self.flyout.is_pinned)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def _get_viewport(self) -> Optional[QWidget]:
        try:
            method = getattr(self.editor, "viewport", None)
            if callable(method):
                return method()
        except Exception:
            pass
        return None

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True

        self._hover_timer.stop()
        self._flyout_close_timer.stop()
        self._cursor_timer.stop()

        for watched in tuple(self._editor_watchers):
            try:
                watched.removeEventFilter(self)
            except Exception:
                pass

        try:
            self.flyout.removeEventFilter(self)
        except Exception:
            pass
        for _child_name in ("browser", "_header"):
            try:
                child = getattr(self.flyout, _child_name, None)
                if child is not None:
                    child.removeEventFilter(self)
                    vp = getattr(child, "viewport", None)
                    if callable(vp):
                        try:
                            vp().removeEventFilter(self)  # type: ignore[operator]
                        except Exception:
                            pass
            except Exception:
                pass

        if self._app is not None:
            try:
                self._app.removeEventFilter(self)
            except Exception:
                pass
