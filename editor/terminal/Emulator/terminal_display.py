"""
(C) COPYRIGHT 2026 EXcellent TechStacks
Terminal Emulator Logic for DreamStudio.
"""

from editor import *

from pyte.screens import HistoryScreen, Char
from pyte.streams import Stream


ANSI_COLORS = [
    QColor(0x00, 0x00, 0x00),
    QColor(0xCD, 0x00, 0x00),
    QColor(0x00, 0xCD, 0x00),
    QColor(0xCD, 0xCD, 0x00),
    QColor(0x00, 0x00, 0xCD),
    QColor(0xCD, 0x00, 0xCD),
    QColor(0x00, 0xCD, 0xCD),
    QColor(0xE5, 0xE5, 0xE5),
    QColor(0x7F, 0x7F, 0x7F),
    QColor(0xFF, 0x00, 0x00),
    QColor(0x00, 0xFF, 0x00),
    QColor(0xFF, 0xFF, 0x00),
    QColor(0x00, 0x00, 0xFF),
    QColor(0xFF, 0x00, 0xFF),
    QColor(0x00, 0xFF, 0xFF),
    QColor(0xFF, 0xFF, 0xFF),
]


def _build_256_colors():
    colors = [QColor(0, 0, 0)] * 256
    for i in range(16):
        colors[i] = ANSI_COLORS[i]
    for r in range(6):
        for g in range(6):
            for b in range(6):
                idx = 16 + r * 36 + g * 6 + b
                colors[idx] = QColor(
                    int(r * 255 / 5) if r > 0 else 0,
                    int(g * 255 / 5) if g > 0 else 0,
                    int(b * 255 / 5) if b > 0 else 0,
                )
    for i in range(24):
        idx = 232 + i
        v = int(i * 255 / 23) + 8
        colors[idx] = QColor(v, v, v)
    return colors


COLORS_256 = _build_256_colors()


_NAMED_COLORS = {
    "black": 0,
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
}


def _resolve_color(color_val, fallback):
    if color_val == "default":
        return fallback
    if isinstance(color_val, str):
        if color_val.startswith("#"):
            return QColor(color_val)
        if len(color_val) == 6 and all(
            c in "0123456789abcdefABCDEF" for c in color_val
        ):
            return QColor("#" + color_val)
        name = color_val.lower()
        if name.startswith("bright"):
            name = name[6:]
            idx = _NAMED_COLORS.get(name)
            if idx is not None:
                return ANSI_COLORS[idx + 8]
        idx = _NAMED_COLORS.get(name)
        if idx is not None:
            return ANSI_COLORS[idx]
    try:
        idx = int(color_val)
        if 0 <= idx < 256:
            return COLORS_256[idx]
    except (ValueError, TypeError):
        pass
    return fallback


KEY_MAP = {
    Qt.Key.Key_Up: b"\x1b[A",
    Qt.Key.Key_Down: b"\x1b[B",
    Qt.Key.Key_Right: b"\x1b[C",
    Qt.Key.Key_Left: b"\x1b[D",
    Qt.Key.Key_Home: b"\x1b[H",
    Qt.Key.Key_End: b"\x1b[F",
    Qt.Key.Key_PageUp: b"\x1b[5~",
    Qt.Key.Key_PageDown: b"\x1b[6~",
    Qt.Key.Key_Insert: b"\x1b[2~",
    Qt.Key.Key_Delete: b"\x1b[3~",
    Qt.Key.Key_Backspace: b"\x7f",
    Qt.Key.Key_Tab: b"\t",
    Qt.Key.Key_Return: b"\r",
    Qt.Key.Key_Enter: b"\r",
    Qt.Key.Key_Escape: b"\x1b",
    Qt.Key.Key_F1: b"\x1bOP",
    Qt.Key.Key_F2: b"\x1bOQ",
    Qt.Key.Key_F3: b"\x1bOR",
    Qt.Key.Key_F4: b"\x1bOS",
    Qt.Key.Key_F5: b"\x1b[15~",
    Qt.Key.Key_F6: b"\x1b[17~",
    Qt.Key.Key_F7: b"\x1b[18~",
    Qt.Key.Key_F8: b"\x1b[19~",
    Qt.Key.Key_F9: b"\x1b[20~",
    Qt.Key.Key_F10: b"\x1b[21~",
    Qt.Key.Key_F11: b"\x1b[23~",
    Qt.Key.Key_F12: b"\x1b[24~",
}

_KEY_IGNORE = {
    Qt.Key.Key_Control,
    Qt.Key.Key_Shift,
    Qt.Key.Key_Alt,
    Qt.Key.Key_Meta,
    Qt.Key.Key_CapsLock,
    Qt.Key.Key_NumLock,
    Qt.Key.Key_ScrollLock,
    Qt.Key.Key_Super_L,
    Qt.Key.Key_Super_R,
    Qt.Key.Key_Menu,
}

# -----------------------------------------------------------------------
# Ctrl+key → control character mapping.
#
# Replaces the old raw arithmetic ``key - Qt.Key.Key_A + 1`` which broke
# on non-QWERTY / international keyboard layouts where the Qt key code
# for the physical "A" key might not correspond to the letter 'A' in the
# active keymap.  This table maps every Qt.Key.Key_A..Key_Z value to the
# corresponding ASCII control code (0x01–0x1A) independently of layout.
# -----------------------------------------------------------------------
_CTRL_KEY_MAP = {
    Qt.Key.Key_A: 0x01, Qt.Key.Key_B: 0x02, Qt.Key.Key_C: 0x03,
    Qt.Key.Key_D: 0x04, Qt.Key.Key_E: 0x05, Qt.Key.Key_F: 0x06,
    Qt.Key.Key_G: 0x07, Qt.Key.Key_H: 0x08, Qt.Key.Key_I: 0x09,
    Qt.Key.Key_J: 0x0A, Qt.Key.Key_K: 0x0B, Qt.Key.Key_L: 0x0C,
    Qt.Key.Key_M: 0x0D, Qt.Key.Key_N: 0x0E, Qt.Key.Key_O: 0x0F,
    Qt.Key.Key_P: 0x10, Qt.Key.Key_Q: 0x11, Qt.Key.Key_R: 0x12,
    Qt.Key.Key_S: 0x13, Qt.Key.Key_T: 0x14, Qt.Key.Key_U: 0x15,
    Qt.Key.Key_V: 0x16, Qt.Key.Key_W: 0x17, Qt.Key.Key_X: 0x18,
    Qt.Key.Key_Y: 0x19, Qt.Key.Key_Z: 0x1A,
}


class TerminalDisplay(QWidget):
    send_data = pyqtSignal(bytes)
    resized = pyqtSignal(int, int)
    history_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StaticContents, True)

        self._bg = QColor("#1e1e1e")
        self._fg = QColor("#d4d4d4")
        self._sel_bg = QColor("#264f78")

        self._columns = 80
        self._rows = 24
        self._screen = HistoryScreen(self._columns, self._rows, history=10000)
        self._stream = Stream(self._screen)

        self._font = QFont("JetBrains Mono", 10)
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        self._cw = 0
        self._ch = 0
        self._update_font_metrics()

        self._cursor_on = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._on_cursor_timer)
        self._cursor_timer.start(500)

        self._scroll_offset = 0
        self._emulator = None

        self._visible_cache: list[dict] = []
        self._cache_valid = False

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._apply_resize)
        self._pending_cols = 0
        self._pending_rows = 0
        self._resizing = False

        # Selection state — stores ABSOLUTE indices (absolute line number
        # in the history+buffer space, column index) rather than relative
        # visible-window indices.  This ensures highlights stay correct
        # when the user scrolls after selecting text.
        self._sel_active = False
        self._sel_start: tuple[int, int] | None = None
        self._sel_end: tuple[int, int] | None = None
        self._pending_feed: list[str] = []

    _EMPTY = Char(data=" ")

    def set_emulator(self, emulator) -> None:
        self._emulator = emulator

    def _update_font_metrics(self):
        fm = QFontMetrics(self._font)
        self._cw = max(fm.horizontalAdvance("W"), fm.averageCharWidth())
        self._ch = fm.height()

    def _on_cursor_timer(self):
        self._cursor_on = not self._cursor_on
        if (self.isVisible() and self.hasFocus()
                and self._scroll_offset == 0 and self._cw > 0 and self._ch > 0):
            cx = self._screen.cursor.x * self._cw
            cy = self._screen.cursor.y * self._ch
            self.update(cx, cy, self._cw, self._ch)

    # ------------------------------------------------------------------
    # History line access — O(1) via pyte's internal top/bottom deques
    # ------------------------------------------------------------------

    def _count_history_lines(self) -> int:
        """O(1) total history line count.

        pyte's HistoryScreen stores individual lines (not full-screen
        pages) in two deques: ``history.top`` (lines that scrolled off
        the top) and ``history.bottom`` (lines that scrolled off the
        bottom during pagination).  The total is simply the sum of both
        deque lengths — no sequential iteration required.
        """
        history = self._screen.history
        return len(history.top) + len(history.bottom)

    def _get_history_line(self, abs_idx: int):
        """O(1) access to a history line by absolute index.

        Lines are ordered chronologically: ``top[0]`` is the oldest line
        that scrolled off the top, ``top[-1]`` is the newest.  ``bottom``
        follows ``top`` in the flat index space.
        """
        history = self._screen.history
        top_len = len(history.top)
        if abs_idx < top_len:
            return history.top[abs_idx]
        bottom_idx = abs_idx - top_len
        if bottom_idx < len(history.bottom):
            return history.bottom[bottom_idx]
        return None

    # ------------------------------------------------------------------
    # Absolute ↔ visible row mapping (Step 6)
    # ------------------------------------------------------------------

    def _visible_start_index(self) -> int:
        """Compute the absolute index of the topmost visible line.

        When ``_scroll_offset == 0`` the window sits at the bottom of the
        buffer — all visible rows come from the live screen buffer.  As
        the offset increases, the window slides back into history.
        """
        total_hist = self._count_history_lines()
        total = total_hist + self._rows
        return max(0, total - self._rows - self._scroll_offset)

    def _absolute_to_visible_row(self, abs_idx: int) -> int | None:
        """Map an absolute line index to a visible-row index, or ``None``
        if the line falls outside the current viewport."""
        start = self._visible_start_index()
        vis_row = abs_idx - start
        if vis_row < 0 or vis_row >= self._rows:
            return None
        return vis_row

    def _visible_to_absolute_row(self, vis_row: int) -> int:
        """Map a visible-row index to an absolute line index."""
        return self._visible_start_index() + vis_row

    # ------------------------------------------------------------------
    # Selection helpers (Step 6 — absolute tracing)
    # ------------------------------------------------------------------

    def _get_selection_bounds(self):
        """Return selection bounds as visible coordinates
        ``((vis_r1, c1), (vis_r2, c2))`` or ``None``.

        Performs direct absolute-index comparisons against the current
        viewport window rather than relying on per-boundary ``None``
        checks from ``_absolute_to_visible_row``.  This prevents the
        bug where a boundary below the viewport was erroneously forced
        to row 0 (flipping the selection logic) and where a selection
        spanning the entire viewport returned ``None`` because both
        individual boundaries fell outside.

        Clamping rules per boundary:
        * abs < viewport start → visible row 0, col 0
        * abs >= viewport end  → visible row (rows-1), col (columns-1)
        * otherwise            → direct subtraction from start

        Returns ``None`` only if the *entire* absolute selection block
        is fully above the viewport (both < start) or fully below it
        (both >= end).
        """
        if self._sel_start is None or self._sel_end is None:
            return None
        abs_r1, c1 = self._sel_start
        abs_r2, c2 = self._sel_end

        # Absolute viewport window: [start, end).
        start = self._visible_start_index()
        end = start + self._rows

        # Entire selection is above the viewport — nothing visible.
        if abs_r1 < start and abs_r2 < start:
            return None
        # Entire selection is below the viewport — nothing visible.
        if abs_r1 >= end and abs_r2 >= end:
            return None

        # Clamp abs_r1 boundary against the viewport window.
        if abs_r1 < start:
            vis_r1 = 0
            c1 = 0
        elif abs_r1 >= end:
            vis_r1 = self._rows - 1
            c1 = self._columns - 1
        else:
            vis_r1 = abs_r1 - start

        # Clamp abs_r2 boundary against the viewport window.
        if abs_r2 < start:
            vis_r2 = 0
            c2 = 0
        elif abs_r2 >= end:
            vis_r2 = self._rows - 1
            c2 = self._columns - 1
        else:
            vis_r2 = abs_r2 - start

        # Normalise so (vis_r1, c1) is always the top-left corner.
        if vis_r1 < vis_r2 or (vis_r1 == vis_r2 and c1 <= c2):
            return ((vis_r1, c1), (vis_r2, c2))
        return ((vis_r2, c2), (vis_r1, c1))

    def _get_selection_range(self, vis_row):
        bounds = self._get_selection_bounds()
        if bounds is None:
            return None
        (top_r, top_c), (bot_r, bot_c) = bounds
        if vis_row < top_r or vis_row > bot_r:
            return None
        if top_r == bot_r:
            return (min(top_c, bot_c), max(top_c, bot_c))
        if vis_row == top_r:
            return (top_c, self._columns - 1)
        if vis_row == bot_r:
            return (0, bot_c)
        return (0, self._columns - 1)

    def _get_selection_text(self):
        if self._sel_start is None or self._sel_end is None:
            return ""
        abs_r1, c1 = self._sel_start
        abs_r2, c2 = self._sel_end
        # Normalise so abs_r1 ≤ abs_r2.
        if abs_r1 > abs_r2 or (abs_r1 == abs_r2 and c1 > c2):
            abs_r1, c1, abs_r2, c2 = abs_r2, c2, abs_r1, c1

        visible = self._get_visible_lines()
        start = self._visible_start_index()
        parts = []
        for abs_r in range(abs_r1, abs_r2 + 1):
            vis_r = abs_r - start
            if vis_r < 0 or vis_r >= len(visible):
                continue
            line = visible[vis_r]
            if abs_r == abs_r1 and abs_r == abs_r2:
                cols = range(c1, c2 + 1)
            elif abs_r == abs_r1:
                cols = range(c1, self._columns)
            elif abs_r == abs_r2:
                cols = range(0, c2 + 1)
            else:
                cols = range(0, self._columns)
            text = "".join(line.get(col, self._EMPTY).data for col in cols)
            parts.append(text.rstrip())
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Mouse events — store absolute indices
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._sel_active = False
            self._sel_start = None
            self._sel_end = None
            visible = self._get_visible_lines()
            if self._cw <= 0 or self._ch <= 0:
                self.update()
                event.accept()
                return
            row = int(event.position().y() // self._ch)
            col = int(event.position().x() // self._cw)
            if 0 <= col < self._columns and 0 <= row < len(visible):
                abs_row = self._visible_to_absolute_row(row)
                self._sel_start = (abs_row, col)
                self._sel_end = (abs_row, col)
                self._sel_active = True
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._sel_active and event.buttons() & Qt.MouseButton.LeftButton:
            visible = self._get_visible_lines()
            if self._cw <= 0 or self._ch <= 0:
                event.accept()
                return
            row = int(event.position().y() // self._ch)
            col = int(event.position().x() // self._cw)
            col = max(0, min(col, self._columns - 1))
            row = max(0, min(row, len(visible) - 1))
            abs_row = self._visible_to_absolute_row(row)
            if self._sel_end != (abs_row, col):
                self._sel_end = (abs_row, col)
                self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._sel_active:
            text = self._get_selection_text()
            if text:
                QApplication.clipboard().setText(text)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def scroll_offset(self) -> int:
        return self._scroll_offset

    def set_scroll_offset(self, offset: int) -> None:
        hist_lines = self._count_history_lines()
        offset = max(0, min(offset, hist_lines))
        if offset != self._scroll_offset:
            self._scroll_offset = offset
            self._cache_valid = False
            self.update()
            self.history_changed.emit(self._scroll_offset, hist_lines)

    def resizeEvent(self, event):
        if self._cw > 0 and self._ch > 0:
            cols = max(20, self.width() // self._cw)
            rows = max(5, self.height() // self._ch)
            if cols != self._columns or rows != self._rows:
                self._pending_cols = cols
                self._pending_rows = rows
                self._resize_timer.start(50)

    def _apply_resize(self):
        if not self.isVisible():
            return
        cols = self._pending_cols
        rows = self._pending_rows
        if cols < 1 or rows < 1:
            return
        if cols == self._columns and rows == self._rows:
            return
        self._resizing = True
        try:
            self._columns = cols
            self._rows = rows
            self._screen.resize(rows, cols)
            self._scroll_offset = 0
            self._cache_valid = False
            self.resized.emit(rows, cols)
            if self._emulator is not None:
                self._emulator.resize(rows, cols)
        finally:
            self._resizing = False
        # Drain any feeds buffered while resizing
        if self._pending_feed:
            pending = "".join(self._pending_feed)
            self._pending_feed.clear()
            try:
                self._stream.feed(pending)
            except Exception:
                pass
        self.update()
        self.history_changed.emit(0, self._count_history_lines())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._pending_feed:
            pending = "".join(self._pending_feed)
            self._pending_feed.clear()
            try:
                self._stream.feed(pending)
            except Exception:
                pass
            self._cache_valid = False
            self.update()
            self.history_changed.emit(0, self._count_history_lines())

    def feed(self, text: str) -> None:
        if self._resizing or not self.isVisible():
            self._pending_feed.append(text)
            # Prevent unbounded growth – join and truncate if too large
            if len(self._pending_feed) > 1000:
                self._pending_feed = ["".join(self._pending_feed)]
            return
        try:
            self._stream.feed(text)
        except Exception:
            return
        self._scroll_offset = 0
        self._cache_valid = False
        self.update()
        self.history_changed.emit(0, self._count_history_lines())

    # ------------------------------------------------------------------
    # Visible cache — O(1) history indexing (Step 3)
    # ------------------------------------------------------------------

    def _build_visible_cache(self):
        """Build the visible-line cache using O(1) direct indexing into
        pyte's ``history.top`` / ``history.bottom`` deques instead of
        iterating through every history line sequentially.

        Complexity: O(rows) — only the currently-visible rows are
        resolved; total history size is irrelevant.
        """
        total_hist = self._count_history_lines()
        total = total_hist + self._rows
        start = max(0, total - self._rows - self._scroll_offset)

        lines = []
        for vis_row in range(self._rows):
            abs_idx = start + vis_row
            if abs_idx < total_hist:
                # O(1) direct access into pyte's internal history deques.
                line = self._get_history_line(abs_idx)
                if line is not None and isinstance(line, dict):
                    lines.append(line)
                else:
                    lines.append(self._EMPTY)
            else:
                # Live screen buffer row — direct dictionary lookup.
                buf_row = abs_idx - total_hist
                row_buf = self._screen.buffer.get(buf_row, {})
                line = {}
                for col in range(self._columns):
                    c = row_buf.get(col)
                    line[col] = c or self._EMPTY
                lines.append(line)

        self._visible_cache = lines
        self._cache_valid = True

    def _get_visible_lines(self):
        if not self._cache_valid:
            self._build_visible_cache()
        return self._visible_cache

    def _resolve_attrs(self, c):
        fg = c.fg
        bg = c.bg
        bold = getattr(c, "bold", False)
        italics = getattr(c, "italics", False)
        underscore = getattr(c, "underscore", False)
        reverse = getattr(c, "reverse", False)
        blink = getattr(c, "blink", False)
        if reverse:
            qfg = _resolve_color(bg if bg != "default" else "default", self._bg)
            qbg = _resolve_color(fg if fg != "default" else "default", self._fg)
        else:
            qfg = _resolve_color(fg, self._fg)
            qbg = _resolve_color(bg, self._bg)
        return qfg, qbg, bold, italics, underscore, blink

    # ------------------------------------------------------------------
    # Paint — event-rect clipping (Step 2)
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        if self._cw < 1 or self._ch < 1:
            return
        painter = QPainter(self)
        painter.setFont(self._font)
        default_fm = QFontMetrics(self._font)
        default_baseline = default_fm.ascent()

        w = self.width()
        h = self.height()

        # Use the damaged region from the event to clip all drawing
        # operations.  Qt coalesces multiple update() calls into a single
        # paint event whose rect is the bounding box of all pending
        # changes.  By computing the row/column slice that intersects
        # this rect we avoid redrawing the entire terminal on every
        # keystroke or streaming stdout burst.
        damaged = event.rect()
        painter.fillRect(damaged, self._bg)

        visible = self._get_visible_lines()
        if not visible:
            painter.end()
            return

        cell_h = self._ch
        cell_w = self._cw
        visible_rows = min(len(visible), h // cell_h)
        visible_cols = min(self._columns, w // cell_w)

        # Clip the painter to the damaged region so that text drawn via
        # drawText can never overflow outside the repaint viewport.  This
        # is a native QPainter clip — it does not affect any external
        # widget layouts or margins.
        painter.setClipRect(damaged)

        # Compute the exact row and column slices that intersect the
        # damaged area.  Only these cells are redrawn.
        start_row = max(0, damaged.top() // cell_h)
        end_row = min(visible_rows, (damaged.bottom() + cell_h) // cell_h)
        start_col = max(0, damaged.left() // cell_w)
        end_col = min(visible_cols, (damaged.right() + cell_w) // cell_w)

        for row_idx in range(start_row, end_row):
            line_dict = visible[row_idx]
            y = row_idx * cell_h
            sel_range = self._get_selection_range(row_idx)
            col = start_col
            while col < end_col:
                c = line_dict.get(col, self._EMPTY)
                qfg, qbg, bold, italics, underscore, blink = self._resolve_attrs(c)
                is_sel = sel_range is not None and sel_range[0] <= col <= sel_range[1]

                run_start = col
                col += 1
                while col < end_col:
                    nc = line_dict.get(col, self._EMPTY)
                    nqfg, nqbg, nbold, nitalics, nunderscore, nblink = (
                        self._resolve_attrs(nc)
                    )
                    n_is_sel = (
                        sel_range is not None and sel_range[0] <= col <= sel_range[1]
                    )
                    if (
                        nqfg != qfg
                        or nqbg != qbg
                        or nbold != bold
                        or nitalics != italics
                        or nunderscore != underscore
                        or n_is_sel != is_sel
                    ):
                        break
                    col += 1

                run_width = (col - run_start) * cell_w
                x = run_start * cell_w

                if is_sel:
                    painter.fillRect(x, y, run_width, cell_h, self._sel_bg)
                elif qbg != self._bg:
                    painter.fillRect(x, y, run_width, cell_h, qbg)

                if bold or italics:
                    f = QFont(self._font)
                    f.setBold(bold)
                    f.setItalic(italics)
                    painter.setFont(f)
                    baseline = QFontMetrics(f).ascent()
                else:
                    painter.setFont(self._font)
                    baseline = default_baseline

                text = "".join(
                    line_dict.get(c, self._EMPTY).data for c in range(run_start, col)
                )
                painter.setPen(QPen(qfg))
                painter.drawText(x, y + baseline, text)

                if underscore:
                    painter.drawLine(x, y + cell_h - 2, x + run_width, y + cell_h - 2)

                if blink and self._cursor_on:
                    painter.fillRect(x, y, run_width, cell_h, qfg)
                    painter.setPen(QPen(qbg))
                    painter.drawText(x, y + baseline, text)

        # Draw the cursor if it falls within the damaged region.
        if self._cursor_on and self.hasFocus() and self._scroll_offset == 0:
            cx = self._screen.cursor.x * cell_w
            cy = self._screen.cursor.y * cell_h
            cursor_rect = QRect(int(cx), int(cy), cell_w, cell_h)
            if cy < visible_rows * cell_h and cx < w - cell_w and damaged.intersects(cursor_rect):
                painter.fillRect(cx, cy, cell_w, cell_h, self._fg)
                d = self._screen.display
                ch = " "
                try:
                    if (self._screen.cursor.y < len(d)
                            and self._screen.cursor.x < len(d[self._screen.cursor.y])):
                        ch = d[self._screen.cursor.y][self._screen.cursor.x]
                except (IndexError, TypeError):
                    pass
                painter.setPen(QPen(self._bg))
                painter.drawText(cx, cy + default_baseline, ch)

        painter.end()

    # ------------------------------------------------------------------
    # Keyboard — safe Ctrl+key translation matrix (Step 10)
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        text = event.text()

        if key in _KEY_IGNORE:
            event.accept()
            return

        if (
            mods
            == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
            and key == Qt.Key.Key_V
        ):
            cb = QApplication.clipboard()
            cb_text = cb.text()
            if cb_text:
                self.send_data.emit(cb_text.encode("utf-8"))
            event.accept()
            return

        if mods == Qt.KeyboardModifier.ShiftModifier and key == Qt.Key.Key_Insert:
            cb = QApplication.clipboard()
            cb_text = cb.text()
            if cb_text:
                self.send_data.emit(cb_text.encode("utf-8"))
            event.accept()
            return

        if mods & Qt.KeyboardModifier.ControlModifier:
            # Use the pre-computed control-key translation table instead of
            # raw ``key - Qt.Key.Key_A + 1`` arithmetic.  The table maps
            # each Qt.Key.Key_A..Key_Z value to its ASCII control code
            # (0x01–0x1A) regardless of keyboard layout, preventing crashes
            # and incorrect mappings on AZERTY, Dvorak, Colemak, Cyrillic,
            # and other non-QWERTY layers.
            if key in _CTRL_KEY_MAP:
                self.send_data.emit(bytes([_CTRL_KEY_MAP[key]]))
                event.accept()
                return
            if key in (Qt.Key.Key_Space, Qt.Key.Key_At, Qt.Key.Key_2):
                self.send_data.emit(b"\x00")
                event.accept()
                return
            if key == Qt.Key.Key_Backspace:
                self.send_data.emit(b"\x7f")
                event.accept()
                return
            if key == Qt.Key.Key_6:
                self.send_data.emit(b"\x1e")
                event.accept()
                return
            if key == Qt.Key.Key_Minus:
                self.send_data.emit(b"\x1f")
                event.accept()
                return

        if mods == Qt.KeyboardModifier.AltModifier:
            if text:
                self.send_data.emit(b"\x1b" + text.encode("utf-8"))
                event.accept()
                return
            if key in KEY_MAP:
                self.send_data.emit(b"\x1b" + KEY_MAP[key])
                event.accept()
                return

        if key in KEY_MAP:
            self.send_data.emit(KEY_MAP[key])
            event.accept()
            return

        if text:
            self.send_data.emit(text.encode("utf-8"))
            event.accept()
            return

        event.accept()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        hist_lines = self._count_history_lines()
        if delta > 0:
            self._scroll_offset = min(self._scroll_offset + 3, hist_lines)
        elif delta < 0:
            self._scroll_offset = max(self._scroll_offset - 3, 0)
        self._cache_valid = False
        if self._cw > 0 and self._ch > 0:
            self.update()
        self.history_changed.emit(self._scroll_offset, hist_lines)

    def set_theme(self, bg: str, fg: str, sel_bg: str) -> None:
        self._bg = QColor(bg)
        self._fg = QColor(fg)
        self._sel_bg = QColor(sel_bg)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.update()

    def reset(self) -> None:
        self._screen.reset()
        self._scroll_offset = 0
        self._cache_valid = False
        self.update()
