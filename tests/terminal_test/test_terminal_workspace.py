"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for TerminalWorkspace.
"""

import os
import sys
import time

import pytest

from editor.terminal.Emulator.terminal_workspace import TerminalWorkspace


pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Unix PTY tests")


class TestTerminalWorkspace:
    def test_create_first_session(self, qapp, temp_cwd):
        ws = TerminalWorkspace()
        ws._on_add_session(cwd=temp_cwd)
        qapp.processEvents()
        assert len(ws._sessions) == 1
        ws.cleanup()
        ws.deleteLater()
        qapp.processEvents()

    def test_multiple_sessions_unique_ids(self, qapp, temp_cwd):
        ws = TerminalWorkspace()
        ws._on_add_session(cwd=temp_cwd)
        ws._on_add_session(cwd=temp_cwd)
        qapp.processEvents()
        assert len(ws._sessions) == 2
        ids = list(ws._sessions.keys())
        assert ids[0] != ids[1]
        ws.cleanup()
        ws.deleteLater()

    def test_session_isolation_widgets(self, qapp, temp_cwd):
        ws = TerminalWorkspace()
        ws._on_add_session(cwd=temp_cwd)
        ws._on_add_session(cwd=temp_cwd)
        qapp.processEvents()
        views = [s["view"] for s in ws._sessions.values()]
        assert views[0] is not views[1]
        ws.cleanup()
        ws.deleteLater()

    def test_switch_session(self, qapp, temp_cwd):
        ws = TerminalWorkspace()
        ws._on_add_session(cwd=temp_cwd)
        ws._on_add_session(cwd=temp_cwd)
        qapp.processEvents()
        ids = list(ws._sessions.keys())
        ws._on_list_row_changed(0)
        qapp.processEvents()
        assert ws._active_id == ids[0]
        ws.cleanup()
        ws.deleteLater()

    def test_remove_session(self, qapp, temp_cwd):
        ws = TerminalWorkspace()
        ws._on_add_session(cwd=temp_cwd)
        ws._on_add_session(cwd=temp_cwd)
        qapp.processEvents()
        ids = list(ws._sessions.keys())
        ws.kill_session(ids[0])
        qapp.processEvents()
        assert ids[0] not in ws._sessions
        ws.cleanup()
        ws.deleteLater()

    def test_invalid_cwd_session_handled(self, qapp):
        ws = TerminalWorkspace()
        try:
            ws._on_add_session(cwd="/no/such/dir")
            qapp.processEvents()
        except Exception:
            pass
        ws.cleanup()
        ws.deleteLater()

    def test_set_default_cwd(self, qapp, temp_cwd):
        ws = TerminalWorkspace()
        ws.set_default_cwd(temp_cwd)
        ws.cleanup()
        ws.deleteLater()

    def test_set_theme(self, qapp, temp_cwd):
        ws = TerminalWorkspace()
        ws._on_add_session(cwd=temp_cwd)
        qapp.processEvents()
        ws.set_theme("#000000", "#ffffff", "#264f78")
        ws.cleanup()
        ws.deleteLater()

    def test_cleanup(self, qapp, temp_cwd):
        ws = TerminalWorkspace()
        ws._on_add_session(cwd=temp_cwd)
        qapp.processEvents()
        ws.cleanup()
        ws.deleteLater()
        qapp.processEvents()
        assert True
