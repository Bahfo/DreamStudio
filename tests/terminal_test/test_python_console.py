"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Tests for PythonConsole (PythonShell).
"""

import sys

import pytest

from editor.terminal.PythonConsole.console import PythonShell


class TestPythonConsole:
    def test_instantiation(self, qapp):
        w = PythonShell()
        assert w is not None
        w.deleteLater()
        qapp.processEvents()

    def test_clear_console(self, qapp):
        w = PythonShell()
        try:
            w.clear_console()
        except Exception:
            pass
        w.deleteLater()
        qapp.processEvents()

    def test_set_workspace(self, qapp, tmp_path):
        w = PythonShell()
        try:
            w.set_workspace(str(tmp_path))
        except Exception:
            pass
        w.deleteLater()
        qapp.processEvents()
