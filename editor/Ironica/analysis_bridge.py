"""Parent-side client for the out-of-process analysis server."""

from __future__ import annotations

import itertools
import select
import tempfile
import time

from editor import *

from editor.analysis.wire import (
    SPILL_DIR_NAME as _SPILL_DIR_NAME,
    discard_spills as _wire_discard,
    resolve_spills as _wire_resolve,
    spill_large_strings as _wire_spill,
)

logger = logging.getLogger(__name__)

_FRAME_HEADER = struct.Struct("<Q")
_PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL

_SPILL_THRESHOLD_BYTES = 1_000_000
_MAX_FRAME_BYTES = 20_000_000
_REQUEST_TIMEOUT_S = 15.0
_spill_counter = itertools.count()
_spill_lock = threading.Lock()


class AnalysisProcessError(RuntimeError):
    """Raised when the analysis subprocess dies or the wire protocol breaks."""


def _read_exact(stream, n: int, deadline: Optional[float] = None) -> bytes:
    """Read exactly *n* bytes from *stream* or raise ``AnalysisProcessError``."""
    if n <= 0:
        raise AnalysisProcessError(f"invalid frame read length: {n}")
    chunks: list = []
    remaining = n
    fileno = None
    if deadline is not None:
        try:
            fileno = stream.fileno()
        except Exception:
            fileno = None
    while remaining > 0:
        if deadline is not None:
            if fileno is not None:
                # NOTE: checking the clock *between* reads is not enough —
                remaining_time = deadline - time.monotonic()
                if remaining_time <= 0:
                    raise AnalysisProcessError(
                        "analysis subprocess response timed out"
                    )
                try:
                    ready, _, _ = select.select([fileno], [], [], remaining_time)
                except (OSError, ValueError):
                    ready = [fileno]
                if not ready:
                    raise AnalysisProcessError(
                        "analysis subprocess response timed out"
                    )
            elif time.monotonic() >= deadline:
                raise AnalysisProcessError("analysis subprocess response timed out")
        chunk = stream.read(remaining)
        if not chunk:
            raise AnalysisProcessError("analysis subprocess closed its output stream")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(stream, deadline: Optional[float] = None) -> object:
    """Read one length-prefixed pickle frame from *stream*."""
    header = _read_exact(stream, _FRAME_HEADER.size, deadline)
    (size,) = _FRAME_HEADER.unpack(header)
    if size > _MAX_FRAME_BYTES:
        raise AnalysisProcessError(f"analysis frame too large: {size} bytes")
    if size == 0:
        raise AnalysisProcessError("empty analysis frame")
    data = _read_exact(stream, size, deadline)
    return pickle.loads(data)


def write_frame(stream, payload) -> None:
    """Write one length-prefixed pickle frame to *stream*."""
    data = pickle.dumps(payload, protocol=_PICKLE_PROTOCOL)
    stream.write(_FRAME_HEADER.pack(len(data)))
    stream.write(data)
    stream.flush()


def _spill_dir() -> str:
    """Return the temp directory for spilled sources, creating it."""
    path = os.path.join(tempfile.gettempdir(), _SPILL_DIR_NAME)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


def _cleanup_stale_spills(max_age_s: float = 3600.0) -> None:
    """Delete spilled sources older than *max_age_s* (best effort)."""
    try:
        now = time.time()
        for name in os.listdir(_spill_dir()):
            full = os.path.join(_spill_dir(), name)
            try:
                if now - os.path.getmtime(full) > max_age_s:
                    os.unlink(full)
            except OSError:
                pass
    except OSError:
        pass


def spill_large_strings(payload):
    """Delegate to shared wire helper (kept for backward compat)."""
    return _wire_spill(payload)


def resolve_spills(payload):
    """Delegate to shared wire helper, mapping errors compatibly."""
    try:
        return _wire_resolve(payload)
    except Exception as exc:
        raise AnalysisProcessError(f"missing spilled source: {exc}")


def discard_spills(paths) -> None:
    """Delegate to shared wire helper (kept for backward compat)."""
    return _wire_discard(paths)


class AnalysisProcess:
    """Client end of the analysis-server subprocess."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._pipe_lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._shutdown_requested = False


    def _server_script(self) -> str:
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(here, "analysis_server.py")

    def _root_dir(self) -> str:
        return os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

    def _server_cmd(self) -> list[str]:
        """Return the command to launch the analysis server."""
        if getattr(sys, "frozen", False):
            exe_dir = pathlib.Path(sys.executable).resolve().parent
            candidate = exe_dir / "DreamStudioAnalysisServer"
            if candidate.is_file():
                return [str(candidate)]
            try:
                if hasattr(sys, "_MEIPASS"):
                    alt = (
                        pathlib.Path(sys._MEIPASS).resolve().parent
                        / "DreamStudioAnalysisServer"
                    )
                    if alt.is_file():
                        return [str(alt)]
            except Exception:
                pass
            return [str(candidate)]
        return [sys.executable, self._server_script()]

    def _drain_stderr(self, stream) -> None:
        try:
            for line in stream:
                logger.debug("analysis-server: %s", line.rstrip())
        except Exception:
            pass


    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> None:
        """Spawn (or respawn) the analysis subprocess."""
        with self._lifecycle_lock:
            if self._shutdown_requested:
                return
            if self.is_alive():
                return

            cmd = self._server_cmd()
            if getattr(sys, "frozen", False):
                exe_path = pathlib.Path(cmd[0])
                if not exe_path.is_file():
                    raise FileNotFoundError(
                        f"DreamStudioAnalysisServer not found at {exe_path}. "
                        f"Expected sibling executable next to {sys.executable}"
                    )

            # NOTE: bufsize=0 keeps the pipes unbuffered at the Python
            if getattr(sys, "frozen", False):
                self._proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0,
                )
            else:
                root = self._root_dir()
                env = dict(os.environ)
                pythonpath = env.get("PYTHONPATH", "")
                if root not in pythonpath.split(os.pathsep):
                    env["PYTHONPATH"] = root + (
                        os.pathsep + pythonpath if pythonpath else ""
                    )

                self._proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=root,
                    env=env,
                    bufsize=0,
                )
            self._stderr_thread = threading.Thread(
                target=self._drain_stderr,
                args=(self._proc.stderr,),
                name="analysis-server-stderr",
                daemon=True,
            )
            self._stderr_thread.start()
            logger.debug("analysis-server started (pid=%s)", self._proc.pid)
            try:
                _cleanup_stale_spills()
            except Exception:
                pass

    def __del__(self) -> None:
        """Kill a still-running child when the client is collected."""
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.kill()
                try:
                    proc.wait(timeout=2)
                except Exception:
                    pass
        except Exception:
            pass
        for stream_name in ("stdin", "stdout", "stderr"):
            try:
                stream = getattr(proc, stream_name, None)
                if stream is not None:
                    stream.close()
            except Exception:
                pass

    def request(self, payload, timeout: float = _REQUEST_TIMEOUT_S) -> object:
        """Send *payload* to the server and block for its reply."""
        locked = self._pipe_lock.acquire(timeout=timeout)
        if not locked:
            raise AnalysisProcessError("analysis subprocess busy (lock timeout)")
        try:
            if self._shutdown_requested:
                raise AnalysisProcessError("analysis subprocess is shut down")
            proc = self._proc
            if proc is None or proc.poll() is not None:
                self.start()
                proc = self._proc
            if proc is None:
                raise AnalysisProcessError("unable to start analysis subprocess")

            packed, spilled = payload, []
            try:
                if isinstance(payload, tuple):
                    packed, spilled = spill_large_strings(payload)
                write_frame(proc.stdin, packed)
                # NOTE: the lock is already held, so the read must be
                return read_frame(proc.stdout, time.monotonic() + timeout)
            except (BrokenPipeError, OSError, pickle.PickleError) as exc:
                logger.warning(
                    "Analysis subprocess IPC failed, resetting handle: %s", exc
                )
                if self._proc is not None:
                    try:
                        self._proc.kill()
                    except Exception:
                        pass
                    self._proc = None
                raise AnalysisProcessError(f"IPC communication failure: {exc}")
            except AnalysisProcessError:
                raise
            finally:
                if spilled:
                    discard_spills(spilled)
        finally:
            try:
                self._pipe_lock.release()
            except Exception:
                pass

    def shutdown(self) -> None:
        """Request a graceful shutdown without blocking the caller."""
        with self._lifecycle_lock:
            if self._shutdown_requested:
                return
            self._shutdown_requested = True
            proc = self._proc
            self._proc = None

        if proc is None or proc.poll() is not None:
            return

        threading.Thread(
            target=self._reap,
            args=(proc,),
            name="analysis-server-reaper",
            daemon=False,
        ).start()

    def _reap(self, proc: subprocess.Popen) -> None:
        """Gracefully stop *proc*, force-killing it after the timeout."""
        try:
            try:
                if self._pipe_lock.acquire(timeout=2.0):
                    try:
                        if proc.poll() is None:
                            proc.stdin.write(_FRAME_HEADER.pack(0))
                            proc.stdin.flush()
                    finally:
                        self._pipe_lock.release()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
            if proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
        finally:
            for pipe in (proc.stdin, proc.stdout, proc.stderr):
                if pipe is not None:
                    try:
                        pipe.close()
                    except Exception:
                        pass
