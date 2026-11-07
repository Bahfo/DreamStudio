"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the PTY backend (editor/terminal/Emulator/emulator.py).
"""

import os
import sys
import threading
import time

import pytest

from editor.terminal.Emulator.emulator import UnixPty, WinPty, BasePty, _default_shell


pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Unix PTY tests")


class TestUnixPtySpawn:
    def test_spawn_shell_returns_pid(self, temp_cwd):
        pty = UnixPty()
        try:
            pid = pty.spawn(["/bin/sh", "-i"], temp_cwd, os.environ.copy(), rows=24, cols=80)
            assert isinstance(pid, int) and pid > 0
            assert pty.pid == pid
            assert pty.fd >= 0
        finally:
            pty.killpg()
            pty.close()

    def test_spawn_invalid_executable_raises(self, temp_cwd):
        pty = UnixPty()
        with pytest.raises(Exception):
            pty.spawn(["/no/such/binary"], temp_cwd, os.environ.copy())
        pty.close()

    def test_spawn_invalid_cwd_raises(self, temp_cwd):
        pty = UnixPty()
        with pytest.raises(Exception):
            pty.spawn(["/bin/sh", "-i"], "/no/such/dir", os.environ.copy())
        pty.close()

    def test_multiple_independent_ptys(self, temp_cwd):
        p1 = UnixPty()
        p2 = UnixPty()
        try:
            pid1 = p1.spawn(["/bin/sh", "-i"], temp_cwd, os.environ.copy())
            pid2 = p2.spawn(["/bin/sh", "-i"], temp_cwd, os.environ.copy())
            assert pid1 != pid2
            assert p1.fd != p2.fd
        finally:
            p1.killpg(); p1.close()
            p2.killpg(); p2.close()

    def test_read_write_roundtrip(self, temp_cwd):
        pty = UnixPty()
        try:
            pty.spawn(["/bin/sh", "-i"], temp_cwd, os.environ.copy())
            # send command
            pty.write(b"echo HELLO_PTY\n")
            buf = b""
            deadline = time.time() + 3
            while time.time() < deadline:
                import select
                r, _, _ = select.select([pty.fd], [], [], 0.2)
                if r:
                    try:
                        chunk = pty.read()
                    except OSError:
                        break
                    if not chunk:
                        break
                    buf += chunk
                    if b"HELLO_PTY" in buf:
                        break
            assert b"HELLO_PTY" in buf
        finally:
            pty.killpg(); pty.close()

    def test_setwinsize(self, temp_cwd):
        pty = UnixPty()
        try:
            pty.spawn(["/bin/sh", "-i"], temp_cwd, os.environ.copy())
            pty.setwinsize(40, 120)
            # verify via stty
            pty.write(b"stty size\n")
            buf = b""
            deadline = time.time() + 3
            while time.time() < deadline:
                import select
                r, _, _ = select.select([pty.fd], [], [], 0.2)
                if r:
                    try:
                        chunk = pty.read()
                    except OSError:
                        break
                    if not chunk:
                        break
                    buf += chunk
                    if b"40" in buf or b"120" in buf:
                        break
            assert b"40" in buf or b"120" in buf
        finally:
            pty.killpg(); pty.close()

    def test_poll_after_kill(self, temp_cwd):
        pty = UnixPty()
        try:
            pty.spawn(["/bin/sh", "-i"], temp_cwd, os.environ.copy())
            pty.killpg()
            time.sleep(0.3)
            rc = pty.poll()
            assert rc is not None
        finally:
            pty.close()

    def test_close_idempotent(self, temp_cwd):
        pty = UnixPty()
        pty.spawn(["/bin/sh", "-i"], temp_cwd, os.environ.copy())
        pty.killpg()
        pty.close()
        pty.close()  # should not raise
        assert pty.fd == -1

    def test_unicode_output(self, temp_cwd):
        pty = UnixPty()
        try:
            pty.spawn(["/bin/sh", "-i"], temp_cwd, os.environ.copy())
            pty.write("echo 'héllo 🎉'\n".encode())
            buf = b""
            deadline = time.time() + 3
            while time.time() < deadline:
                import select
                r, _, _ = select.select([pty.fd], [], [], 0.2)
                if r:
                    try:
                        chunk = pty.read()
                    except OSError:
                        break
                    if not chunk:
                        break
                    buf += chunk
                    if b"h\xc3\xa9llo" in buf:
                        break
            assert b"h\xc3\xa9llo" in buf
        finally:
            pty.killpg(); pty.close()
