# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""Parent-side client for the out-of-process analysis server.

Analysis runs in a dedicated interpreter subprocess (``analysis_server.py``)
so that CPU-bound Python work (jedi, ast, tokenize) never contends with the
main thread's GIL — the root cause of UI freezes while typing in large files.

Protocol
--------
Framed pickle over the child's stdin/stdout: every message is an 8-byte
little-endian length followed by ``pickle.dumps`` of a plain-data payload.
Both endpoints are strictly request/response: the worker thread writes one
frame, then blocks reading the reply, so at most a single request is in
flight per subprocess.

The server is spawned as a plain script (not ``-m``) with its own isolated
package stubs, so importing it never pulls in the heavyweight
``editor/__init__.py`` GUI chain.
"""

from __future__ import annotations

import logging
import os
import pickle
import struct
import subprocess
import sys
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_FRAME_HEADER = struct.Struct("<Q")
_PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL


class AnalysisProcessError(RuntimeError):
    """Raised when the analysis subprocess dies or the wire protocol breaks."""


def _read_exact(stream, n: int) -> bytes:
    """Read exactly *n* bytes from *stream* or raise ``AnalysisProcessError``."""
    chunks: list = []
    remaining = n
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            raise AnalysisProcessError("analysis subprocess closed its output stream")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(stream) -> object:
    """Read one length-prefixed pickle frame from *stream*."""
    header = _read_exact(stream, _FRAME_HEADER.size)
    (size,) = _FRAME_HEADER.unpack(header)
    data = _read_exact(stream, size)
    return pickle.loads(data)


def write_frame(stream, payload) -> None:
    """Write one length-prefixed pickle frame to *stream*."""
    data = pickle.dumps(payload, protocol=_PICKLE_PROTOCOL)
    stream.write(_FRAME_HEADER.pack(len(data)))
    stream.write(data)
    stream.flush()


class AnalysisProcess:
    """Client end of the analysis-server subprocess.

    Designed for exactly one live subprocess shared across the whole IDE:
    ``request`` serialises write/read round-trips through an internal lock,
    and ``shutdown`` hands the blocking reap off to a daemon reaper thread
    so the UI thread never waits on a busy child.  A dead child is
    transparently respawned on the next ``request`` call unless a clean
    ``shutdown`` has already been requested.
    """

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._pipe_lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._shutdown_requested = False

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def _server_script(self) -> str:
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(here, "analysis_server.py")

    def _root_dir(self) -> str:
        # <root>/editor/Ironica/analysis_bridge.py -> <root>
        return os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

    def _drain_stderr(self, stream) -> None:
        try:
            for line in stream:
                logger.debug("analysis-server: %s", line.rstrip())
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> None:
        """Spawn (or respawn) the analysis subprocess."""
        with self._lifecycle_lock:
            if self._shutdown_requested:
                return
            if self.is_alive():
                return

            root = self._root_dir()
            env = dict(os.environ)
            pythonpath = env.get("PYTHONPATH", "")
            if root not in pythonpath.split(os.pathsep):
                env["PYTHONPATH"] = root + (
                    os.pathsep + pythonpath if pythonpath else ""
                )

            self._proc = subprocess.Popen(
                [sys.executable, self._server_script()],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=root,
                env=env,
            )
            self._stderr_thread = threading.Thread(
                target=self._drain_stderr,
                args=(self._proc.stderr,),
                name="analysis-server-stderr",
                daemon=True,
            )
            self._stderr_thread.start()
            logger.debug("analysis-server started (pid=%s)", self._proc.pid)

    def __del__(self) -> None:
        """Kill a still-running child when the client is collected.

        The worker threads are deliberately not ``QThread`` so garbage
        collection of an editor never aborts Qt; this finalizer prevents
        the orphaned child from outliving the parent process.
        """
        proc = self._proc
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.kill()
        except Exception:
            pass

    def request(self, payload) -> object:
        """Send *payload* to the server and block for its reply.

        The pipe lock is held for the whole write/read round-trip so at
        most one request is in flight against the child at a time.
        """
        with self._pipe_lock:
            if self._shutdown_requested:
                raise AnalysisProcessError("analysis subprocess is shut down")
            proc = self._proc
            if proc is None or proc.poll() is not None:
                self.start()
                proc = self._proc
            if proc is None:
                raise AnalysisProcessError("unable to start analysis subprocess")
            write_frame(proc.stdin, payload)
            return read_frame(proc.stdout)

    def shutdown(self) -> None:
        """Request a graceful shutdown without blocking the caller.

        The exit sentinel is written by a daemon reaper thread once any
        in-flight round-trip has finished; the child then exits and is
        force-killed only if it fails to do so within the reap timeout.
        Never touches ``self._pipe_lock`` from the caller's thread, so
        shutting down while the child is busy computing never stalls the
        UI thread.
        """
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
            daemon=True,
        ).start()

    def _reap(self, proc: subprocess.Popen) -> None:
        """Gracefully stop *proc*, force-killing it after the timeout."""
        try:
            try:
                # Wait for any in-flight round-trip to release the pipe
                # lock, then ask the child to exit. Bounded by the current
                # request's compute time.
                with self._pipe_lock:
                    if proc.poll() is None:
                        proc.stdin.write(_FRAME_HEADER.pack(0))
                        proc.stdin.flush()
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
