"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Singleton VCS status broker mediating between the Solution Explorer and the Source Control panel.
"""

from editor import *

from editor.utils.git_control.git_control import get_status_map, return_repository

logger = logging.getLogger(__name__)

#: Strong references to workers that have been started. See the note in
_RETAINED_WORKERS: list = []


def _retain_worker(worker) -> None:
    """Keep *worker* alive for the life of the process.

    Args:
        worker: The started ``_ScanWorker`` to retain.
    """
    if worker not in _RETAINED_WORKERS:
        _RETAINED_WORKERS.append(worker)


class _ScanWorker(QObject):
    """Event-driven scan loop living off the GUI thread."""

    statuses_ready = pyqtSignal(str, dict)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        # NOTE: deliberately NOT parented to the owning service. Qt destroys a
        super().__init__(parent)
        self._wake_event = threading.Event()
        self._state_lock = threading.Lock()
        self._dirty = False
        self._running = True
        self._root: Optional[str] = None
        self._generation = 0
        self._thread: Optional[threading.Thread] = None

    def start_scan(self) -> None:
        """Launch the scan loop on a fresh daemon thread (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return
        thread = threading.Thread(
            target=self._loop,
            name="DreamStudio-VcsScanner",
            daemon=True,
        )
        self._thread = thread
        thread.start()
        _retain_worker(self)

    def set_root(self, root_path: Optional[str]) -> None:
        """Update the scanned workspace root and force a fresh scan."""
        with self._state_lock:
            self._root = root_path
            self._dirty = False
            self._generation += 1
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

    def join(self, timeout: float = 3.0) -> bool:
        """Wait for the scan thread to exit."""
        thread = self._thread
        if thread is None or not thread.is_alive():
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def _loop(self) -> None:
        """Block until woken, scan, publish; repeat until stopped."""
        while True:
            self._wake_event.wait()
            self._wake_event.clear()
            with self._state_lock:
                if not self._running:
                    return
                root = self._root
                gen = self._generation
                self._dirty = False

            repo_root, snapshot = self._scan(root)

            with self._state_lock:
                superseded = self._dirty or gen != self._generation
                if not self._running:
                    return
            if superseded:
                continue
            try:
                self.statuses_ready.emit(repo_root, snapshot)
            except RuntimeError:
                return
            except Exception:
                logger.debug("VCS status publish failed", exc_info=True)

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
    """Lock-guarded publisher of repository status snapshots."""

    statuses_updated = pyqtSignal(str, dict)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._stopped = False
        self._worker = _ScanWorker()
        _retain_worker(self._worker)
        self._snapshot_lock = threading.Lock()
        self._snapshot: Dict[str, str] = {}
        self._repo_root = ""
        self._expected_root = ""

        self._worker.statuses_ready.connect(self._on_statuses_ready)
        self._worker.start_scan()

        application = QApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(self.stop)

    def set_root(self, root_path: str) -> None:
        """Point the scanner at a workspace root (triggers initial scan)."""
        with self._snapshot_lock:
            self._expected_root = root_path or ""
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
        """Stop the scan loop and wait for its thread to exit."""
        if self._stopped:
            return
        self._stopped = True
        worker = getattr(self, "_worker", None)
        if worker is None:
            return
        try:
            worker.stop()
            if not worker.join(3.0):
                logger.warning("VCS scan thread did not finish within 3s")
        except Exception:
            logger.debug("VCS worker stop failed", exc_info=True)

    def _on_statuses_ready(self, repo_root: str, snapshot: dict) -> None:
        """Store the fresh snapshot under the lock, then republish it."""
        with self._snapshot_lock:
            expected = self._expected_root
        if expected:
            try:
                from editor.utils.git_control.git_control import return_repository

                repo = return_repository(expected)
                expected_root = repo.working_dir if repo else expected
                if repo_root and expected_root and repo_root != expected_root:
                    return
            except Exception:
                pass
            with self._snapshot_lock:
                self._repo_root = repo_root
                self._snapshot = dict(snapshot)
            self.statuses_updated.emit(repo_root, dict(snapshot))
        else:
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


def _shutdown_status_service() -> None:
    """Join the scan thread at interpreter exit, before Qt tears down.

    Registered with :mod:`atexit` so the singleton is stopped while the
    ``QApplication`` still exists; relying on module-global collection
    alone leaves the worker running into Qt's finalisation.
    """
    service = _service
    if service is None:
        return
    try:
        service.stop()
    except Exception:
        pass


atexit.register(_shutdown_status_service)
