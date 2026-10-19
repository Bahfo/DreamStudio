"""Focus-aware owner of the single shared analysis subprocess."""

from __future__ import annotations

from editor import *

from editor.Ironica.analysis_bridge import AnalysisProcess

logger = logging.getLogger(__name__)


class AnalysisProcessManager:
    """Shared, focus-routed owner of a single warm analysis process."""

    def __init__(self) -> None:
        self._process = AnalysisProcess()
        self._active_owner: Optional[int] = None
        self._engaged = False
        self._shutting_down = False
        self._lock = threading.Lock()


    def set_active(self, owner_id: Optional[int]) -> None:
        """Make *owner_id* the only owner allowed to submit requests."""
        self._engaged = True
        self._active_owner = owner_id

    def release(self, owner_id: Optional[int]) -> None:
        """Clear the active owner if it is still *owner_id*."""
        if self._active_owner == owner_id:
            self._active_owner = None

    def is_active(self, owner_id: Optional[int]) -> bool:
        """Return ``True`` if *owner_id* may submit requests right now."""
        if owner_id is None or self._shutting_down:
            return False
        if not self._engaged:
            return True
        return owner_id == self._active_owner


    def request(self, owner_id: Optional[int], payload) -> object:
        """Submit *payload* on behalf of *owner_id*; block for the reply."""
        if self._shutting_down or not self.is_active(owner_id):
            return None

        with self._lock:
            if self._shutting_down or not self.is_active(owner_id):
                return None
            result = self._process.request(payload)
            if not self.is_active(owner_id):
                return None
            return result


    def shutdown(self) -> None:
        """Stop the shared process (asynchronously) and drop all requests."""
        self._shutting_down = True
        self._active_owner = None
        try:
            self._process.shutdown()
        except Exception as exc:
            logger.debug("analysis process shutdown failed: %s", exc)


process_manager = AnalysisProcessManager()
atexit.register(process_manager.shutdown)
