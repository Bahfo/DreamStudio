"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Tests for terminal API.
"""

import sys

import pytest

from editor.terminal import api


class TestTerminalAPI:
    def test_public_symbols(self):
        assert "TerminalPanel" in api.__all__
        assert "TAB_SYSTEM_SHELL" in api.__all__

    def test_imports(self):
        from editor.terminal.Emulator.terminal_ui import TerminalPanel

        assert TerminalPanel is api.TerminalPanel
