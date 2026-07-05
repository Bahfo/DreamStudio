"""
(C) COPYRIGHT 2026 EXcellent TechStacks
Terminal Emulator Logic for DreamStudio.
"""

import os
import sys
import codecs
import signal
import platform
import subprocess
import threading

from abc import ABC, abstractmethod
from collections import deque
from PyQt6.QtCore import pyqtSignal, QObject, QTimer

try:
    import pty

    _HAVE_PTY = True
except ImportError:
    _HAVE_PTY = False


class BasePty(ABC):
    """Abstract pseudo-terminal backend. Implementations: UnixPty, WinPty."""

    @abstractmethod
    def spawn(self, argv: list[str], cwd: str | None, env: dict) -> int:
        """Spawn a child process connected to the PTY. Returns pid."""

    @abstractmethod
    def read(self, size: int = 65536) -> bytes:
        """Read from PTY master. May raise OSError if fd was closed."""

    @abstractmethod
    def write(self, data: bytes) -> int:
        """Write to PTY master."""

    @abstractmethod
    def setwinsize(self, rows: int, cols: int) -> None:
        """Inform the kernel of new terminal dimensions."""

    @abstractmethod
    def close(self) -> None:
        """Close the PTY master fd only (idempotent). Does NOT kill child."""

    @abstractmethod
    def killpg(self, sig: int = signal.SIGKILL) -> None:
        """Send a signal to the child's process group."""

    @abstractmethod
    def poll(self) -> int | None:
        """Non-blocking: return child returncode or None if still alive."""

    @property
    @abstractmethod
    def fd(self) -> int:
        """PTY master file descriptor. -1 if closed."""

    @property
    @abstractmethod
    def pid(self) -> int:
        """Child process pid. -1 if not spawned."""


class UnixPty(BasePty):
    def __init__(self):
        self._master_fd = -1
        self._process: subprocess.Popen | None = None

    def spawn(self, argv: list[str], cwd: str | None, env: dict) -> int:
        master_fd, slave_fd = pty.openpty()
        self._master_fd = master_fd
        self._process = subprocess.Popen(
            argv,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            env=env,
            close_fds=True,
            preexec_fn=os.setsid,
        )
        os.close(slave_fd)
        return self._process.pid

    def read(self, size: int = 65536) -> bytes:
        return os.read(self._master_fd, size)

    def write(self, data: bytes) -> int:
        return os.write(self._master_fd, data)

    def setwinsize(self, rows: int, cols: int) -> None:
        import struct
        import fcntl
        import termios

        size = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, size)

    def close(self) -> None:
        if self._master_fd >= 0:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = -1

    def killpg(self, sig: int = signal.SIGKILL) -> None:
        if self._process is None:
            return
        try:
            pgid = os.getpgid(self._process.pid)
            if pgid != os.getpgid(0):
                os.killpg(pgid, sig)
            else:
                os.kill(self._process.pid, sig)
        except (ProcessLookupError, OSError):
            pass

    def poll(self) -> int | None:
        return self._process.poll() if self._process else None

    @property
    def fd(self) -> int:
        return self._master_fd

    @property
    def pid(self) -> int:
        return self._process.pid if self._process else -1


class WinPty(BasePty):
    """
    Windows specific emulator behavior (Using BasePty)
    """

    def __init__(self):
        self._proc = None

    # Window specific code. Will not run if platform is not Windows
    def spawn(self, argv: list[str], cwd: str | None, env: dict) -> int:
        if platform.system() == "Windows":
            from pywinpty import PtyProcess

        self._proc = PtyProcess.spawn(
            argv[0],
            cwd=cwd,
            env=env,
            cols=80,
            rows=24,
        )
        return self._proc.pid

    def read(self, size: int = 65536) -> bytes:
        return self._proc.read(size)

    def write(self, data: bytes) -> int:
        text = data.decode("utf-8", errors="replace")
        self._proc.write(text)
        return len(data)

    def setwinsize(self, rows: int, cols: int) -> None:
        self._proc.setwinsize(rows, cols)

    def close(self) -> None:
        if self._proc is not None:
            try:
                self._proc.close()
            except OSError:
                pass
            self._proc = None

    def killpg(self, sig: int = signal.SIGKILL) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
            except OSError:
                pass

    def poll(self) -> int | None:
        return None

    @property
    def fd(self) -> int:
        return getattr(self._proc, "fd", -1) if self._proc else -1

    @property
    def pid(self) -> int:
        return self._proc.pid if self._proc else -1


class PtyReader(QObject):
    raw_output_received = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, pty: BasePty, parent=None):
        super().__init__(parent)
        self._pty = pty
        self._running = True
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._events: deque = deque()
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_events)
        self._thread = threading.Thread(
            target=self._run, name="pty_reader", daemon=True
        )

    def start(self):
        self._poll_timer.start(50)
        self._thread.start()

    def _poll_events(self):
        while True:
            try:
                kind, data = self._events.popleft()
            except IndexError:
                break
            if kind == "data":
                self.raw_output_received.emit(data)
            elif kind == "done":
                self._poll_timer.stop()
                self.finished.emit()
                return

    def _run(self) -> None:
        if sys.platform == "win32":
            self._run_windows()
        else:
            self._run_unix()
        self._events.append(("done", None))

    def _run_unix(self) -> None:
        import select

        try:
            while self._running:
                r, _, _ = select.select([self._pty.fd], [], [], 0.15)
                if r:
                    try:
                        data = self._pty.read()
                    except OSError:
                        break
                    if not data:
                        break
                    self._emit_data(data)
        except (OSError, ValueError):
            pass
        finally:
            self._pty.close()

    def _run_windows(self) -> None:
        try:
            while self._running:
                data = self._pty.read()
                if not data:
                    break
                self._emit_data(data)
        except Exception:
            pass
        finally:
            self._pty.close()

    def _emit_data(self, data: bytes) -> None:
        decoded = self._decoder.decode(data)
        if decoded:
            self._events.append(("data", decoded))

    def stop(self) -> None:
        self._running = False


class ShellEmulator(QObject):
    raw_output_received = pyqtSignal(str)
    process_started = pyqtSignal()
    process_finished = pyqtSignal(int)
    process_errored = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pty: BasePty | None = None
        self._reader: PtyReader | None = None
        self._running = False

    def start(self, cwd: str | None = None) -> None:
        if sys.platform == "win32":
            self._pty = WinPty()
        else:
            self._pty = UnixPty()

        shell = os.environ.get("SHELL", "/bin/bash")
        if "zsh" in shell:
            shell_args = [shell, "-i", "+Z", "+zle"]
        else:
            shell_args = [shell, "-i"]

        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        if cwd:
            env["PWD"] = cwd

        self._pty.spawn(shell_args, cwd, env)
        self._running = True
        self.process_started.emit()

        self._reader = PtyReader(self._pty)
        self._reader.raw_output_received.connect(self.raw_output_received.emit)
        self._reader.finished.connect(self._on_reader_finished)
        self._reader.start()

    def write(self, text: str) -> None:
        if self._pty is not None and self._running:
            try:
                self._pty.write(text.encode("utf-8"))
            except OSError:
                pass

    def resize(self, rows: int, cols: int) -> None:
        if self._pty is not None and self._running:
            try:
                self._pty.setwinsize(rows, cols)
            except (OSError, ValueError):
                pass

    def stop(self) -> None:
        """Graceful stop: close fd, send SIGTERM, do not block."""
        self._running = False
        if self._reader is not None:
            self._reader.stop()
        if self._pty is not None:
            try:
                self._pty.close()
            except Exception:
                pass
            try:
                self._pty.killpg(signal.SIGTERM)
            except Exception:
                pass

    def kill(self) -> None:
        """Brutal kill: close fd first to unblock reader, then SIGKILL."""
        self._running = False
        if self._reader is not None:
            self._reader.stop()
        if self._pty is not None:
            try:
                self._pty.close()
            except Exception:
                pass
            try:
                self._pty.killpg(signal.SIGKILL)
            except Exception:
                pass

    def _on_reader_finished(self) -> None:
        self._running = False
        rc = None
        if self._pty is not None:
            try:
                rc = self._pty.poll()
            except Exception:
                pass
        self.process_finished.emit(rc if rc is not None else -1)
        if self._reader is not None:
            try:
                self._reader._poll_timer.stop()
                self._reader.deleteLater()
            except Exception:
                pass
            self._reader = None

    def is_running(self) -> bool:
        return self._running
