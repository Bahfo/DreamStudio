from collections import deque

import pyte
from pyte.screens import HistoryScreen, Char
from pyte.streams import Stream

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen
from PyQt6.QtCore import pyqtSignal, Qt, QTimer

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
    "black": 0, "red": 1, "green": 2, "yellow": 3,
    "blue": 4, "magenta": 5, "cyan": 6, "white": 7,
}

def _resolve_color(color_val, fallback):
    if color_val == "default":
        return fallback
    if isinstance(color_val, str):
        if color_val.startswith("#"):
            return QColor(color_val)
        if len(color_val) == 6 and all(c in "0123456789abcdefABCDEF" for c in color_val):
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


class TerminalDisplay(QWidget):
    send_data = pyqtSignal(bytes)
    resized = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self._bg = QColor("#1e1e1e")
        self._fg = QColor("#d4d4d4")
        self._sel_bg = QColor("#264f78")

        self._columns = 80
        self._rows = 24
        self._screen = HistoryScreen(self._columns, self._rows, history=10000)
        self._stream = Stream(self._screen)

        self._font = QFont("JetBrains Mono", 12)
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        self._cw = 0
        self._ch = 0
        self._update_font_metrics()

        self._cursor_on = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._on_cursor_timer)
        self._cursor_timer.start(500)

        self._scroll_offset = 0

    _EMPTY = Char(data=" ")

    def _update_font_metrics(self):
        fm = QFontMetrics(self._font)
        self._cw = max(fm.horizontalAdvance("W"), fm.averageCharWidth())
        self._ch = fm.height()

    def _on_cursor_timer(self):
        self._cursor_on = not self._cursor_on
        if self.isVisible():
            self.update()

    def resizeEvent(self, event):
        if self._cw > 0 and self._ch > 0:
            cols = max(20, self.width() // self._cw)
            rows = max(5, self.height() // self._ch)
            if cols != self._columns or rows != self._rows:
                self._columns = cols
                self._rows = rows
                self._screen.resize(rows, cols)
                self._scroll_offset = 0
                self.resized.emit(rows, cols)
                self.update()

    def feed(self, text: str) -> None:
        self._stream.feed(text)
        self._scroll_offset = 0
        self.update()

    def _count_history_lines(self) -> int:
        count = 0
        for page in self._screen.history:
            if isinstance(page, (deque, list, tuple)):
                count += len(page)
        return count

    def _get_visible_lines(self):
        total_hist = self._count_history_lines()
        total = total_hist + self._rows
        start = max(0, total - self._rows - self._scroll_offset)

        lines = []
        need = self._rows
        cursor = 0

        for page in self._screen.history:
            if not isinstance(page, (deque, list, tuple)) or not page:
                continue
            for line_dict in page:
                if not isinstance(line_dict, dict):
                    continue
                if cursor >= start:
                    lines.append(line_dict)
                    need -= 1
                    if need <= 0:
                        return lines
                cursor += 1

        for row in range(self._rows):
            if need <= 0:
                break
            if cursor >= start:
                row_buf = self._screen.buffer.get(row, {})
                line = {}
                for col in range(self._columns):
                    c = row_buf.get(col)
                    line[col] = c or self._EMPTY
                lines.append(line)
                need -= 1
            cursor += 1

        return lines

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(self._font)

        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, self._bg)

        visible = self._get_visible_lines()
        visible_rows = min(len(visible), h // self._ch)
        visible_cols = min(self._columns, w // self._cw)

        for row_idx in range(visible_rows):
            line_dict = visible[row_idx]
            y = row_idx * self._ch
            col = 0
            while col < visible_cols:
                c = line_dict.get(col, self._EMPTY)
                qfg, qbg, bold, italics, underscore, blink = self._resolve_attrs(c)

                run_start = col
                col += 1
                while col < visible_cols:
                    nc = line_dict.get(col, self._EMPTY)
                    nqfg, nqbg, nbold, nitalics, nunderscore, nblink = self._resolve_attrs(nc)
                    if (nqfg != qfg or nqbg != qbg or nbold != bold
                            or nitalics != italics or nunderscore != underscore):
                        break
                    col += 1

                run_width = (col - run_start) * self._cw
                x = run_start * self._cw

                if qbg != self._bg:
                    painter.fillRect(x, y, run_width, self._ch, qbg)

                if bold or italics:
                    f = QFont(self._font)
                    f.setBold(bold)
                    f.setItalic(italics)
                    painter.setFont(f)
                else:
                    painter.setFont(self._font)

                text = "".join(
                    line_dict.get(c, self._EMPTY).data for c in range(run_start, col)
                )
                painter.setPen(QPen(qfg))
                painter.drawText(x, y, run_width, self._ch,
                                 Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                                 text)

                if underscore:
                    painter.drawLine(x, y + self._ch - 2, x + run_width, y + self._ch - 2)

                if blink and self._cursor_on:
                    painter.fillRect(x, y, run_width, self._ch, qfg)
                    painter.setPen(QPen(qbg))
                    painter.drawText(x, y, run_width, self._ch,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                                     text)

        if self._cursor_on and self.hasFocus() and self._scroll_offset == 0:
            cx = self._screen.cursor.x * self._cw
            cy = self._screen.cursor.y * self._ch
            if cy < visible_rows * self._ch:
                painter.fillRect(cx, cy, self._cw, self._ch, self._fg)
                d = self._screen.display
                ch = " "
                if self._screen.cursor.y < len(d) and self._screen.cursor.x < len(d[self._screen.cursor.y]):
                    ch = d[self._screen.cursor.y][self._screen.cursor.x]
                painter.setPen(QPen(self._bg))
                painter.drawText(cx, cy, self._cw, self._ch,
                                 Qt.AlignmentFlag.AlignCenter, ch)

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        text = event.text()

        if key in _KEY_IGNORE:
            return

        if mods & Qt.KeyboardModifier.ControlModifier:
            if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
                self.send_data.emit(bytes([key - Qt.Key.Key_A + 1]))
                return
            if key in (Qt.Key.Key_Space, Qt.Key.Key_At, Qt.Key.Key_2):
                self.send_data.emit(b"\x00")
                return
            if key == Qt.Key.Key_Backspace:
                self.send_data.emit(b"\x7f")
                return
            if key == Qt.Key.Key_6:
                self.send_data.emit(b"\x1e")
                return
            if key == Qt.Key.Key_Minus:
                self.send_data.emit(b"\x1f")
                return

        if mods == Qt.KeyboardModifier.AltModifier:
            if text:
                self.send_data.emit(b"\x1b" + text.encode("utf-8"))
                return
            if key in KEY_MAP:
                self.send_data.emit(b"\x1b" + KEY_MAP[key])
                return

        if key in KEY_MAP:
            self.send_data.emit(KEY_MAP[key])
            return

        if text:
            self.send_data.emit(text.encode("utf-8"))

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        hist_lines = self._count_history_lines()
        if delta > 0:
            self._scroll_offset = min(self._scroll_offset + 3, hist_lines)
        elif delta < 0:
            self._scroll_offset = max(self._scroll_offset - 3, 0)
        self.update()

    def set_theme(self, bg: str, fg: str, sel_bg: str) -> None:
        self._bg = QColor(bg)
        self._fg = QColor(fg)
        self._sel_bg = QColor(sel_bg)
        self.update()

    def reset(self) -> None:
        self._screen.reset()
        self._scroll_offset = 0
        self.update()
