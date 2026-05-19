import os
import sys
import signal
import logging
import subprocess

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class ProcessRunner(QThread):
    output_received = pyqtSignal(str)
    error_received = pyqtSignal(str)
    process_finished = pyqtSignal(int, str)
    process_started = pyqtSignal(int)
    process_errored = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = None
        self._cmd = None
        self._cwd = None
        self._env = None
        self._running = False
        self._timeout_ms = 0

    def configure(self, cmd, cwd=None, env=None, timeout_ms=0):
        self._cmd = cmd
        self._cwd = cwd or os.getcwd()
        self._env = env
        self._timeout_ms = timeout_ms

    def run(self):
        if not self._cmd:
            self.process_errored.emit("No command configured")
            return

        try:
            env = self._env or os.environ.copy()
            env.setdefault("PYTHONUNBUFFERED", "1")

            self._process = subprocess.Popen(
                self._cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                cwd=self._cwd,
                env=env,
                text=True,
                bufsize=1,
            )

            self._running = True
            self.process_started.emit(self._process.pid)

            import select
            import time

            start_time = time.monotonic()
            timed_out = False

            stdout_fd = self._process.stdout.fileno()
            stderr_fd = self._process.stderr.fileno()

            while self._running:
                if self._timeout_ms > 0:
                    elapsed = (time.monotonic() - start_time) * 1000
                    if elapsed > self._timeout_ms:
                        timed_out = True
                        break

                reads, _, _ = select.select(
                    [stdout_fd, stderr_fd], [], [], 0.05
                )

                for fd in reads:
                    if fd == stdout_fd:
                        line = self._process.stdout.readline()
                        if line:
                            self.output_received.emit(line)
                    elif fd == stderr_fd:
                        line = self._process.stderr.readline()
                        if line:
                            self.error_received.emit(line)

                if self._process.poll() is not None:
                    for line in self._process.stdout:
                        self.output_received.emit(line)
                    for line in self._process.stderr:
                        self.error_received.emit(line)
                    break

            if timed_out:
                self._kill_process()
                self.process_finished.emit(-1, "TIMEOUT")
                return

            if not self._running:
                self._kill_process()
                self.process_finished.emit(-1, "CANCELLED")
                return

            returncode = self._process.wait()
            self.process_finished.emit(returncode, "")

        except FileNotFoundError as e:
            self.process_errored.emit(f"Command not found: {e}")
        except PermissionError as e:
            self.process_errored.emit(f"Permission denied: {e}")
        except OSError as e:
            self.process_errored.emit(f"OS error: {e}")
        except Exception as e:
            self.process_errored.emit(f"Unexpected error: {e}")
        finally:
            self._running = False
            self._process = None

    def write_stdin(self, text):
        proc = self._process
        if proc and proc.stdin and not proc.stdin.closed:
            try:
                proc.stdin.write(text)
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

    def stop(self):
        self._running = False
        self._kill_process()

    def _kill_process(self):
        proc = self._process
        if proc is None:
            return
        try:
            if sys.platform == "win32":
                proc.terminate()
            else:
                try:
                    pgid = os.getpgid(proc.pid)
                    if pgid != os.getpgid(0):
                        os.killpg(pgid, signal.SIGTERM)
                    else:
                        proc.terminate()
                except ProcessLookupError:
                    proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    pgid = os.getpgid(proc.pid)
                    if pgid != os.getpgid(0):
                        os.killpg(pgid, signal.SIGKILL)
                    else:
                        proc.kill()
                except (ProcessLookupError, OSError):
                    proc.kill()
                proc.wait(timeout=2)
        except (ProcessLookupError, OSError):
            pass

    def is_running(self):
        return self._running and self._process is not None


class PythonRunner(ProcessRunner):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._interpreter = None
        self._venv_path = None

    def set_interpreter(self, interpreter_path):
        self._interpreter = interpreter_path

    def find_interpreter(self, project_path=None):
        candidates = []

        if project_path:
            venv_candidates = [
                os.path.join(project_path, ".venv", "bin", "python3"),
                os.path.join(project_path, ".venv", "bin", "python"),
                os.path.join(project_path, "venv", "bin", "python3"),
                os.path.join(project_path, "venv", "bin", "python"),
                os.path.join(project_path, ".venv", "Scripts", "python.exe"),
                os.path.join(project_path, "venv", "Scripts", "python.exe"),
            ]
            for c in venv_candidates:
                if os.path.isfile(c):
                    self._venv_path = os.path.dirname(os.path.dirname(c))
                    candidates.append(c)

        candidates.append(sys.executable)

        for c in candidates:
            if os.path.isfile(c):
                self._interpreter = c
                return c

        return None

    def run_file(self, file_path, args=None):
        interpreter = self._interpreter or self.find_interpreter(os.path.dirname(file_path))
        if not interpreter:
            self.process_errored.emit("No Python interpreter found")
            return

        cmd = [interpreter, file_path]
        if args:
            cmd.extend(args)

        self.configure(cmd=cmd, cwd=os.path.dirname(file_path))
        self.start()

    def run_code(self, code, cwd=None):
        interpreter = self._interpreter or self.find_interpreter(cwd)
        if not interpreter:
            interpreter = sys.executable

        cmd = [interpreter, "-c", code]
        self.configure(cmd=cmd, cwd=cwd or os.getcwd())
        self.start()

    def run_module(self, module_name, args=None, cwd=None):
        interpreter = self._interpreter or self.find_interpreter(cwd)
        if not interpreter:
            self.process_errored.emit("No Python interpreter found")
            return

        cmd = [interpreter, "-m", module_name]
        if args:
            cmd.extend(args)

        self.configure(cmd=cmd, cwd=cwd or os.getcwd())
        self.start()
