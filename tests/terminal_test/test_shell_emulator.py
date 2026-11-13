"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Tests for ShellEmulator lifecycle.
"""

import os
import sys
import time

import pytest
from PyQt6.QtCore import Qt

from editor.terminal.Emulator.emulator import ShellEmulator

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Unix PTY tests")


class TestShellEmulatorLifecycle:
    def test_start_emits_process_started(self, qapp, temp_cwd):
        emu = ShellEmulator()
        received = []
        emu.process_started.connect(lambda: received.append(True))
        emu.start(cwd=temp_cwd)
        # process events
        deadline = time.time() + 3
        while time.time() < deadline and not received:
            qapp.processEvents()
            time.sleep(0.05)
        assert received, "process_started not emitted"
        emu.kill()

    def test_invalid_cwd_raises(self, qapp, temp_cwd):
        emu = ShellEmulator()
        with pytest.raises(RuntimeError):
            emu.start(cwd="/no/such/dir")
        emu.kill()

    def test_output_delivered(self, qapp, temp_cwd):
        emu = ShellEmulator()
        outputs = []
        emu.raw_output_received.connect(lambda t: outputs.append(t))
        emu.start(cwd=temp_cwd)
        # wait for prompt
        time.sleep(0.5)
        qapp.processEvents()
        emu.write("echo MARKER_OUTPUT_123\n")
        deadline = time.time() + 5
        collected = ""
        while time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.1)
            collected = "".join(outputs)
            if "MARKER_OUTPUT_123" in collected:
                break
        assert "MARKER_OUTPUT_123" in collected
        emu.kill()

    def test_exit_status_reported(self, qapp, temp_cwd):
        emu = ShellEmulator()
        finished = []
        emu.process_finished.connect(lambda rc: finished.append(rc))
        emu.start(cwd=temp_cwd)
        time.sleep(0.5)
        qapp.processEvents()
        emu.write("exit\n")
        deadline = time.time() + 5
        while time.time() < deadline and not finished:
            qapp.processEvents()
            time.sleep(0.1)
        assert finished, "process_finished not emitted"

    def test_resize_no_crash(self, qapp, temp_cwd):
        emu = ShellEmulator()
        emu.start(cwd=temp_cwd)
        time.sleep(0.3)
        emu.resize(40, 120)
        emu.resize(10, 40)
        qapp.processEvents()
        emu.kill()

    def test_repeated_start_stop(self, qapp, temp_cwd):
        emu = ShellEmulator()
        for _ in range(3):
            emu.start(cwd=temp_cwd)
            time.sleep(0.2)
            qapp.processEvents()
            emu.kill()
            time.sleep(0.2)
            qapp.processEvents()
        assert True

    def test_env_not_polluted_parent(self, qapp, temp_cwd):
        import os as _os

        before = _os.environ.get("TERM")
        emu = ShellEmulator()
        emu.start(cwd=temp_cwd)
        time.sleep(0.3)
        # child env set TERM but parent should be unchanged (we didn't modify)
        assert _os.environ.get("TERM") == before
        emu.kill()

    def test_prevent_duplicate_reader(self, qapp, temp_cwd):
        emu = ShellEmulator()
        emu.start(cwd=temp_cwd)
        # calling start again should kill and restart, not duplicate
        emu.start(cwd=temp_cwd)
        time.sleep(0.3)
        qapp.processEvents()
        emu.kill()
        assert True

    def test_large_output(self, qapp, temp_cwd):
        emu = ShellEmulator()
        outputs = []
        emu.raw_output_received.connect(lambda t: outputs.append(t))
        emu.start(cwd=temp_cwd)
        time.sleep(0.5)
        qapp.processEvents()
        emu.write("python3 -c \"print('A'*100000)\"\n")
        deadline = time.time() + 10
        collected = ""
        while time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.1)
            collected = "".join(outputs)
            if collected.count("A") >= 100000:
                break
        assert collected.count("A") >= 100000
        emu.kill()

    def test_unicode_output(self, qapp, temp_cwd):
        emu = ShellEmulator()
        outputs = []
        emu.raw_output_received.connect(lambda t: outputs.append(t))
        emu.start(cwd=temp_cwd)
        time.sleep(0.5)
        qapp.processEvents()
        emu.write("printf 'héllo 🎉\\n'\n")
        deadline = time.time() + 5
        collected = ""
        while time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.1)
            collected = "".join(outputs)
            if "héllo" in collected:
                break
        assert "héllo" in collected
        emu.kill()
