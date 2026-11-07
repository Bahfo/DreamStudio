"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Stress tests for terminal subsystem.
"""

import os
import sys
import time

import pytest

from editor.terminal.Emulator.emulator import ShellEmulator


pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Unix PTY tests")


class TestTerminalStress:
    def test_repeated_session_create_destroy(self, qapp, temp_cwd):
        from editor.terminal.Emulator.terminal_workspace import TerminalWorkspace

        for _ in range(5):
            ws = TerminalWorkspace()
            ws._on_add_session(cwd=temp_cwd)
            qapp.processEvents()
            time.sleep(0.2)
            ws.cleanup()
            ws.deleteLater()
            qapp.processEvents()

    def test_continuous_output_no_crash(self, qapp, temp_cwd):
        emu = ShellEmulator()
        outputs = []
        emu.raw_output_received.connect(lambda t: outputs.append(t))
        emu.start(cwd=temp_cwd)
        time.sleep(0.3)
        qapp.processEvents()
        emu.write("for i in $(seq 1 200); do echo line$i; done\n")
        deadline = time.time() + 10
        while time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.1)
            if "".join(outputs).count("line") >= 200:
                break
        assert "".join(outputs).count("line") >= 190
        emu.kill()

    def test_repeated_resize(self, qapp, temp_cwd):
        emu = ShellEmulator()
        emu.start(cwd=temp_cwd)
        time.sleep(0.3)
        for i in range(20):
            emu.resize(10 + (i % 5), 40 + i)
            qapp.processEvents()
        emu.kill()
        assert True
