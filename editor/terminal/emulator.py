import codecs
import os
import sys
import re
import select
import signal
import subprocess
import threading

from PyQt6.QtCore import QThread, pyqtSignal, QObject

try:
    import pty
    _HAVE_PTY = True
except ImportError:
    _HAVE_PTY = False


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\][0-9;]*[^\x1b]*\x1b\\|\x1b[\\\]_].*?\x1b\\|\x1b[N-Z]|[\x00-\x08\x0e-\x1f]")


def strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


def _clean_output(text: str) -> str:
    text = strip_ansi(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


class PtyReader(QThread):
    output_received = pyqtSignal(str)
    raw_output_received = pyqtSignal(str)

    def __init__(self, fd: int, pid: int, parent=None):
        super().__init__(parent)
        self._fd = fd
        self._pid = pid
        self._running = True
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")

    def run(self) -> None:
        try:
            while self._running:
                r, _, _ = select.select([self._fd], [], [], 0.15)
                if r:
                    try:
                        data = os.read(self._fd, 65536)
                    except OSError:
                        break
                    if not data:
                        break
                    decoded = self._decoder.decode(data)
                    if decoded:
                        self.raw_output_received.emit(decoded)
                    text = _clean_output(decoded)
                    if text:
                        self.output_received.emit(text)
        except (OSError, ValueError):
            pass
        finally:
            try:
                os.close(self._fd)
            except OSError:
                pass
            try:
                os.waitpid(self._pid, 0)
            except ChildProcessError:
                pass

    def stop(self) -> None:
        self._running = False


class PipeReader(QThread):
    output_received = pyqtSignal(str)
    raw_output_received = pyqtSignal(str)
    error_received = pyqtSignal(str)

    def __init__(self, process: subprocess.Popen, parent=None):
        super().__init__(parent)
        self._process = process
        self._running = True
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")

    def run(self) -> None:
        try:
            while self._running:
                data = self._process.stdout.read(65536)
                if not data:
                    break
                if isinstance(data, bytes):
                    decoded = self._decoder.decode(data)
                else:
                    decoded = data
                if decoded:
                    self.raw_output_received.emit(decoded)
                    cleaned = _clean_output(decoded)
                    if cleaned:
                        self.output_received.emit(cleaned)
        except (OSError, ValueError):
            pass
        finally:
            self._drain_stderr()
            self._process.wait()

    def _drain_stderr(self):
        try:
            remaining = self._process.stderr.read()
            if remaining:
                if isinstance(remaining, bytes):
                    remaining = remaining.decode("utf-8", errors="replace")
                cleaned = _clean_output(remaining)
                if cleaned:
                    self.error_received.emit(cleaned)
        except (OSError, ValueError):
            pass

    def stop(self) -> None:
        self._running = False


class StderrReader(QThread):
    error_received = pyqtSignal(str)

    def __init__(self, pipe, parent=None):
        super().__init__(parent)
        self._pipe = pipe
        self._running = True
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")

    def run(self) -> None:
        try:
            while self._running:
                data = self._pipe.read(65536)
                if not data:
                    break
                if isinstance(data, bytes):
                    decoded = self._decoder.decode(data)
                else:
                    decoded = data
                if decoded:
                    cleaned = _clean_output(decoded)
                    if cleaned:
                        self.error_received.emit(cleaned)
        except (OSError, ValueError):
            pass

    def stop(self) -> None:
        self._running = False


class ShellEmulator(QObject):
    output_received = pyqtSignal(str)
    raw_output_received = pyqtSignal(str)
    process_started = pyqtSignal()
    process_finished = pyqtSignal(int)
    process_errored = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._master_fd: int | None = None
        self._process: subprocess.Popen | None = None
        self._reader: PtyReader | PipeReader | None = None
        self._stderr_reader: StderrReader | None = None
        self._running = False

    def start(self, cwd: str | None = None) -> None:
        if sys.platform == "win32":
            self._start_windows(cwd)
        else:
            self._start_unix(cwd)

    def _start_unix(self, cwd: str | None = None) -> None:
        shell = os.environ.get("SHELL", "/bin/bash")
        if "zsh" in shell:
            shell_args = [shell, "-i", "+Z", "+zle"]
        else:
            shell_args = [shell, "-i"]

        master_fd, slave_fd = pty.openpty()
        self._master_fd = master_fd

        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        if cwd:
            env["PWD"] = cwd

        self._process = subprocess.Popen(
            shell_args,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            env=env,
            close_fds=True,
            preexec_fn=os.setsid,
        )
        os.close(slave_fd)

        self._running = True
        self.process_started.emit()

        self._reader = PtyReader(master_fd, self._process.pid)
        self._reader.output_received.connect(self.output_received.emit)
        self._reader.raw_output_received.connect(self.raw_output_received.emit)
        self._reader.finished.connect(self._on_reader_finished)
        self._reader.start()

    def _start_windows(self, cwd: str | None = None) -> None:
        self._process = subprocess.Popen(
            ["powershell.exe"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
        )
        self._running = True
        self.process_started.emit()

        self._reader = PipeReader(self._process)
        self._reader.output_received.connect(self.output_received.emit)
        self._reader.raw_output_received.connect(self.raw_output_received.emit)
        self._reader.finished.connect(self._on_reader_finished)
        self._reader.start()

        self._stderr_reader = StderrReader(self._process.stderr)
        self._stderr_reader.error_received.connect(self._on_windows_stderr)
        self._stderr_reader.start()

    def _on_windows_stderr(self, text: str) -> None:
        self.raw_output_received.emit(text)

    def write(self, text: str) -> None:
        if sys.platform == "win32":
            self._write_windows(text)
        else:
            self._write_unix(text)

    def _write_unix(self, text: str) -> None:
        if self._master_fd is not None and self._running:
            try:
                os.write(self._master_fd, text.encode("utf-8"))
            except OSError:
                pass

    def _write_windows(self, text: str) -> None:
        if self._process and self._process.stdin and not self._process.stdin.closed:
            try:
                self._process.stdin.write(text.encode("utf-8"))
                self._process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

    def resize(self, rows: int, cols: int) -> None:
        if self._master_fd is None:
            return
        try:
            import fcntl
            import termios
            import struct

            size = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, size)
        except (ImportError, OSError):
            pass

    def stop(self) -> None:
        self._running = False
        if self._reader:
            self._reader.stop()
        if self._process:
            self._terminate_process()
        if self._reader:
            self._reader.wait(3000)
        if self._stderr_reader:
            self._stderr_reader.stop()
            self._stderr_reader.wait(1000)

    def _terminate_process(self) -> None:
        try:
            pgid = os.getpgid(self._process.pid)
            if pgid != os.getpgid(0):
                os.killpg(pgid, signal.SIGTERM)
            else:
                self._process.terminate()
        except (ProcessLookupError, OSError):
            self._process.terminate()
        try:
            self._process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                pgid = os.getpgid(self._process.pid)
                if pgid != os.getpgid(0):
                    os.killpg(pgid, signal.SIGKILL)
                else:
                    self._process.kill()
            except (ProcessLookupError, OSError):
                self._process.kill()
            self._process.wait(timeout=2)

    def _on_reader_finished(self) -> None:
        self._running = False
        returncode = self._process.poll() if self._process else -1
        self.process_finished.emit(returncode if returncode is not None else -1)

    def is_running(self) -> bool:
        return self._running
