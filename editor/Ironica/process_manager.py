# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""Focus-aware owner of the single shared analysis subprocess.

The whole IDE keeps exactly one ``AnalysisProcess`` alive (warm) and routes
requests from the currently *focused* editor through it.  Only the active
owner's requests are sent; switching tabs just swaps ``_active_owner``, so:

- Closing a tab never touches the process (no main-thread ``proc.wait``).
- Memory stays O(1) regardless of how many tabs are open.
- An in-flight result whose owner lost focus is discarded the moment it
  arrives, so stale overlays can never repaint the active buffer.

When focus routing has never been engaged (no tab editor wired it up) the
manager is "unmanaged": any request is allowed — the mode unit tests and
standalone editors use.  Once engaged, only the focused owner submits.
"""

from __future__ import annotations

import atexit
import logging
import threading
from typing import Optional

from editor.Ironica.analysis_bridge import AnalysisProcess

logger = logging.getLogger(__name__)


class AnalysisProcessManager:
    """Shared, focus-routed owner of a single warm analysis process."""

    def __init__(self) -> None:
        self._process = AnalysisProcess()
        self._active_owner: Optional[int] = None
        # ``_engaged`` distinguishes "focus routing never wired up" (the
        # standalone/unmanaged mode unit tests rely on) from "explicitly
        # cleared" (e.g. a designer tab focused, or the last tab closed)
        # where *no* owner may submit requests.
        self._engaged = False
        self._shutting_down = False
        # Serialises the write/read round-trip; one request in flight at a
        # time against the single-flight child.
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Focus routing
    # ------------------------------------------------------------------

    def set_active(self, owner_id: Optional[int]) -> None:
        """Make *owner_id* the only owner allowed to submit requests.

        Deliberately lock-free (a single atomic assignment) so switching
        tabs never blocks behind an in-flight round-trip.  ``None`` clears
        the active owner and blocks every submission until a new owner is
        focused.
        """
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
            return True  # unmanaged — no focus routing engaged
        return owner_id == self._active_owner

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    def request(self, owner_id: Optional[int], payload) -> object:
        """Submit *payload* on behalf of *owner_id*; block for the reply.

        Returns ``None`` when the request was *dropped* — the owner is not
        active (or the manager is shutting down) — so callers never have to
        wait their turn behind a stale owner's work.  An in-flight result
        whose owner loses focus while the child computes is discarded upon
        arrival via the post-read ownership re-check.
        """
        if self._shutting_down or not self.is_active(owner_id):
            return None

        with self._lock:
            if self._shutting_down or not self.is_active(owner_id):
                return None
            result = self._process.request(payload)
            if not self.is_active(owner_id):
                return None  # owner lost focus while the child was working
            return result

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

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
