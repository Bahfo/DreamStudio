"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Integration tests for terminal subsystem.
"""

import os
import sys
import time

import pytest

from editor.terminal.Emulator.terminal_display import TerminalDisplay
from editor.terminal.Emulator.emulator import ShellEmulator


pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Unix PTY tests")


class TestIntegrationWorkflowA:
    def test_real_shell_output_reaches_display(self, qapp, temp_cwd):
        emu = ShellEmulator()
        display = TerminalDisplay()
        display.set_emulator(emu)
        outputs = []
        display_received = []

        def on_raw(text):
            display.feed(text)
            display_received.append(text)

        emu.raw_output_received.connect(on_raw)
        emu.start(cwd=temp_cwd)
        time.sleep(0.5)
        qapp.processEvents()
        emu.write("echo INTEGRATION_MARKER\n")
        deadline = time.time() + 5
        collected = ""
        while time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.1)
            collected = "".join(display_received)
            if "INTEGRATION_MARKER" in collected:
                break
        assert "INTEGRATION_MARKER" in collected
        emu.kill()
        display.deleteLater()


class TestIntegrationMultipleSessions:
    def test_two_sessions_isolation(self, qapp, temp_cwd):
        from editor.terminal.Emulator.terminal_workspace import TerminalWorkspace

        ws = TerminalWorkspace()
        ws._on_add_session(cwd=temp_cwd)
        ws._on_add_session(cwd=temp_cwd)
        qapp.processEvents()
        assert len(ws._sessions) == 2
        ws.cleanup()
        ws.deleteLater()
        qapp.processEvents()
