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
    def spawn(self, argv: list[str], cwd: str | None, env: dict,
              rows: int = 24, cols: int = 80) -> int:
        """Spawn a child process connected to the PTY. Returns pid.
        Accepts optional initial rows/cols so the PTY is born at the correct
        size, preventing a flash of incorrectly-wrapped text on startup."""

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

    def spawn(self, argv: list[str], cwd: str | None, env: dict,
              rows: int = 24, cols: int = 80) -> int:
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
        # Apply the requested initial dimensions immediately after the PTY
        # is created so the child shell sees the correct geometry from the
        # very first read, avoiding a one-frame size mismatch.
        try:
            self.setwinsize(rows, cols)
        except (OSError, ValueError):
            pass
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
        """Send *sig* to the child's process group.

        PermissionError is caught explicitly: certain child processes (e.g.
        those that call setuid/setgid or become session leaders) can cause
        os.killpg to fail with EPERM even though the process is alive.  In
        that case we fall back to a direct PID-level kill which the kernel
        permits for the parent process that owns the PTY.
        """
        if self._process is None:
            return
        try:
            pgid = os.getpgid(self._process.pid)
            if pgid != os.getpgid(0):
                os.killpg(pgid, sig)
            else:
                os.kill(self._process.pid, sig)
        except (ProcessLookupError, OSError, PermissionError):
            # PGID-based kill failed (permission denied, process already
            # gone, or we are not allowed to signal the group).  Attempt a
            # direct PID-level termination as a last resort.
            try:
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

    def spawn(self, argv: list[str], cwd: str | None, env: dict,
              rows: int = 24, cols: int = 80) -> int:
        """Spawn the child under Windows pywinpty.

        *rows* and *cols* are forwarded to PtyProcess.spawn so the PTY is
        created at the correct geometry instead of the old hard-coded
        80x24.  The caller should query the active display metrics and pass
        those values to avoid an initial mismatched-resize flash.
        """
        if platform.system() == "Windows":
            from pywinpty import PtyProcess

        self._proc = PtyProcess.spawn(
            argv[0],
            cwd=cwd,
            env=env,
            cols=cols,
            rows=rows,
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
    """Background reader that pulls data from a PTY fd and delivers it to
    the Qt event loop via queued signal connections.

    Thread-safety design
    --------------------
    The background thread emits ``raw_output_received`` and ``finished``
    directly.  Because the receiver lives in the main (GUI) thread, PyQt6
    automatically marshals these calls across threads using queued
    connections — no manual deque or QTimer polling is required.

    When ``stop()`` is called, the PTY master fd is closed immediately to
    unblock any pending ``select()`` or ``os.read()`` call.  The caller
    can then ``wait()`` on the thread with a timeout to guarantee it has
    exited *before* any QObject deletion (``deleteLater()``) runs,
    eliminating the race condition that previously caused segfaults.
    """

    raw_output_received = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, pty: BasePty, parent=None):
        super().__init__(parent)
        self._pty = pty
        self._running = True
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._thread = threading.Thread(
            target=self._run, name="pty_reader", daemon=True
        )

    def start(self):
        self._thread.start()

    def _run(self) -> None:
        """Entry point for the background reading thread.  Dispatches to
        the platform-specific loop and always emits *finished* at the end
        so the main thread can safely tear down."""
        if sys.platform == "win32":
            self._run_windows()
        else:
            self._run_unix()
        # PyQt will queue this signal to the main thread automatically
        # because PtyReader has main-thread affinity.
        self.finished.emit()

    def _run_unix(self) -> None:
        import select

        try:
            while self._running:
                # select() with a short timeout so we can periodically
                # check the _running flag even when no data arrives.
                r, _, _ = select.select([self._pty.fd], [], [], 0.15)
                if r:
                    try:
                        data = self._pty.read()
                    except OSError:
                        break
                    if not data:
                        break
                    decoded = self._decoder.decode(data)
                    if decoded:
                        self.raw_output_received.emit(decoded)
        except (OSError, ValueError):
            pass
        finally:
            # Always close the fd from the reader side when the read loop
            # exits — this is safe because close() is idempotent.
            self._pty.close()

    def _run_windows(self) -> None:
        try:
            while self._running:
                data = self._pty.read()
                if not data:
                    break
                decoded = self._decoder.decode(data)
                if decoded:
                    self.raw_output_received.emit(decoded)
        except Exception:
            pass
        finally:
            self._pty.close()

    def stop(self) -> None:
        """Signal the reader thread to stop and unblock any pending I/O.

        Closing the PTY fd forces any blocking ``select()`` / ``os.read()``
        to raise OSError, which breaks the read loop immediately rather
        than waiting for the 0.15 s select timeout to expire.
        """
        self._running = False
        try:
            self._pty.close()
        except Exception:
            pass

    def wait(self, timeout: float = 1.0) -> bool:
        """Block the calling (main) thread until the reader thread exits or
        *timeout* seconds elapse.  Returns ``True`` if the thread finished
        within the window, ``False`` otherwise.

        MUST be called before ``deleteLater()`` to prevent the event-loop
        from destroying the QObject while its thread is still alive —
        that race was the root cause of the original segfault.
        """
        self._thread.join(timeout=timeout)
        return not self._thread.is_alive()


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
        # Thread-safe accumulation buffer for high-throughput stream batching.
        # Protects against UI starvation when the child process emits millions
        # of lines per second (e.g. ``seq 1 5000000``).
        self._buf_lock = threading.Lock()
        self._buf: list[str] = []
        self._batch_timer = QTimer(self)
        self._batch_timer.setInterval(15)
        self._batch_timer.timeout.connect(self._drain_buffer)

    def start(self, cwd: str | None = None, rows: int = 24, cols: int = 80) -> None:
        """Spawn the shell and begin reading from its PTY.

        *rows* and *cols* are forwarded to the PTY backend so the child
        is born at the correct terminal geometry, eliminating the
        hard-coded 80x24 default that caused mismatched scaling on
        high-DPI or ultrawide displays.
        """
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

        self._pty.spawn(shell_args, cwd, env, rows=rows, cols=cols)
        self._running = True
        self.process_started.emit()

        self._reader = PtyReader(self._pty)
        # Direct connection — PyQt auto-queues cross-thread signals
        self._reader.raw_output_received.connect(self._on_raw_output)
        self._reader.finished.connect(self._on_reader_finished)
        self._reader.start()
        # Kick off the batch drain timer so accumulated output chunks are
        # flushed to the display at a steady ~60 FPS cadence.
        self._batch_timer.start()

    def _on_raw_output(self, text: str) -> None:
        """Receiver slot: accumulates raw PTY output under a lock instead of
        forwarding each chunk directly to the display.  This decouples the
        PTY reader's emission rate from the GUI repaint cycle, preventing
        UI starvation when the child process produces high-throughput output."""
        with self._buf_lock:
            self._buf.append(text)

    def _drain_buffer(self) -> None:
        """Timer callback on the main GUI thread: extracts all accumulated
        text blocks, joins them into a single consolidated string, and
        emits one signal per frame.  This preserves a responsive 50-60 FPS
        refresh rate even under millions of lines of streaming output."""
        with self._buf_lock:
            if not self._buf:
                return
            chunks = self._buf[:]
            self._buf.clear()
        merged = "".join(chunks)
        if merged:
            self.raw_output_received.emit(merged)

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
        """Graceful stop: SIGTERM the process group FIRST while the PTY
        master fd and PID are still valid, then close the fd, join the
        reader thread, and reap the child.  This ordering eliminates the
        ProcessLookupError that occurred when killpg was invoked after
        the shell leader died from an EOF on the closed master fd."""
        self._running = False
        # Stop the batch drain timer to prevent further signal emissions
        # during teardown.
        self._batch_timer.stop()
        # Signal the entire process group FIRST — the fd and pid are
        # still valid at this point so os.getpgid() will succeed.
        if self._pty is not None:
            try:
                self._pty.killpg(signal.SIGTERM)
            except Exception:
                pass
        # Stop the reader thread — this closes the PTY master fd,
        # unblocking any pending select()/os.read() in the read loop.
        if self._reader is not None:
            self._reader.stop()
            self._reader.wait(timeout=2.0)
        # Final drain of any buffered output still pending in the queue
        # so the user sees the last output before the process exits.
        self._drain_buffer()
        # Reap the child process state from the OS process table.
        if self._pty is not None:
            try:
                self._pty.poll()
            except Exception:
                pass

    def kill(self) -> None:
        """Brutal kill: SIGKILL the process group FIRST while the PTY
        master fd and PID are still valid, then close the fd and join
        the reader thread.  Same signal-first topology as stop() but
        using SIGKILL for immediate, non-ignorable termination."""
        self._running = False
        # Stop the batch drain timer to prevent further signal emissions
        # during teardown.
        self._batch_timer.stop()
        # SIGKILL the entire process group FIRST — descriptors are intact.
        if self._pty is not None:
            try:
                self._pty.killpg(signal.SIGKILL)
            except Exception:
                pass
        # Stop the reader thread (closes fd, unblocks pending I/O).
        if self._reader is not None:
            self._reader.stop()
            self._reader.wait(timeout=1.0)
        # Final drain of any buffered output.
        self._drain_buffer()
        # Reap the child process state.
        if self._pty is not None:
            try:
                self._pty.poll()
            except Exception:
                pass

    def _on_reader_finished(self) -> None:
        """Called on the main thread when the PtyReader's background thread
        exits.  Stops the batch drain timer, performs a final buffer drain,
        emits process_finished, then safely tears down the reader.

        Critical ordering: ``wait()`` MUST happen BEFORE ``deleteLater()``.
        The old code called deleteLater() while the reader's thread could
        still be alive on a blocking read, causing a segfault when the
        QObject was freed from under the running thread.
        """
        self._running = False
        self._batch_timer.stop()
        self._drain_buffer()
        rc = None
        if self._pty is not None:
            try:
                rc = self._pty.poll()
            except Exception:
                pass
        self.process_finished.emit(rc if rc is not None else -1)
        if self._reader is not None:
            # Guarantee the background thread has exited before we allow
            # the event loop to destroy the QObject.
            self._reader.wait(timeout=1.0)
            try:
                self._reader.deleteLater()
            except Exception:
                pass
            self._reader = None

    def is_running(self) -> bool:
        return self._running
