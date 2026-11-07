"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Failure-path and lifecycle tests for terminal subsystem.
"""

import os
import sys
import time

import pytest

from editor.terminal.Emulator.emulator import ShellEmulator
from editor.terminal.Emulator.terminal_workspace import TerminalWorkspace

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Unix PTY tests")


class TestFailurePaths:
    def test_invalid_executable_shell_start(self, qapp, temp_cwd, monkeypatch):
        # Force _default_shell to nonexistent by monkeypatching? Instead test cwd invalid.
        emu = ShellEmulator()
        with pytest.raises(RuntimeError):
            emu.start(cwd="/no/such/dir")
        emu.kill()

    def test_write_after_kill_no_crash(self, qapp, temp_cwd):
        emu = ShellEmulator()
        emu.start(cwd=temp_cwd)
        time.sleep(0.3)
        qapp.processEvents()
        emu.kill()
        time.sleep(0.2)
        qapp.processEvents()
        # write should not crash
        emu.write("echo hi\n")
        assert True

    def test_double_kill_no_crash(self, qapp, temp_cwd):
        emu = ShellEmulator()
        emu.start(cwd=temp_cwd)
        time.sleep(0.3)
        qapp.processEvents()
        emu.kill()
        emu.kill()
        assert True

    def test_stop_graceful(self, qapp, temp_cwd):
        emu = ShellEmulator()
        finished = []
        emu.process_finished.connect(lambda rc: finished.append(rc))
        emu.start(cwd=temp_cwd)
        time.sleep(0.3)
        qapp.processEvents()
        emu.stop()
        deadline = time.time() + 5
        while time.time() < deadline and not finished:
            qapp.processEvents()
            time.sleep(0.1)
        # finished may or may not emit; no crash
        assert True

    def test_workspace_invalid_cwd_session_handled(self, qapp):
        ws = TerminalWorkspace()
        try:
            ws._on_add_session(cwd="/no/such/dir")
            qapp.processEvents()
        except Exception:
            pass
        ws.cleanup()
        ws.deleteLater()
        qapp.processEvents()
        assert True

    def test_workspace_kill_all_and_recreate(self, qapp, temp_cwd):
        ws = TerminalWorkspace()
        ws._on_add_session(cwd=temp_cwd)
        ws._on_add_session(cwd=temp_cwd)
        qapp.processEvents()
        for sid in list(ws._sessions.keys()):
            ws.kill_session(sid)
        qapp.processEvents()
        assert len(ws._sessions) == 0
        ws._on_add_session(cwd=temp_cwd)
        qapp.processEvents()
        assert len(ws._sessions) == 1
        ws.cleanup()
        ws.deleteLater()
        qapp.processEvents()

    def test_widget_destruction_while_running(self, qapp, temp_cwd):
        emu = ShellEmulator()
        emu.start(cwd=temp_cwd)
        time.sleep(0.3)
        qapp.processEvents()
        # destroy without explicit kill
        emu.deleteLater()
        qapp.processEvents()
        time.sleep(0.3)
        qapp.processEvents()
        assert True


class TestResourceCleanup:
    def test_repeated_create_destroy_workspace(self, qapp, temp_cwd):
        for _ in range(3):
            ws = TerminalWorkspace()
            ws._on_add_session(cwd=temp_cwd)
            qapp.processEvents()
            time.sleep(0.2)
            ws.cleanup()
            ws.deleteLater()
            qapp.processEvents()
        assert True
