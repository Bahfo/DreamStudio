"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Singleton VCS status broker mediating between the Solution Explorer and
the Source Control panel. Neither panel references the other; both talk
exclusively to this service, which owns the scanning thread and the
lock-guarded status snapshot.
"""

import logging
import threading
from typing import Dict, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

from editor.utils.git_control.git_control import get_status_map, return_repository

logger = logging.getLogger(__name__)


class _ScanWorker(QThread):
    """
    Event-driven scan loop living off the GUI thread.

    Wakes exclusively when an operation requests a scan. A dirty flag set
    during an active scan coalesces bursts into exactly one follow-up
    pass instead of queuing per-operation work.
    """

    statuses_ready = pyqtSignal(str, dict)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._wake_event = threading.Event()
        self._state_lock = threading.Lock()
        self._dirty = False
        self._running = True
        self._root: Optional[str] = None

    def set_root(self, root_path: Optional[str]) -> None:
        """Update the scanned workspace root and force a fresh scan."""
        with self._state_lock:
            self._root = root_path
            self._dirty = False
        self._wake_event.set()

    def request_scan(self, reason: str = "") -> None:
        """Coalesce a scan request; concurrent requests collapse to one."""
        with self._state_lock:
            self._dirty = True
        logger.debug("VCS scan requested: %s", reason)
        self._wake_event.set()

    def stop(self) -> None:
        """Terminate the loop; safe to call from any thread."""
        with self._state_lock:
            self._running = False
        self._wake_event.set()

    def run(self) -> None:
        """Block until woken, scan, publish; repeat until stopped."""
        while True:
            self._wake_event.wait()
            self._wake_event.clear()
            with self._state_lock:
                if not self._running:
                    return
                root = self._root
                self._dirty = False

            repo_root, snapshot = self._scan(root)

            with self._state_lock:
                superseded = self._dirty
            if superseded:
                continue
            self.statuses_ready.emit(repo_root, snapshot)

    @staticmethod
    def _scan(root_path: Optional[str]) -> tuple[str, dict[str, str]]:
        """Resolve the enclosing repository and read its status map."""
        if not root_path:
            return "", {}
        repo = return_repository(root_path)
        if repo is None:
            return "", {}
        try:
            return repo.working_dir or "", get_status_map(repo)
        except Exception:
            logger.exception("VCS status scan failed")
            return "", {}


class GitStatusService(QObject):
    """
    Lock-guarded publisher of repository status snapshots.

    Consumers connect to :attr:`statuses_updated`; the payload maps
    repository-relative paths to ``M``/``U``/``A`` symbols. Files without
    changes are intentionally absent so renderers skip them entirely.
    """

    statuses_updated = pyqtSignal(str, dict)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._worker = _ScanWorker()
        self._snapshot_lock = threading.Lock()
        self._snapshot: Dict[str, str] = {}
        self._repo_root = ""

        self._worker.statuses_ready.connect(self._on_statuses_ready)
        self._worker.start()

        application = QApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(self.stop)

    def set_root(self, root_path: str) -> None:
        """Point the scanner at a workspace root (triggers initial scan)."""
        self._worker.set_root(root_path)

    def request_scan(self, reason: str = "") -> None:
        """Ask for a rescan after any mutating operation."""
        self._worker.request_scan(reason)

    def snapshot(self) -> Dict[str, str]:
        """Return a thread-safe copy of the latest status snapshot."""
        with self._snapshot_lock:
            return dict(self._snapshot)

    def repo_root(self) -> str:
        """Return the repository root of the last completed scan."""
        with self._snapshot_lock:
            return self._repo_root

    def stop(self) -> None:
        """Stop the worker and flush state; invoked on application quit."""
        self._worker.stop()
        self._worker.wait(3000)

    def _on_statuses_ready(self, repo_root: str, snapshot: dict) -> None:
        """Store the fresh snapshot under the lock, then republish it."""
        with self._snapshot_lock:
            self._repo_root = repo_root
            self._snapshot = dict(snapshot)
        self.statuses_updated.emit(repo_root, dict(snapshot))


_service: Optional[GitStatusService] = None


def get_status_service() -> GitStatusService:
    """Return the process-wide status service, creating it lazily."""
    global _service
    if _service is None:
        _service = GitStatusService()
    return _service
