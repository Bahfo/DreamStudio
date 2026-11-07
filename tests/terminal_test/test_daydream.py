"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for DayDream.
"""

import sys

import pytest

from editor.terminal.DayDream.daydream import main_terminal


class TestDayDream:
    def test_main_terminal_callable(self, qapp):
        # main_terminal launches a separate Tk window; just ensure importable
        assert callable(main_terminal)
