"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for TerminalDisplay.
"""

import time

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from editor.terminal.Emulator.terminal_display import TerminalDisplay


class TestTerminalDisplayBasic:
    def test_instantiation(self, qapp):
        td = TerminalDisplay()
        assert td is not None
        td.deleteLater()
        qapp.processEvents()

    def test_feed_text_updates_screen(self, qapp):
        td = TerminalDisplay()
        td.show()
        qapp.processEvents()
        td.feed("Hello")
        screen = td._screen
        # screen display contains Hello
        row = screen.display[0]
        assert "H" in "".join(row)
        td.deleteLater()

    def test_feed_newline(self, qapp):
        td = TerminalDisplay()
        td.show()
        qapp.processEvents()
        td.feed("A\nB")
        screen = td._screen
        assert "A" in "".join(screen.display[0])
        assert "B" in "".join(screen.display[1])
        td.deleteLater()

    def test_resize(self, qapp):
        td = TerminalDisplay()
        td.resized.emit if False else None
        td._apply_resize() if False else None
        # trigger resize via widget resize
        td.resize(400, 200)
        qapp.processEvents()
        td.deleteLater()

    def test_clear_reset(self, qapp):
        td = TerminalDisplay()
        td.show()
        qapp.processEvents()
        td.feed("Hello")
        td.reset()
        screen = td._screen
        assert "H" not in "".join(screen.display[0])
        td.deleteLater()

    def test_cursor_position_after_text(self, qapp):
        td = TerminalDisplay()
        td.show()
        qapp.processEvents()
        td.feed("abc")
        assert td._screen.cursor.x == 3
        td.deleteLater()
