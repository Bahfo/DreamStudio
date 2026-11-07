"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Deep protocol-level tests for TerminalDisplay ANSI handling.
"""

import sys

import pytest

from editor.terminal.Emulator.terminal_display import TerminalDisplay, ANSI_COLORS


class TestProtocolText:
    def _make(self, qapp):
        td = TerminalDisplay()
        td.show()
        qapp.processEvents()
        return td

    def test_plain_text(self, qapp):
        td = self._make(qapp)
        td.feed("Hello")
        row = td._screen.buffer.get(0, {})
        text = "".join((row.get(c) and row[c].data or " ") for c in range(5))
        assert text == "Hello"
        assert td._screen.cursor.x == 5
        td.deleteLater()

    def test_newline_and_carriage_return(self, qapp):
        td = self._make(qapp)
        td.feed("AB\r\nCD")
        assert td._screen.buffer[0][0].data == "A"
        assert td._screen.buffer[0][1].data == "B"
        assert td._screen.buffer[1][0].data == "C"
        assert td._screen.buffer[1][1].data == "D"
        td.deleteLater()

    def test_backspace(self, qapp):
        td = self._make(qapp)
        td.feed("AB\bC")
        row = td._screen.buffer[0]
        assert row[0].data == "A"
        assert row[1].data == "C"
        td.deleteLater()

    def test_tab(self, qapp):
        td = self._make(qapp)
        td.feed("A\tB")
        # tab moves to next tab stop (8)
        assert td._screen.buffer[0][8].data == "B"
        td.deleteLater()


class TestProtocolColors:
    def _make(self, qapp):
        td = TerminalDisplay()
        td.show()
        qapp.processEvents()
        return td

    def test_standard_fg_color(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[31mR\x1b[0m")
        cell = td._screen.buffer[0][0]
        assert cell.data == "R"
        # pyte stores fg as color name/index; check not default
        assert cell.fg != "default"
        td.deleteLater()

    def test_256_color(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[38;5;196mX\x1b[0m")
        cell = td._screen.buffer[0][0]
        assert cell.data == "X"
        assert cell.fg not in ("default",)
        td.deleteLater()

    def test_rgb_color(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[38;2;10;20;30mY\x1b[0m")
        cell = td._screen.buffer[0][0]
        assert cell.data == "Y"
        td.deleteLater()

    def test_background_color(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[42mG\x1b[0m")
        cell = td._screen.buffer[0][0]
        assert cell.data == "G"
        assert cell.bg != "default"
        td.deleteLater()


class TestProtocolAttributes:
    def _make(self, qapp):
        td = TerminalDisplay()
        td.show()
        qapp.processEvents()
        return td

    def test_bold(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[1mB\x1b[0m")
        assert td._screen.buffer[0][0].bold is True
        td.deleteLater()

    def test_italic(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[3mI\x1b[0m")
        assert td._screen.buffer[0][0].italics is True
        td.deleteLater()

    def test_underline(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[4mU\x1b[0m")
        assert td._screen.buffer[0][0].underscore is True
        td.deleteLater()

    def test_reverse(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[7mV\x1b[0m")
        assert td._screen.buffer[0][0].reverse is True
        td.deleteLater()

    def test_blink(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[5mK\x1b[0m")
        assert td._screen.buffer[0][0].blink is True
        td.deleteLater()

    def test_reset_clears_attributes(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[1mB\x1b[0mN")
        assert td._screen.buffer[0][0].bold is True
        assert td._screen.buffer[0][1].bold is False
        td.deleteLater()

    def test_combined_attributes(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[1;3;4mC\x1b[0m")
        cell = td._screen.buffer[0][0]
        assert cell.bold and cell.italics and cell.underscore
        td.deleteLater()


class TestProtocolCursor:
    def _make(self, qapp):
        td = TerminalDisplay()
        td.show()
        qapp.processEvents()
        return td

    def test_cursor_position_escape(self, qapp):
        td = self._make(qapp)
        td.feed("\x1b[3;5H")
        assert td._screen.cursor.y == 2
        assert td._screen.cursor.x == 4
        td.deleteLater()

    def test_cursor_up_down(self, qapp):
        td = self._make(qapp)
        td.feed("AAAA\n\x1b[1A")
        # after moving up one row, cursor y should be 0
        assert td._screen.cursor.y == 0
        td.deleteLater()

    def test_clear_screen(self, qapp):
        td = self._make(qapp)
        td.feed("Hello\x1b[2J\x1b[H")
        # screen cleared
        row = td._screen.buffer.get(0, {})
        text = "".join((row.get(c) and row[c].data or " ") for c in range(5))
        assert text.strip() == ""
        td.deleteLater()

    def test_clear_line(self, qapp):
        td = self._make(qapp)
        td.feed("Hello\x1b[2K\r")
        row = td._screen.buffer.get(0, {})
        text = "".join((row.get(c) and row[c].data or " ") for c in range(5))
        assert text.strip() == ""
        td.deleteLater()


class TestProtocolInvalid:
    def _make(self, qapp):
        td = TerminalDisplay()
        td.show()
        qapp.processEvents()
        return td

    def test_incomplete_escape_no_crash(self, qapp):
        td = self._make(qapp)
        td.feed("abc\x1b[")
        # should not crash; text present
        row = td._screen.buffer.get(0, {})
        text = "".join((row.get(c) and row[c].data or " ") for c in range(3))
        assert text == "abc"
        td.deleteLater()

    def test_invalid_sequence_no_crash(self, qapp):
        td = self._make(qapp)
        td.feed("abc\x1b[999zdef")
        row = td._screen.buffer.get(0, {})
        text = "".join((row.get(c) and row[c].data or " ") for c in range(6))
        assert "abc" in text
        td.deleteLater()
